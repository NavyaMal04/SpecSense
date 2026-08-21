"""
frontend/data_access.py
========================
All file I/O and pipeline calls the UI needs, in one place, so pages
stay thin. The local JSON files in data/batch_output/ are the source
of truth (this is what batch_runner.py already writes to and what
batch_summary.json can go stale relative to) — every page reads live
from disk rather than trusting cached summary stats.
"""

import glob
import json
import os
import sys
from typing import Optional

# Make the project root importable regardless of Streamlit's cwd
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.schema import ProductRecord, to_delivery_format_row, DELIVERY_FORMAT_HEADERS  # noqa: E402

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "batch_output")
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "batch_summary.json")

# Fields whose FieldValue.value is typed float in the schema — everything else
# that's FieldValue-shaped is expected to be a string.
_NUMERIC_FIELDS = {"list_price", "length", "height", "width", "weight", "volume"}


def sanitize_record_dict(data: dict) -> tuple:
    """
    Defensively coerces malformed field types before ProductRecord validation.
    The Gemini extraction occasionally returns a list (e.g. multiple
    certifications) or a bool where the schema expects a plain string —
    this repairs those in place rather than letting the whole record fail
    validation and silently vanish from the CSV export.

    Returns (sanitized_dict, list_of_field_names_that_were_fixed).
    """
    fixed = []
    for key, val in list(data.items()):
        if not isinstance(val, dict) or "value" not in val or "source_type" not in val:
            continue  # not a FieldValue-shaped entry (e.g. part_number, ref_urls, attributes)
        v = val.get("value")
        if v is None or key in _NUMERIC_FIELDS:
            continue
        if isinstance(v, list):
            val["value"] = "; ".join(str(x) for x in v if x is not None) or None
            fixed.append(key)
        elif isinstance(v, bool):
            val["value"] = "Yes" if v else "No"
            fixed.append(key)
        elif not isinstance(v, str):
            val["value"] = str(v)
            fixed.append(key)
    return data, fixed

SCALAR_SECTIONS = {
    "Enriched Identity": [
        ("manufacturer_name", "Manufacturer Name"),
        ("brand_name", "Brand Name"),
        ("trade_name", "Trade Name"),
        ("manufacturer_part_number", "Manufacturer Part Number"),
        ("alternate_part_number", "Alternate Part Number"),
        ("classpath", "Classpath"),
        ("mfr_url", "Manufacturer URL"),
    ],
    "Descriptions": [
        ("mobile_desc", "Mobile Description"),
        ("invoice_desc", "Invoice Description"),
        ("short_desc", "Short Description"),
        ("long_desc1", "Long Description"),
        ("retail_desc", "Retail Description"),
        ("marketing_description", "Marketing Description"),
    ],
    "Modifiers": [
        ("with_features", "With"),
        ("standard_approvals", "Standard / Approvals"),
        ("prop_65", "Prop 65"),
        ("application", "Application"),
        ("includes", "Includes"),
        ("product_name", "Product Name"),
    ],
    "Identifiers": [
        ("upc", "UPC"),
        ("ean", "EAN"),
        ("gtin", "GTIN"),
        ("unspsc", "UNSPSC"),
    ],
    "Commercial": [
        ("warranty", "Warranty"),
        ("list_price", "List Price"),
        ("selling_qty", "Selling Qty"),
        ("selling_uom", "Selling UOM"),
        ("standard_packaging_info", "Standard Packaging Info"),
    ],
    "Dimensions": [
        ("length", "Length"), ("length_uom", "Length UOM"),
        ("height", "Height"), ("height_uom", "Height UOM"),
        ("width", "Width"), ("width_uom", "Width UOM"),
        ("weight", "Weight"), ("weight_uom", "Weight UOM"),
        ("volume", "Volume"), ("volume_uom", "Volume UOM"),
    ],
    "Misc": [
        ("country_of_origin", "Country of Origin"),
        ("discontinued", "Discontinued"),
        ("actual_image_yn", "Actual Image (Y/N)"),
    ],
}

IDENTITY_PASSTHROUGH = [
    ("part_number", "Part Number"), ("dept", "Dept"), ("product_class", "Class"),
    ("fine_class", "Fine"), ("sku", "SKU"), ("mfg_part_num", "Mfg Part Num"),
    ("part_desc", "Part Desc"), ("e1_brand", "E1 Brand"), ("unilog_brand", "Unilog Brand"),
    ("dib_brand", "DIB Brand"), ("part_manuf", "Part Manuf"),
]


def list_record_files() -> list:
    """All product JSON files on disk, excluding the batch summary."""
    if not os.path.isdir(OUTPUT_DIR):
        return []
    files = glob.glob(os.path.join(OUTPUT_DIR, "*.json"))
    return sorted(f for f in files if os.path.basename(f) != "batch_summary.json")


# Populated by load_all_records() on every call — MPNs whose stored JSON
# needed defensive type coercion before it would validate against ProductRecord.
# Exposed here (rather than only logged) so the API layer can surface it if needed.
last_sanitized_log: dict = {}


