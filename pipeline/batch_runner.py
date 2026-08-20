import os
import sys
import json
import re
import csv
import time
from datetime import datetime, timezone

# Force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pipeline.enricher import (
    enrich_product_record,
    RETRY_STATS,
    AllKeys429Error,
    print_key_usage_report,
    KEY_STATS,
    GEMINI_KEY_POOL,
)
from pipeline.schema import ProductRecord

# Target sample MPNs representing 5 diverse categories
TARGET_MPNS = [
    # Appliances
    'WDTS7024RZ', 'PDSH4816AF', 'KDFM404KPS', 'D519127',
    # Tools & Accessories
    '49-94-0013', '05134545001', 'LNL65301',
    # Abrasives & Sanding
    'DCB518ASTS06G', '3MABR-7100075678', '5B-332-080',
    # Electrical & Hardware
    '1700-1PK-BB40', '413S-DBA-36', '402-R',
    # Building Materials & Fixtures
    'FS C01 2004S', 'ADB15516CS', '27233', 'PP-8BL'
]


def run_batch(resume: bool = True):
    """Run the batch enrichment over TARGET_MPNS.
    
    Args:
        resume: If True (default), skip MPNs that already have a JSON output file
                in data/batch_output/ — allows safe re-runs after quota resets.
    """
    start_wall_time = time.time()
    output_dir = os.path.join("data", "batch_output")
    os.makedirs(output_dir, exist_ok=True)

    input_csv = os.path.join("data", "samples", "Unihack_ Sample Dataset - Input.csv")
    with open(input_csv, encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f))

    # Filter target rows
    target_rows = []
    for mpn in TARGET_MPNS:
        match = next((r for r in all_rows if r.get("Mfg_Part_Num") == mpn), None)
        if match:
            target_rows.append(match)

    print("=" * 75)
    print(f"  BATCH ENRICHMENT RUNNER — {len(target_rows)} Rows Selected Across 5 Categories")
    print("=" * 75)

    results_summary = []
    errors = []
    flagged_count = 0
    pending_count = 0
    total_pct_sum = 0.0
    total_fields_found_sum = 0

    skipped = []
    for idx, row in enumerate(target_rows, 1):
        mpn = row.get("Mfg_Part_Num", f"row_{idx}")
        desc = row.get("Part_Desc", "")[:45]
        manuf = row.get("Part_Manuf", "")
        safe_mpn = re.sub(r'[/\\:*?"<>| ]', '_', mpn)
        json_filepath = os.path.join(output_dir, f"{safe_mpn}.json")

        # Resume mode: skip rows already completed in a prior run
        if resume and os.path.exists(json_filepath):
            print(f"\n[{idx}/{len(target_rows)}] SKIPPING (already done): {mpn}")
            skipped.append(mpn)
            continue

        # Pacing delay between rows (2.5s) to reduce rate-limit pressure
        if idx > 1 and not (resume and len(skipped) == idx - 1):  # no delay after skipped rows
            time.sleep(2.5)

        print(f"\n[{idx}/{len(target_rows)}] Processing: {mpn} | {manuf} | {desc}...")

        try:
            rec = enrich_product_record(row, source_row_index=idx - 1)

            # Save JSON to output folder
            json_filename = f"{safe_mpn}.json"
            json_filepath = os.path.join(output_dir, json_filename)
            with open(json_filepath, "w", encoding="utf-8") as jf:
                json.dump(rec.model_dump(), jf, indent=2, ensure_ascii=False)

            pct = (rec.fields_found_count / rec.fields_total_count * 100) if rec.fields_total_count else 0
            total_pct_sum += pct
            total_fields_found_sum += rec.fields_found_count

            if rec.review_status == "flagged":
                flagged_count += 1
            else:
                pending_count += 1

            unresolved = rec.unresolved_taxonomy_labels or []

            row_summary = {
                "mpn": mpn,
                "safe_mpn": safe_mpn,
                "part_manuf": manuf,
                "part_desc": row.get("Part_Desc"),
                "resolved_mfr": rec.manufacturer_name.value,
                "resolved_brand": rec.brand_name.value,
                "mfr_url": rec.mfr_url.value,
                "fields_found_count": rec.fields_found_count,
                "fields_total_count": rec.fields_total_count,
                "found_pct": round(pct, 1),
                "review_status": rec.review_status,
                "attributes_count": len(rec.attributes),
                "unresolved_taxonomy_count": len(unresolved),
                "unresolved_taxonomy_labels": unresolved,
                "json_file": json_filepath
            }
            results_summary.append(row_summary)

            print(f"    ✅ Saved to {json_filepath}")
            print(f"       MFR: {rec.manufacturer_name.value} | Brand: {rec.brand_name.value}")
            print(f"       Found: {rec.fields_found_count}/{rec.fields_total_count} ({pct:.1f}%) | Status: {rec.review_status} | Attrs: {len(rec.attributes)}")
            print(f"       Unresolved Taxonomy ({len(unresolved)}): {', '.join(unresolved[:5])}{'...' if len(unresolved) > 5 else ''}")

        except AllKeys429Error as quota_exc:
            err_msg = str(quota_exc)
            print(f"    ⛔ ALL KEYS QUOTA EXHAUSTED for {mpn} — skipping row gracefully.")
            print(f"       {err_msg[:200]}")
            errors.append({"mpn": mpn, "error": f"AllKeys429: {err_msg[:300]}"})

        except Exception as exc:
            err_msg = str(exc)
            print(f"    ⛔ ERROR processing {mpn}: {err_msg}")
            errors.append({"mpn": mpn, "error": err_msg})

    elapsed_wall_time = time.time() - start_wall_time
    total_processed = len(results_summary)
    avg_pct = (total_pct_sum / total_processed) if total_processed > 0 else 0.0
    avg_fields_found = (total_fields_found_sum / total_processed) if total_processed > 0 else 0.0

    if skipped:
        print(f"\n  ℹ️  Skipped {len(skipped)} already-complete rows (resume mode): {', '.join(skipped)}")

    # Add per-key call distribution to the report
    key_usage = {f"key_{i+1}": KEY_STATS.get(i, 0) for i in range(len(GEMINI_KEY_POOL))}

    batch_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_attempted": len(target_rows),
        "total_processed": total_processed,
        "total_errored": len(errors),
        "total_skipped": len(skipped),
        "skipped_mpns": skipped,
        "avg_found_pct": round(avg_pct, 1),
        "avg_fields_found_count": round(avg_fields_found, 1),
        "total_wall_clock_seconds": round(elapsed_wall_time, 2),
        "total_wall_clock_formatted": f"{int(elapsed_wall_time // 60)}m {int(elapsed_wall_time % 60)}s",
        "review_status_counts": {
            "pending": pending_count,
            "flagged": flagged_count
        },
        "retry_statistics": {
            "total_calls": RETRY_STATS["total_calls"],
            "total_retries": RETRY_STATS["total_retries"],
            "rows_requiring_retries_count": len(RETRY_STATS["rows_with_retries"]),
            "rows_requiring_retries_list": list(RETRY_STATS["rows_with_retries"])
        },
        "key_usage_distribution": key_usage,
        "errors": errors,
        "rows": results_summary
    }

    summary_file = os.path.join(output_dir, "batch_summary.json")
    with open(summary_file, "w", encoding="utf-8") as sf:
        json.dump(batch_report, sf, indent=2, ensure_ascii=False)

    print("\n" + "=" * 75)
    print("  BATCH ENRICHMENT COMPLETE — AGGREGATE METRICS")
    print("=" * 75)
    print(f"  Total Attempted    : {len(target_rows)}")
    print(f"  Total Skipped      : {len(skipped)} (resume: already done)")
    print(f"  Total Processed    : {total_processed}")
    print(f"  Total Errors       : {len(errors)}")
    print(f"  Avg Fields Found   : {avg_fields_found:.1f}")
    print(f"  Avg Completeness   : {avg_pct:.1f}%")
    print(f"  Status Counts      : {pending_count} pending, {flagged_count} flagged")
    print(f"  Total API Calls    : {RETRY_STATS['total_calls']}")
    print(f"  Total Retries      : {RETRY_STATS['total_retries']}")
    print(f"  Rows Retried       : {len(RETRY_STATS['rows_with_retries'])}")
    print(f"  Wall-Clock Time    : {int(elapsed_wall_time // 60)}m {int(elapsed_wall_time % 60)}s ({elapsed_wall_time:.1f}s)")
    print_key_usage_report()
    print(f"  Summary Saved      : {summary_file}")


if __name__ == "__main__":
    run_batch()
