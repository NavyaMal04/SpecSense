"""
pipeline/reenrich_targeted.py
==============================
Re-enriches a prioritised list of MPNs from scratch using the current enricher.py
(strict manufacturer-only sourcing), then overwrites their JSON files and
Firestore documents.  Results are printed immediately as each row finishes —
don't wait for the whole list to complete.

Priority list (highest-impact first):
  PDSH4816AF, WDTS7024RZ, 65-1222, KDFM404KPS, 27233,
  ADB15516CS, FS_C01_2004S, 05134545001, 37418A

Usage:
    python -m pipeline.reenrich_targeted
"""

import os
import sys
import json
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pipeline.enricher import enrich_product_record, GEMINI_KEY_POOL
from pipeline.schema import ProductRecord
from pipeline.firestore_client import save_product_record

# ── Priority list of rows to re-enrich ───────────────────────────────────────
# Raw-row dicts matching the CSV column names enrich_product_record() expects.
# Listed highest-impact (most fields lost in prune) first.

TARGET_ROWS = [
    {
        "Mfg_Part_Num": "PDSH4816AF",
        "PART_NUMBER": "PDSH4816AF",
        "Part_Desc": "Frigidaire Professional 24'' Stainless Steel Tub Built-In Dishwasher with CleanBoost™",
        "E1_Brand": "Frigidaire",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "Frigidaire (FRIGR)",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
    {
        "Mfg_Part_Num": "WDTS7024RZ",
        "PART_NUMBER": "WDTS7024RZ",
        "Part_Desc": "WDTS7024RZ Dishwasher SS - Display Only",
        "E1_Brand": "-- Unbranded --",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "Whirlpool Corporation (WHIRL)",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
    {
        "Mfg_Part_Num": "65-1222",
        "PART_NUMBER": "65-1222",
        "Part_Desc": "LED 1' Connectable Strip Light",
        "E1_Brand": "-- Unbranded --",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "Satco Products Inc (SATCO)",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
    {
        "Mfg_Part_Num": "KDFM404KPS",
        "PART_NUMBER": "KDFM404KPS",
        "Part_Desc": "KitchenAid 44 dBA Dishwasher with FreeFlex Third Level Rack",
        "E1_Brand": "KitchenAid",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "KitchenAid / Whirlpool Corporation (KITAD)",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
    {
        "Mfg_Part_Num": "27233",
        "PART_NUMBER": "27233",
        "Part_Desc": "27233 Product",
        "E1_Brand": "-- Unbranded --",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
    {
        "Mfg_Part_Num": "ADB15516CS",
        "PART_NUMBER": "ADB15516CS",
        "Part_Desc": "ADB15516CS Dishwasher",
        "E1_Brand": "-- Unbranded --",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
    {
        "Mfg_Part_Num": "FS_C01_2004S",
        "PART_NUMBER": "FS_C01_2004S",
        "Part_Desc": "FS C01 2004S Product",
        "E1_Brand": "-- Unbranded --",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
    {
        "Mfg_Part_Num": "05134545001",
        "PART_NUMBER": "05134545001",
        "Part_Desc": "9516 Kneeling Pad & Bottle Opener",
        "E1_Brand": "Wera",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "Wera Tools NA Inc (WERTO)",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
    {
        "Mfg_Part_Num": "37418A",
        "PART_NUMBER": "37418A",
        "Part_Desc": "37418A Product",
        "E1_Brand": "-- Unbranded --",
        "Unilog_Brand": "-- No Unilog Brand --",
        "DIB_Brand": "-- No DIB Brand --",
        "Part_Manuf": "",
        "Dept": None, "Class": None, "Fine": None, "SKU - MY_PART_NUMBER": None,
    },
]


def _find_batch_dir() -> str:
    for candidate in [".", "..", os.path.dirname(__file__), os.path.join(os.path.dirname(__file__), "..")]:
        p = os.path.join(candidate, "data", "batch_output")
        if os.path.isdir(p):
            return p
    return "data/batch_output"


def _load_before_stats(batch_dir: str, mpn: str) -> tuple:
    """Return (fields_found, fields_total) from the current saved JSON, or (0,0)."""
    fp = os.path.join(batch_dir, f"{mpn}.json")
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("fields_found_count", 0), d.get("fields_total_count", 0)
    return 0, 0


def run_reenrichment():
    batch_dir = _find_batch_dir()
    total = len(TARGET_ROWS)
    W = 100

    print("=" * W)
    print(f"  TARGETED RE-ENRICHMENT — {total} rows, highest-impact first")
    print(f"  Key pool: {len(GEMINI_KEY_POOL)} key(s) → ~{len(GEMINI_KEY_POOL) * 20} req/day capacity")
    print(f"  Batch dir: {batch_dir}")
    print("=" * W)
    sys.stdout.flush()

    summary_rows = []

    for idx, row in enumerate(TARGET_ROWS, 1):
        mpn = row["Mfg_Part_Num"]
        before_found, before_total = _load_before_stats(batch_dir, mpn)
        before_pct = (before_found / before_total * 100) if before_total else 0.0

        print(f"\n{'─'*W}")
        print(f"  [{idx}/{total}] ▶  {mpn}  |  before: {before_found}/{before_total} ({before_pct:.1f}%)")
        print(f"{'─'*W}")
        sys.stdout.flush()

        try:
            record: ProductRecord = enrich_product_record(row, source_row_index=idx - 1)

            # Set stable doc ID = MPN for idempotent upsert
            record.id = mpn

            after_found = record.fields_found_count or 0
            after_total = record.fields_total_count or 0
            after_pct = (after_found / after_total * 100) if after_total else 0.0
            delta = after_found - before_found

            # Persist JSON
            json_path = os.path.join(batch_dir, f"{mpn}.json")
            record_dict = record.model_dump()
            record_dict["id"] = mpn
            with open(json_path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(record_dict, f, indent=2, ensure_ascii=False, default=str)

            # Push to Firestore
            doc_id = save_product_record(record)

            # Key sourcing snapshot
            mfr_val = record.manufacturer_name.value if record.manufacturer_name else "None"
            mfr_src = record.manufacturer_name.source_url if record.manufacturer_name else "None"
            mfr_url = record.mfr_url.value if record.mfr_url else "None"
            ref_count = len(record.ref_urls or [])

            print(f"  ✅  DONE — after: {after_found}/{after_total} ({after_pct:.1f}%)  Δ={delta:+d}")
            print(f"       manufacturer_name : {mfr_val!r}")
            print(f"       source_url        : {mfr_src}")
            print(f"       mfr_url           : {mfr_url}")
            print(f"       ref_urls kept     : {ref_count}")
            print(f"       Firestore doc_id  : {doc_id!r}")
            sys.stdout.flush()

            summary_rows.append({
                "mpn": mpn, "status": "✅ OK",
                "before_pct": round(before_pct, 1),
                "after_pct": round(after_pct, 1),
                "delta": delta, "doc_id": doc_id,
            })

        except Exception as exc:
            err = str(exc)[:80]
            print(f"  ❌  FAILED — {err}")
            sys.stdout.flush()
            summary_rows.append({"mpn": mpn, "status": "❌ ERROR", "error": str(exc)})

    # ── Final table ──
    print(f"\n{'='*W}")
    print("  FINAL SUMMARY")
    print(f"{'='*W}")
    print(f"  {'#':<3} {'MPN':<22} {'Before':>8} {'After':>8} {'Δ':>6}  {'Status'}")
    print("  " + "-" * 65)
    for i, r in enumerate(summary_rows, 1):
        if r["status"].startswith("✅"):
            print(
                f"  {i:<3} {r['mpn']:<22} {r['before_pct']:>6.1f}%  {r['after_pct']:>6.1f}%  "
                f"{r['delta']:>+5}  {r['status']}"
            )
        else:
            print(f"  {i:<3} {r['mpn']:<22} {'—':>8} {'—':>8} {'—':>6}  {r['status']}  {r.get('error','')[:35]}")
    ok = sum(1 for r in summary_rows if r["status"].startswith("✅"))
    print(f"\n  {ok}/{total} rows succeeded.")
    print("=" * W)


if __name__ == "__main__":
    run_reenrichment()