def load_all_records() -> list:
    """Returns [(mpn, record_dict), ...] for every product JSON on disk.
    Malformed field types are auto-corrected (see sanitize_record_dict);
    corrections are tracked in `last_sanitized_log` rather than silently
    hiding the issue."""
    global last_sanitized_log

    records = []
    sanitized_log = {}
    for path in list_record_files():
        mpn = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        data, fixed = sanitize_record_dict(raw)
        if fixed:
            sanitized_log[mpn] = fixed
        records.append((mpn, data))

    last_sanitized_log = sanitized_log
    return records


def load_record(mpn: str) -> Optional[dict]:
    path = os.path.join(OUTPUT_DIR, f"{mpn}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    data, _fixed = sanitize_record_dict(raw)
    return data


def save_record(mpn: str, record_dict: dict) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{mpn}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record_dict, f, indent=2, ensure_ascii=False)


def load_batch_summary() -> Optional[dict]:
    if not os.path.exists(SUMMARY_PATH):
        return None
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def record_completeness(record_dict: dict) -> float:
    found = record_dict.get("fields_found_count")
    total = record_dict.get("fields_total_count")
    if not found or not total:
        return 0.0
    return round(100 * found / total, 1)


def field_get(record_dict: dict, field_name: str) -> dict:
    """Safe accessor for a FieldValue sub-dict, tolerating missing/None fields."""
    f = record_dict.get(field_name)
    if not isinstance(f, dict):
        return {"value": None, "source_type": "unavailable", "confidence": 0.0, "source_url": None, "source_snippet": None}
    return f


def build_delivery_csv_bytes(record_dicts: list) -> tuple:
    """Build the full 252-column delivery CSV from a list of record dicts.
    Returns (csv_bytes, failed_mpns) — failures are surfaced to the caller
    rather than silently dropped from the export."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=DELIVERY_FORMAT_HEADERS)
    writer.writeheader()
    failed = []
    for mpn, data in record_dicts:
        try:
            rec = ProductRecord(**data)
            writer.writerow(to_delivery_format_row(rec))
        except Exception as e:
            failed.append((mpn, str(e)[:200]))
    return buf.getvalue().encode("utf-8-sig"), failed


def run_single_enrichment(raw_row: dict, source_row_index: int = 0):
    """Calls the real pipeline enrichment function. Raises on failure (quota, network, etc.) — caller should catch."""
    from pipeline.enricher import enrich_product_record
    return enrich_product_record(raw_row, source_row_index=source_row_index)


def calculate_provenance_stats(records: list) -> dict:
    """
    Calculates aggregate provenance breakdown (extracted vs inferred vs unavailable)
    across all loaded product records.
    """
    counts = {"extracted": 0, "inferred": 0, "unavailable": 0, "total_fields": 0}

    for _mpn, rec in records:
        for section, fields in SCALAR_SECTIONS.items():
            for key, _label in fields:
                fv = field_get(rec, key)
                stype = fv.get("source_type", "unavailable")
                if fv.get("value") is not None and stype in ("extracted", "verified"):
                    counts["extracted"] += 1
                elif fv.get("value") is not None and stype == "inferred":
                    counts["inferred"] += 1
                else:
                    counts["unavailable"] += 1
                counts["total_fields"] += 1

    total = counts["total_fields"] or 1
    return {
        "extracted_pct": round(100 * counts["extracted"] / total, 1),
        "inferred_pct": round(100 * counts["inferred"] / total, 1),
        "unavailable_pct": round(100 * counts["unavailable"] / total, 1),
        "counts": counts,
    }


def calculate_section_completeness(records: list) -> dict:
    """Calculates fill rate (%) per section across all records."""
    if not records:
        return {sec: 0.0 for sec in SCALAR_SECTIONS.keys()}

    section_stats = {sec: {"filled": 0, "total": 0} for sec in SCALAR_SECTIONS.keys()}

    for _mpn, rec in records:
        for sec, fields in SCALAR_SECTIONS.items():
            for key, _label in fields:
                fv = field_get(rec, key)
                section_stats[sec]["total"] += 1
                if fv.get("value") is not None:
                    section_stats[sec]["filled"] += 1

    return {
        sec: round(100 * data["filled"] / (data["total"] or 1), 1)
        for sec, data in section_stats.items()
    }


def bulk_update_status(mpn_list: list, new_status: str) -> int:
    """Updates review_status for a list of MPNs and saves to disk."""
    updated = 0
    for mpn in mpn_list:
        rec = load_record(mpn)
        if rec:
            rec["review_status"] = new_status
            save_record(mpn, rec)
            updated += 1
    return updated


def export_records_json(records: list) -> bytes:
    """Returns formatted JSON bytes of all provided records."""
    catalog = [rec for _mpn, rec in records]
    return json.dumps(catalog, indent=2, ensure_ascii=False).encode("utf-8")


def compare_records(mpn_list: list) -> list:
    """
    Returns loaded records for the specified MPNs for comparison.
    """
    results = []
    for mpn in mpn_list:
        rec = load_record(mpn)
        if rec:
            results.append((mpn, rec))
    return results

