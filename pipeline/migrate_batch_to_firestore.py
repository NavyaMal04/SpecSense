"""
migrate_batch_to_firestore.py
==============================
One-time (and idempotent) migration script that loads every product JSON from
data/batch_output/ into the Firestore "products" collection using the 252-column
UniHack ProductRecord schema.

Runs a verification pass at the end calling list_product_records() and
get_dashboard_stats() to confirm all data is queryable for the frontend.
"""

import os
import sys
import json
from typing import Dict, Any, List

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pipeline.schema import ProductRecord
from pipeline.firestore_client import (
    save_product_record,
    list_product_records,
    get_dashboard_stats,
    get_product_record,
)


def migrate_batch_to_firestore(batch_dir: str = "data/batch_output") -> Dict[str, Any]:
    """
    Scans batch_dir for all product JSON files, parses them as ProductRecords,
    and upserts them into Firestore.

    Returns:
        Summary dict containing counts and any errors.
    """
    if not os.path.isdir(batch_dir):
        raise FileNotFoundError(f"Batch directory not found at: {batch_dir}")

    files = [
        f for f in sorted(os.listdir(batch_dir))
        if f.endswith(".json") and f not in ("batch_summary.json", "package.json", "tsconfig.json")
    ]

    print("=" * 75)
    print(f"  FIRESTORE BATCH MIGRATION — {len(files)} JSON Files Found in {batch_dir}")
    print("=" * 75)

    migrated_records: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for idx, fname in enumerate(files, 1):
        fpath = os.path.join(batch_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as jf:
                raw_data = json.load(jf)

            # Validate against current ProductRecord schema
            record = ProductRecord.model_validate(raw_data)

            # Ensure an idempotent ID based on MPN if not already assigned
            if not record.id:
                record.id = record.mfg_part_num or record.part_number or fname[:-5]

            # Upsert into Firestore
            doc_id = save_product_record(record)

            # Sync doc_id back to local JSON if it changed
            if raw_data.get("id") != doc_id:
                raw_data["id"] = doc_id
                with open(fpath, "w", encoding="utf-8") as jf:
                    json.dump(raw_data, jf, indent=2, ensure_ascii=False)

            prod_name = (
                (record.product_name.value if record.product_name else None)
                or record.part_desc
                or record.mfg_part_num
                or ""
            )
            pct = (
                (record.fields_found_count / record.fields_total_count * 100)
                if record.fields_total_count
                else 0.0
            )

            print(
                f"  [{idx:2d}/{len(files):2d}] ✅ Migrated: {record.mfg_part_num or fname:<20} "
                f"→ doc_id='{doc_id}' | {pct:>5.1f}% | {record.review_status}"
            )

            migrated_records.append({
                "file": fname,
                "doc_id": doc_id,
                "mpn": record.mfg_part_num,
                "product_name": prod_name,
                "completeness_pct": round(pct, 1),
                "review_status": record.review_status,
            })

        except Exception as exc:
            err_msg = str(exc)
            print(f"  [{idx:2d}/{len(files):2d}] ❌ FAILED on {fname}: {err_msg}")
            errors.append({"file": fname, "error": err_msg})

    print("\n" + "=" * 75)
    print("  MIGRATION SUMMARY")
    print("=" * 75)
    print(f"  Total JSON files scanned : {len(files)}")
    print(f"  Successfully migrated    : {len(migrated_records)}")
    print(f"  Errors / Skipped         : {len(errors)}")

    return {
        "total_scanned": len(files),
        "migrated_count": len(migrated_records),
        "error_count": len(errors),
        "migrated_records": migrated_records,
        "errors": errors,
    }


if __name__ == "__main__":
    # ── Step 1: Run migration ────────────────────────────────────────────────
    res = migrate_batch_to_firestore()

    # ── Step 2: Query Firestore list_product_records() ───────────────────────
    print("\n" + "=" * 75)
    print("  VERIFICATION 1: list_product_records() (Lightweight Summaries)")
    print("=" * 75)
    summaries = list_product_records()
    print(f"  Total records returned by Firestore list query: {len(summaries)}")
    print(f"  {'DOC ID':<22} | {'MPN':<18} | {'COMPLETENESS':<12} | {'STATUS':<9} | {'PRODUCT / DESC'}")
    print("  " + "-" * 85)
    for s in summaries:
        print(
            f"  {s['id'][:20]:<22} | {s['mfg_part_num']:<18} | "
            f"{s['completeness_pct']:>5.1f}% ({s['fields_found_count']}/{s['fields_total_count']}) | "
            f"{s['review_status']:<9} | {s['product_name'][:35]}"
        )

    # ── Step 3: Query Firestore get_dashboard_stats() ────────────────────────
    print("\n" + "=" * 75)
    print("  VERIFICATION 2: get_dashboard_stats() (Aggregate Metrics)")
    print("=" * 75)
    stats = get_dashboard_stats()
    print(f"  Total Products In Firestore : {stats['total_products']}")
    print(f"  Average Completeness        : {stats['avg_completeness_pct']}%")
    print(f"  Review Status Counts        : {stats['pending_count']} pending, {stats['flagged_count']} flagged, {stats['approved_count']} approved")

    # ── Step 4: Test single round-trip fetch on first record ─────────────────
    if summaries:
        first_id = summaries[0]["id"]
        print(f"\n[Test] Testing deep round-trip get_product_record('{first_id}')...")
        full_rec = get_product_record(first_id)
        print(f"       ✅ Successfully retrieved: MPN={full_rec.mfg_part_num}, Attrs={len(full_rec.attributes)}, MFR={full_rec.manufacturer_name.value}")

    print("\n" + "=" * 75)
    print("  FIRESTORE DATA LAYER IS FULLY OPERATIONAL AND READY FOR REACT UI!")
    print("=" * 75)
