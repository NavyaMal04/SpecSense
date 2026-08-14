"""
firestore_client.py
====================
Firestore persistence layer for the SpecSense pipeline.

Provides four core operations on the "products" collection:
  - save_product_record()       — upsert a ProductRecord
  - get_product_record()        — fetch by document ID
  - list_product_records()      — list all, or filter by review_status
  - update_review_status()      — patch just the review_status field

Credentials are loaded from FIREBASE_CREDENTIALS_PATH in .env.
"""

import os
import sys
import json
from typing import Optional, List

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from pipeline.schema import ProductRecord

load_dotenv()

# ---------------------------------------------------------------------------
# Module-level Firebase app singleton — initialised once on first import
# ---------------------------------------------------------------------------
_db: Optional[firestore.Client] = None   # type: ignore[name-defined]


def _get_db() -> firestore.Client:  # type: ignore[name-defined]
    """
    Returns a Firestore client, initialising Firebase Admin SDK on first call.

    Reads FIREBASE_CREDENTIALS_PATH from the environment.  Raises a clear
    RuntimeError if the credentials file is absent or the SDK fails to start.
    """
    global _db
    if _db is not None:
        return _db

    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not creds_path:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS_PATH is not set in your .env file. "
            "Add the path to your Firebase service-account JSON."
        )

    abs_creds = os.path.abspath(creds_path)
    if not os.path.isfile(abs_creds):
        raise RuntimeError(
            f"Firebase credentials file not found at: {abs_creds}\n"
            "Verify that FIREBASE_CREDENTIALS_PATH in your .env points to the "
            "correct service-account JSON file."
        )

    # Only initialise if no default app exists yet (guard against re-imports)
    if not firebase_admin._apps:
        cred = credentials.Certificate(abs_creds)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _record_to_dict(record: ProductRecord) -> dict:
    """
    Converts a ProductRecord to a plain Python dict safe for Firestore storage.

    model_dump() handles all nested Pydantic models including generic
    AttributeField[T] and CommerceCopyField[T] instances.
    """
    return record.model_dump()


