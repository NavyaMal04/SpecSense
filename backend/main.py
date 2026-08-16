"""
backend/main.py
================
FastAPI app for SpecSense.

Wires the existing pipeline modules together:
  extractor -> llm_extractor -> record_builder (+ inference) -> copy_generator -> firestore_client

Every endpoint here calls the pipeline functions exactly as they're
defined in pipeline/ — this file does orchestration and HTTP plumbing
only, no pipeline logic of its own.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.extractor import get_full_text_with_citations, PDFExtractionError
from pipeline.llm_extractor import extract_structured_fields, LLMExtractionError
from pipeline.record_builder import build_product_record, infer_missing_fields
from pipeline.copy_generator import generate_commerce_copy, CopyGenerationError
from pipeline.schema import ProductRecord, AttributeField
from pipeline import firestore_client as fdb

app = FastAPI(title="SpecSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Reference dataset (for TF-IDF inference) — loaded once at startup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_PATH = PROJECT_ROOT / "data" / "reference" / "sample_products.json"

_reference_dataset: List[dict] = []
if REFERENCE_PATH.exists():
    with open(REFERENCE_PATH, "r", encoding="utf-8") as f:
        _reference_dataset = json.load(f)

CORE_KEYS = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]
EST_MANUAL_MINUTES_PER_PRODUCT = 12


# ---------------------------------------------------------------------------
# Shared pipeline runner — used by both /upload and /batch so the numbers
# on the batch dashboard come from the exact same code path as a single
# upload, not a separate/duplicated implementation.
# ---------------------------------------------------------------------------
def _run_pipeline(pdf_path: str, filename: str) -> ProductRecord:
    cited_text, _offsets = get_full_text_with_citations(pdf_path)
    raw_llm_json = extract_structured_fields(cited_text, source_filename=filename)
    record = build_product_record(raw_llm_json, filename, cited_text)
    record = infer_missing_fields(record, _reference_dataset)

    # Don't generate buyer copy on top of unresolved conflicts — copy_generator
    # already excludes flagged fields from its grounding context, but if a
    # record is entirely flagged there's nothing useful to write yet.
    has_any_verified = any(
        getattr(record, k).value is not None and getattr(record, k).source_type != "flagged"
        for k in CORE_KEYS
    )
    if has_any_verified:
        record = generate_commerce_copy(record)

    try:
        fdb.save_product_record(record)
    except Exception as save_err:
        # Firestore may not be configured yet during local dev — surface the
        # record anyway rather than failing the whole request silently.
        print(f"[WARN] Could not save to Firestore: {save_err}")

    return record


def _save_upload_to_tmp(file: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        return tmp.name


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/upload")
async def upload_single(file: UploadFile = File(...)):
    tmp_path = _save_upload_to_tmp(file)
    try:
        record = _run_pipeline(tmp_path, file.filename)
    except PDFExtractionError as e:
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {e}")
    except LLMExtractionError as e:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {e}")
    except CopyGenerationError as e:
        raise HTTPException(status_code=502, detail=f"Copy generation failed: {e}")
    finally:
        os.unlink(tmp_path)
    return record.model_dump()


@app.post("/batch")
async def upload_batch(files: List[UploadFile] = File(...)):
    start = time.time()
    results: List[dict] = []
    errors: List[dict] = []

    for file in files:
        tmp_path = _save_upload_to_tmp(file)
        try:
            record = _run_pipeline(tmp_path, file.filename)
            results.append(record.model_dump())
        except (PDFExtractionError, LLMExtractionError, CopyGenerationError) as e:
            errors.append({"filename": file.filename, "error": str(e)})
        finally:
            os.unlink(tmp_path)

    flagged_total = sum(
        1 for r in results for k in CORE_KEYS if r[k]["source_type"] == "flagged"
    )
    fully_verified = sum(
        1 for r in results if all(r[k]["source_type"] != "flagged" for k in CORE_KEYS)
    )

    return {
        "processed_count": len(results),
        "failed_count": len(errors),
        "fully_verified_count": fully_verified,
        "flagged_field_total": flagged_total,
        "estimated_manual_minutes": len(results) * EST_MANUAL_MINUTES_PER_PRODUCT,
        "elapsed_seconds": round(time.time() - start, 1),
        "records": results,
        "errors": errors,
    }


@app.get("/products")
async def get_products(review_status: Optional[str] = Query(default=None)):
    try:
        records = fdb.list_product_records(review_status=review_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Firestore not configured: {e}")
    return [r.model_dump() for r in records]


@app.get("/products/{product_id}")
async def get_product(product_id: str):
    try:
        record = fdb.get_product_record(product_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Firestore not configured: {e}")
    return record.model_dump()


class FieldReviewRequest(BaseModel):
    accept_as_is: bool = False
    corrected_value: Optional[str] = None  # required if accept_as_is is False
    additional_attribute_index: Optional[int] = None  # set to review an additional_attributes[i] entry instead


@app.post("/products/{product_id}/review/{field_name}")
async def review_field(product_id: str, field_name: str, body: FieldReviewRequest):
    """
    Human-in-the-loop review for a single field.

    - accept_as_is=True: keeps the current value, marks it human-verified.
    - accept_as_is=False: overwrites the value with corrected_value, marks it human-verified.

    After updating the field, recomputes the record's overall review_status:
    "approved" if no fields remain flagged, otherwise stays "flagged".
    """
    try:
        record = fdb.get_product_record(product_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Firestore not configured: {e}")

    if not body.accept_as_is and body.corrected_value is None:
        raise HTTPException(status_code=400, detail="corrected_value is required when accept_as_is is False")

    note = "Manually approved by reviewer" if body.accept_as_is else "Manually corrected by reviewer"

    if body.additional_attribute_index is not None:
        idx = body.additional_attribute_index
        if idx < 0 or idx >= len(record.additional_attributes):
            raise HTTPException(status_code=400, detail="additional_attribute_index out of range")
        current = record.additional_attributes[idx]
        new_value = current.value if body.accept_as_is else body.corrected_value
        record.additional_attributes[idx] = AttributeField(
            value=new_value, source_type="extracted", confidence=1.0, source_location=note
        )
    else:
        if field_name not in CORE_KEYS:
            raise HTTPException(status_code=400, detail=f"Unknown field '{field_name}'. Must be one of {CORE_KEYS}")
        current: AttributeField = getattr(record, field_name)
        new_value = current.value if body.accept_as_is else body.corrected_value
        setattr(
            record, field_name,
            AttributeField(value=new_value, source_type="extracted", confidence=1.0, source_location=note),
        )

    still_flagged = any(getattr(record, k).source_type == "flagged" for k in CORE_KEYS) or any(
        attr.source_type == "flagged" for attr in record.additional_attributes
    )
    record.review_status = "flagged" if still_flagged else "approved"

    try:
        fdb.save_product_record(record)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Firestore not configured: {e}")

    return record.model_dump()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "reference_products_loaded": len(_reference_dataset),
        "gemini_key_set": bool(os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here"),
        "firebase_configured": bool(os.getenv("FIREBASE_CREDENTIALS_PATH")),
    }
