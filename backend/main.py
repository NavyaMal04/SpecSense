"""
backend/main.py
================
FastAPI backend service for SpecSense.
Provides RESTful API endpoints for catalog product browsing, live AI enrichments,
product detail updates, bulk operations, and CSV/JSON export generation.
"""

import os
import sys
import glob
import json
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure project root is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import data_access as da  # noqa: E402
from pipeline.schema import ProductRecord, to_delivery_format_row, DELIVERY_FORMAT_HEADERS  # noqa: E402

app = FastAPI(
    title="SpecSense Product Intelligence API",
    description="AI-powered product datasheet extraction, similarity inference, and commerce catalog API.",
    version="1.0.0",
)

# CORS middleware for web frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StatusUpdateRequest(BaseModel):
    status: str


class BulkStatusRequest(BaseModel):
    mpns: List[str]
    status: str


class SingleEnrichmentRequest(BaseModel):
    mfg_part_num: str
    part_desc: Optional[str] = ""
    part_manuf: Optional[str] = ""
    e1_brand: Optional[str] = "-- Unbranded --"


@app.get("/")
def read_root():
    return {
        "status": "active",
        "service": "SpecSense Product Intelligence API",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.get("/api/products")
def get_products(
    query: Optional[str] = Query(None, description="Search query by MPN, Manufacturer, or Brand"),
    status: Optional[str] = Query("All", description="Filter by review status (pending, approved, flagged)"),
    sort_by: Optional[str] = Query("completeness_desc", description="Sort order"),
):
    records = da.load_all_records()
    results = []

    for mpn, rec in records:
        mfr = da.field_get(rec, "manufacturer_name").get("value") or ""
        brand = da.field_get(rec, "brand_name").get("value") or ""
        rec_status = rec.get("review_status", "pending")

        if status != "All" and rec_status != status:
            continue
        if query and query.lower() not in f"{mpn} {mfr} {brand}".lower():
            continue

        results.append({
            "mpn": mpn,
            "part_desc": rec.get("part_desc") or "",
            "manufacturer": mfr,
            "brand": brand,
            "completeness": da.record_completeness(rec),
            "fields_found": rec.get("fields_found_count", 0),
            "fields_total": rec.get("fields_total_count", 60),
            "review_status": rec_status,
        })

    if sort_by == "completeness_desc":
        results.sort(key=lambda x: x["completeness"], reverse=True)
    elif sort_by == "completeness_asc":
        results.sort(key=lambda x: x["completeness"])
    elif sort_by == "mpn_asc":
        results.sort(key=lambda x: x["mpn"].lower())

    return {"total": len(results), "products": results}


@app.get("/api/products/{mpn}")
def get_product_detail(mpn: str):
    rec = da.load_record(mpn)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Product record '{mpn}' not found.")
    
    provenance = da.calculate_provenance_stats([(mpn, rec)])
    return {"mpn": mpn, "record": rec, "provenance": provenance}


@app.put("/api/products/{mpn}")
def update_product_detail(mpn: str, record_dict: Dict[str, Any]):
    existing = da.load_record(mpn)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Product record '{mpn}' not found.")
    
    da.save_record(mpn, record_dict)
    return {"status": "success", "mpn": mpn, "message": f"Product '{mpn}' updated successfully."}


@app.patch("/api/products/{mpn}/status")
def update_product_status(mpn: str, req: StatusUpdateRequest):
    if req.status not in ("pending", "approved", "flagged"):
        raise HTTPException(status_code=400, detail="Invalid status value. Must be 'pending', 'approved', or 'flagged'.")
    
    rec = da.load_record(mpn)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Product record '{mpn}' not found.")

    rec["review_status"] = req.status
    da.save_record(mpn, rec)
    return {"status": "success", "mpn": mpn, "review_status": req.status}


@app.post("/api/bulk-status")
def bulk_update_status(req: BulkStatusRequest):
    if req.status not in ("pending", "approved", "flagged"):
        raise HTTPException(status_code=400, detail="Invalid status value.")
    
    updated_count = da.bulk_update_status(req.mpns, req.status)
    return {"status": "success", "updated_count": updated_count, "new_status": req.status}


@app.post("/api/enrich")
def enrich_single_product(req: SingleEnrichmentRequest):
    if not req.mfg_part_num.strip():
        raise HTTPException(status_code=400, detail="mfg_part_num is required.")

    raw_row = {
        "Mfg_Part_Num": req.mfg_part_num.strip(),
        "Part_Desc": (req.part_desc or "").strip(),
        "Part_Manuf": (req.part_manuf or "").strip(),
        "E1_Brand": (req.e1_brand or "-- Unbranded --").strip(),
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
    }

    try:
        enriched_rec = da.run_single_enrichment(raw_row, source_row_index=0)
        safe_mpn = "".join(c if c.isalnum() or c in "-_" else "_" for c in req.mfg_part_num.strip())
        rec_dict = enriched_rec.model_dump()
        da.save_record(safe_mpn, rec_dict)
        return {
            "status": "success",
            "mpn": safe_mpn,
            "completeness": da.record_completeness(rec_dict),
            "record": rec_dict,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment pipeline error: {str(e)}")


@app.get("/api/export/csv")
def export_delivery_csv(only_approved: bool = Query(False, description="Include only approved records")):
    records = da.load_all_records()
    if only_approved:
        records = [(m, r) for m, r in records if r.get("review_status") == "approved"]

    csv_bytes, failed = da.build_delivery_csv_bytes(records)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=delivery_format.csv"},
    )


@app.get("/api/export/json")
def export_catalog_json(only_approved: bool = Query(False, description="Include only approved records")):
    records = da.load_all_records()
    if only_approved:
        records = [(m, r) for m, r in records if r.get("review_status") == "approved"]

    json_bytes = da.export_records_json(records)
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=spec_sense_catalog.json"},
    )


@app.get("/api/telemetry")
def get_telemetry():
    records = da.load_all_records()
    summary = da.load_batch_summary()
    prov_stats = da.calculate_provenance_stats(records)
    sec_stats = da.calculate_section_completeness(records)

    return {
        "total_records": len(records),
        "provenance": prov_stats,
        "section_fill_rates": sec_stats,
        "batch_summary": summary,
    }