def _dict_to_record(data: dict) -> ProductRecord:
    """
    Parses a raw Firestore document dict back into a ProductRecord.

    Uses model_validate() so Pydantic rebuilds nested sub-models correctly.
    """
    return ProductRecord.model_validate(data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

COLLECTION = "products"


def save_product_record(record: ProductRecord) -> str:
    """
    Saves (or overwrites) a ProductRecord to Firestore.

    - If record.id is None  → Firestore auto-generates a document ID, which
      is then written back onto record.id before returning.
    - If record.id is set   → that ID is used as the document key (upsert).

    Returns:
        The Firestore document ID (str).

    Raises:
        RuntimeError: On credential / SDK initialisation failure.
        Exception:    On any Firestore write error (wraps with context).
    """
    try:
        db = _get_db()
        collection_ref = db.collection(COLLECTION)
        payload = _record_to_dict(record)

        if record.id is None:
            # Auto-generate ID
            _, doc_ref = collection_ref.add(payload)
            record.id = doc_ref.id
            # Patch the auto-generated id back into the stored document
            doc_ref.update({"id": record.id})
        else:
            doc_ref = collection_ref.document(record.id)
            payload["id"] = record.id
            doc_ref.set(payload)          # full overwrite / upsert

        return record.id

    except RuntimeError:
        raise
    except Exception as err:
        raise Exception(
            f"[Firestore] Failed to save product record: {err}"
        ) from err


def get_product_record(doc_id: str) -> ProductRecord:
    """
    Fetches a single ProductRecord from Firestore by document ID.

    Args:
        doc_id: The Firestore document ID to retrieve.

    Returns:
        A fully parsed ProductRecord instance.

    Raises:
        KeyError:   If the document does not exist.
        Exception:  On any Firestore read error.
    """
    try:
        db = _get_db()
        doc_ref = db.collection(COLLECTION).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise KeyError(
                f"[Firestore] No product found with document ID '{doc_id}'. "
                "Verify the ID or check the 'products' collection."
            )

        return _dict_to_record(doc.to_dict())

    except (KeyError, RuntimeError):
        raise
    except Exception as err:
        raise Exception(
            f"[Firestore] Failed to fetch product record '{doc_id}': {err}"
        ) from err


def list_product_records(review_status: Optional[str] = None) -> List[ProductRecord]:
    """
    Returns all ProductRecords in the "products" collection.

    Args:
        review_status: Optional filter value — "pending", "approved", or
                       "flagged".  When provided only matching documents are
                       returned.  When None, all documents are returned.

    Returns:
        A list of ProductRecord instances (may be empty).

    Raises:
        ValueError:  If review_status is not one of the accepted values.
        Exception:   On any Firestore query error.
    """
    valid_statuses = {"pending", "approved", "flagged"}
    if review_status is not None and review_status not in valid_statuses:
        raise ValueError(
            f"[Firestore] Invalid review_status '{review_status}'. "
            f"Must be one of: {', '.join(sorted(valid_statuses))}."
        )

    try:
        db = _get_db()
        query = db.collection(COLLECTION)

        if review_status is not None:
            query = query.where(filter=FieldFilter("review_status", "==", review_status))

        docs = query.stream()
        records = []
        for doc in docs:
            try:
                records.append(_dict_to_record(doc.to_dict()))
            except Exception as parse_err:
                # Skip malformed docs but surface a warning
                print(
                    f"[Firestore] Warning: could not parse document '{doc.id}': "
                    f"{parse_err}"
                )

        return records

    except (ValueError, RuntimeError):
        raise
    except Exception as err:
        raise Exception(
            f"[Firestore] Failed to list product records: {err}"
        ) from err


def update_review_status(doc_id: str, new_status: str) -> None:
    """
    Patches the review_status field on an existing Firestore document.

    Used by the human-review dashboard to approve or re-flag records without
    overwriting the full document.

    Args:
        doc_id:     The Firestore document ID to update.
        new_status: The new review status — must be "pending", "approved",
                    or "flagged".

    Raises:
        ValueError:  If new_status is not a valid option.
        KeyError:    If the document does not exist.
        Exception:   On any Firestore write error.
    """
    valid_statuses = {"pending", "approved", "flagged"}
    if new_status not in valid_statuses:
        raise ValueError(
            f"[Firestore] Invalid review_status '{new_status}'. "
            f"Must be one of: {', '.join(sorted(valid_statuses))}."
        )

    try:
        db = _get_db()
        doc_ref = db.collection(COLLECTION).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise KeyError(
                f"[Firestore] Cannot update — no document found with ID '{doc_id}'."
            )

        doc_ref.update({"review_status": new_status})

    except (ValueError, KeyError, RuntimeError):
        raise
    except Exception as err:
        raise Exception(
            f"[Firestore] Failed to update review_status for '{doc_id}': {err}"
        ) from err


# ---------------------------------------------------------------------------
# Test / smoke-test harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json as _json

    # Ensure stdout can handle any Unicode the pipeline produces on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Pipeline imports
    from pipeline.extractor import get_full_text_with_citations
    from pipeline.llm_extractor import extract_structured_fields
    from pipeline.record_builder import build_product_record, infer_missing_fields
    from pipeline.copy_generator import generate_commerce_copy

    REF_PATH = "data/reference/sample_products.json"
    TEST_PDF = "data/samples/cordless_drill_spec.pdf"

    print("=" * 62)
    print("   SpecSense — Firestore Persistence Layer Smoke Test")
    print("=" * 62)

    # ── 1. Load reference dataset ─────────────────────────────────────────
    ref_dataset = []
    if os.path.exists(REF_PATH):
        with open(REF_PATH, "r", encoding="utf-8") as f:
            ref_dataset = _json.load(f)
        print(f"[Setup]  Loaded {len(ref_dataset)} reference products.")

    # ── 2. Run the full pipeline ──────────────────────────────────────────
    filename = os.path.basename(TEST_PDF)
    print(f"\n[Step 1] Running full pipeline on '{filename}' …")

    try:
        cited_text, _ = get_full_text_with_citations(os.path.abspath(TEST_PDF))
        raw_llm = extract_structured_fields(cited_text, source_filename=filename)
        record = build_product_record(raw_llm, filename, cited_text)
        record = infer_missing_fields(record, ref_dataset)
        record = generate_commerce_copy(record)
        print(f"         [OK] Pipeline complete - product name: {record.name.value!r}")
        print(f"         Review status before save: {record.review_status!r}")
    except Exception as err:
        print(f"[ERROR]  Pipeline failed: {err}")
        sys.exit(1)

    # ── 3. Save to Firestore ──────────────────────────────────────────────
    print("\n[Step 2] Saving ProductRecord to Firestore...")
    try:
        doc_id = save_product_record(record)
        print(f"         [OK] Saved successfully. Document ID: {doc_id!r}")
    except Exception as err:
        print(f"[ERROR]  save_product_record() failed: {err}")
        sys.exit(1)

    # ── 4. Fetch back and verify round-trip ───────────────────────────────
    print(f"\n[Step 3] Fetching record back by ID '{doc_id}'...")
    try:
        fetched = get_product_record(doc_id)
        print(f"         [OK] Fetch successful.")
        print(f"         Name       : {fetched.name.value!r}")
        print(f"         Category   : {fetched.category.value!r}")
        print(f"         Title      : {fetched.title.value!r}")
        print(f"         Review     : {fetched.review_status!r}")
        print(f"         Source file: {fetched.source_file!r}")
    except Exception as err:
        print(f"[ERROR]  get_product_record() failed: {err}")
        sys.exit(1)

    # ── 5. List ALL products ──────────────────────────────────────────────
    print("\n[Step 4] Listing ALL products in collection...")
    try:
        all_records = list_product_records()
        print(f"         [OK] Total products in 'products' collection: {len(all_records)}")
        for r in all_records:
            print(f"           - [{r.id}]  {r.name.value!r}  ({r.review_status})")
    except Exception as err:
        print(f"[ERROR]  list_product_records() failed: {err}")

    # ── 6. List FLAGGED products ──────────────────────────────────────────
    print("\n[Step 5] Listing only 'flagged' products...")
    try:
        flagged_records = list_product_records(review_status="flagged")
        print(f"         [OK] Flagged products: {len(flagged_records)}")
        if flagged_records:
            for r in flagged_records:
                print(f"           - [{r.id}]  {r.name.value!r}")
        else:
            print("           (none — the drill has no conflicting fields)")
    except Exception as err:
        print(f"[ERROR]  list_product_records(flagged) failed: {err}")

    # ── 7. Update review status ───────────────────────────────────────────
    print(f"\n[Step 6] Patching review_status to 'approved' on '{doc_id}'...")
    try:
        update_review_status(doc_id, "approved")
        # Confirm the patch landed
        patched = get_product_record(doc_id)
        print(f"         [OK] review_status is now: {patched.review_status!r}")
    except Exception as err:
        print(f"[ERROR]  update_review_status() failed: {err}")

    print("\n" + "=" * 62)
    print("   Smoke test complete.")
    print("=" * 62)
