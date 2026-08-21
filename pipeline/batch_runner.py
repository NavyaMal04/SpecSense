import os
import sys
import json
import re
import csv
import time
import argparse
from collections import Counter, defaultdict
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

# ── Legacy hard-coded 17-row test set (kept for reference) ──────────────────
TARGET_MPNS_LEGACY = [
    'WDTS7024RZ', 'PDSH4816AF', 'KDFM404KPS', 'D519127',
    '49-94-0013', '05134545001', 'LNL65301',
    'DCB518ASTS06G', '3MABR-7100075678', '5B-332-080',
    '1700-1PK-BB40', '413S-DBA-36', '402-R',
    'FS C01 2004S', 'ADB15516CS', '27233', 'PP-8BL'
]

# ── Category classification ──────────────────────────────────────────────────
# Priority order determines category resolution when multiple match.
CATEGORY_KEYWORDS = [
    ("appliance",  ["dishwasher", "refrigerator", "washer", "dryer", "microwave",
                    "range", "oven", "freezer", "heater kit", "appliance", "cooktop",
                    "garbage disposal", "compactor"]),
    ("abrasive",   ["sanding", "abrasive", "sandpaper", "cubitron", "stikit",
                    "disc", "belt", "grinding wheel", "cut-off", "cutoff", "cut off",
                    "flap disc", "fiber disc"]),
    ("tool",       ["drill", "driver", "saw blade", "plier", "wrench", "screwdriver",
                    "hammer", "chisel", "router bit", "grinder", "cutter", "kneeling",
                    "wera", "tool kit", "hex key", "ratchet", "socket"]),
    ("fastener",   ["screw", "bolt", "nut ", "anchor", "rivet", "washer",
                    "pin ", "clip", "bracket", "hinge", "threshold", "toggle"]),
    ("electrical", ["vinyl tape", "elect tape", "wire", "cable", "conduit",
                    "circuit breaker", "switch", "outlet", "panel", "battery",
                    "voltage", "fuse", "connector", "terminal", "wire nut"]),
    ("lighting",   ["light", "led", "lamp", "bulb", "fixture", "luminaire",
                    "fluorescent", "ballast", "lantern", "troffer", "downlight"]),
    ("building",   ["lumber", "board", "panel", "door", "skylight", "roofing",
                    "flooring", "trim", "molding", "drywall", "insulation",
                    "azek", "pvc deck", "composite", "decking", "attic"]),
    ("hvac",       ["hvac", "duct", "damper", "filter", "coil", "furnace",
                    "thermostat", "vent", "blower", "air handler"]),
    ("plumbing",   ["faucet", "valve", "fitting", "pipe", "coupling", "tee",
                    "elbow", "reducer", "manifold", "shut-off", "drain", "toilet"]),
]

# Minimum rows per category to bother including it in the selection
MIN_CATEGORY_SIZE = 5


def classify_row(part_desc: str, part_manuf: str = "") -> str:
    """Keyword-based category classifier. Returns the first matching category or 'other'."""
    text = (part_desc + " " + part_manuf).lower()
    for cat, keywords in CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return cat
    return "other"


def get_already_done(output_dir: str) -> set:
    """
    Build a set of MPNs already completed by scanning output_dir for *.json files.
    """
    done = set()
    summary_path = os.path.join(output_dir, "batch_summary.json")
    if os.path.exists(summary_path):
        try:
            with open(summary_path, encoding="utf-8") as f:
                summary = json.load(f)
            for row in summary.get("rows", []):
                if row.get("mpn"):
                    done.add(str(row["mpn"]).strip())
        except Exception:
            pass
    if os.path.isdir(output_dir):
        for fname in os.listdir(output_dir):
            if fname.endswith(".json") and fname not in ("batch_summary.json", "package.json", "tsconfig.json"):
                safe_stem = fname[:-5]
                try:
                    fpath = os.path.join(output_dir, fname)
                    with open(fpath, encoding="utf-8") as jf:
                        data = json.load(jf)
                    raw_mpn = data.get("mfg_part_num") or data.get("part_number") or data.get("mpn")
                    if isinstance(raw_mpn, dict):
                        raw_mpn = raw_mpn.get("value")
                    if raw_mpn:
                        done.add(str(raw_mpn).strip())
                    else:
                        done.add(safe_stem)
                except Exception:
                    done.add(safe_stem)
    return done


def select_batch_rows(
    input_csv_path: str,
    target_count: int = 70,
    already_done: set = None,
) -> tuple[list[dict], dict]:
    """
    Load the full input CSV, classify every row into a category, then select
    rows proportionally across categories up to target_count.

    Args:
        input_csv_path: Path to the 1000-row input CSV.
        target_count:   Total number of rows to return.
        already_done:   Set of MPNs already processed (will be excluded).

    Returns:
        (selected_rows, category_counts) — the row list and a dict showing
        how many rows per category were selected.
    """
    if already_done is None:
        already_done = set()

    with open(input_csv_path, encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f))

    # Classify every row and bucket by category (excluding already-done MPNs)
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in all_rows:
        mpn = row.get("Mfg_Part_Num", "").strip()
        if not mpn or mpn in already_done:
            continue
        cat = classify_row(row.get("Part_Desc", ""), row.get("Part_Manuf", ""))
        buckets[cat].append(row)

    # Drop thin categories that wouldn't demo well
    eligible = {cat: rows for cat, rows in buckets.items() if len(rows) >= MIN_CATEGORY_SIZE}
    # Cap the 'other' bucket to at most 15% of target_count to keep selection diverse
    other_cap = max(5, round(target_count * 0.15))
    if "other" in eligible:
        eligible["other"] = eligible["other"][:other_cap]
    total_eligible = sum(len(v) for v in eligible.values())

    # Proportional allocation — at least 1 row per eligible category
    selected: list[dict] = []
    category_counts: dict[str, int] = {}
    remaining = target_count

    # Sort categories largest-first for stable allocation
    sorted_cats = sorted(eligible.items(), key=lambda x: -len(x[1]))
    for i, (cat, rows) in enumerate(sorted_cats):
        cats_left = len(sorted_cats) - i
        alloc = max(1, round(len(rows) / total_eligible * target_count))
        alloc = min(alloc, remaining - (cats_left - 1), len(rows))
        alloc = max(1, alloc)
        selected.extend(rows[:alloc])
        category_counts[cat] = alloc
        remaining -= alloc
        if remaining <= 0:
            break

    # If we're short (rounding), top up from the largest category
    while len(selected) < target_count:
        for cat, rows in sorted_cats:
            already_in = category_counts.get(cat, 0)
            if already_in < len(rows):
                selected.append(rows[already_in])
                category_counts[cat] = already_in + 1
                if len(selected) >= target_count:
                    break

    return selected[:target_count], category_counts


def _append_progress_log(output_dir: str, mpn: str, category: str,
                          pct: float, status: str, error: str = "") -> None:
    """Append one line to progress_log.txt after each row is processed."""
    log_path = os.path.join(output_dir, "progress_log.txt")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if error:
        line = f"{ts} | {mpn:<22} | {category:<12} | {'ERROR':>6}% | {status:<12} | {error[:80]}\n"
    else:
        line = f"{ts} | {mpn:<22} | {category:<12} | {pct:>5.1f}% | {status:<12}\n"
    with open(log_path, "a", encoding="utf-8") as lf:
        lf.write(line)


def run_batch(target_count: int = 70, resume: bool = True, legacy_mode: bool = False):
    """
    Main batch enrichment runner.

    Args:
        target_count:  Number of rows to select from the full CSV (default 70).
        resume:        Skip MPNs whose JSON already exists in data/batch_output/.
        legacy_mode:   If True, use the hard-coded 17-row TARGET_MPNS_LEGACY list
                       instead of the proportional CSV selection.
    """
    start_wall_time = time.time()
    output_dir = os.path.join("data", "batch_output")
    os.makedirs(output_dir, exist_ok=True)
    input_csv = os.path.join("data", "samples", "Unihack_ Sample Dataset - Input.csv")

    # ── Build already-done set ───────────────────────────────────────────────
    already_done = get_already_done(output_dir) if resume else set()

    # ── Select target rows ───────────────────────────────────────────────────
    if legacy_mode:
        with open(input_csv, encoding="utf-8-sig") as f:
            all_rows = list(csv.DictReader(f))
        mpn_index = {r["Mfg_Part_Num"]: r for r in all_rows}
        target_rows = [mpn_index[m] for m in TARGET_MPNS_LEGACY if m in mpn_index]
        category_counts = {"legacy": len(target_rows)}
    else:
        target_rows, category_counts = select_batch_rows(
            input_csv, target_count=target_count, already_done=already_done
        )

    print("=" * 75)
    print(f"  BATCH ENRICHMENT RUNNER — {len(target_rows)} rows selected (target={target_count})")
    print(f"  Mode: {'legacy 17-row' if legacy_mode else 'proportional CSV selection'}")
    print(f"  Resume: {resume} | Already done: {len(already_done)} rows")
    print("  Category allocation:")
    for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat:<14}: {cnt:>3} rows")
    print("=" * 75)

    # Write a run header to progress_log.txt
    log_path = os.path.join(output_dir, "progress_log.txt")
    run_header = (
        f"\n{'='*80}\n"
        f"RUN STARTED: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} | "
        f"target={len(target_rows)} | already_done={len(already_done)}\n"
        f"{'='*80}\n"
    )
    with open(log_path, "a", encoding="utf-8") as lf:
        lf.write(run_header)

    results_summary = []
    errors = []
    flagged_count = 0
    pending_count = 0
    total_pct_sum = 0.0
    total_fields_found_sum = 0
    all_keys_429_count = 0

    skipped = []
    last_processed_time = None

    for idx, row in enumerate(target_rows, 1):
        mpn = row.get("Mfg_Part_Num", f"row_{idx}")
        desc = row.get("Part_Desc", "")[:45]
        manuf = row.get("Part_Manuf", "")
        safe_mpn = re.sub(r'[/\\:*?"<>| ]', '_', mpn)
        json_filepath = os.path.join(output_dir, f"{safe_mpn}.json")
        category = classify_row(row.get("Part_Desc", ""), manuf)

        # Resume mode: skip rows already completed
        if resume and (mpn in already_done or os.path.exists(json_filepath)):
            print(f"\n[{idx}/{len(target_rows)}] SKIPPING (already done): {mpn}")
            skipped.append(mpn)
            continue

        # Pacing: 2.5s between API rows, but not after skipped rows
        if last_processed_time is not None:
            time.sleep(2.5)

        print(f"\n[{idx}/{len(target_rows)}] Processing: {mpn} | {category} | {manuf[:35]} | {desc}...")

        try:
            rec = enrich_product_record(row, source_row_index=idx - 1)

            # Write JSON — only after fully successful enrichment (never partial)
            with open(json_filepath, "w", encoding="utf-8") as jf:
                json.dump(rec.model_dump(), jf, indent=2, ensure_ascii=False)

            pct = (rec.fields_found_count / rec.fields_total_count * 100) if rec.fields_total_count else 0
            total_pct_sum += pct
            total_fields_found_sum += rec.fields_found_count
            last_processed_time = time.time()

            if rec.review_status == "flagged":
                flagged_count += 1
            else:
                pending_count += 1

            unresolved = rec.unresolved_taxonomy_labels or []

            row_summary = {
                "mpn": mpn,
                "category": category,
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
                "json_file": json_filepath,
            }
            results_summary.append(row_summary)

            print(f"    ✅ Saved to {json_filepath}")
            print(f"       MFR: {rec.manufacturer_name.value} | Brand: {rec.brand_name.value}")
            print(f"       Found: {rec.fields_found_count}/{rec.fields_total_count} ({pct:.1f}%) | Status: {rec.review_status} | Attrs: {len(rec.attributes)}")
            print(f"       Unresolved Taxonomy ({len(unresolved)}): {', '.join(unresolved[:5])}{'...' if len(unresolved) > 5 else ''}")

            _append_progress_log(output_dir, mpn, category, pct, rec.review_status)

        except AllKeys429Error as quota_exc:
            err_msg = str(quota_exc)
            all_keys_429_count += 1
            print(f"    ⛔ ALL KEYS QUOTA EXHAUSTED for {mpn} — skipping row gracefully.")
            print(f"       {err_msg[:200]}")
            # Do NOT write a partial JSON — row remains unprocessed for next run
            errors.append({"mpn": mpn, "category": category, "error": f"AllKeys429: {err_msg[:300]}"})
            _append_progress_log(output_dir, mpn, category, 0.0, "quota_skip",
                                  error="ALL_KEYS_429 — will retry next run")
            if all_keys_429_count >= 2:
                print(f"\n  🛑 Consecutive AllKeys429 quota exhaustion detected across all {len(GEMINI_KEY_POOL)} keys.")
                print(f"     Stopping batch run cleanly. {len(results_summary)} row(s) completed in this run.")
                print(f"     Re-run tomorrow to resume the remaining {len(target_rows) - idx + 1} rows.")
                break

        except Exception as exc:
            err_msg = str(exc)
            print(f"    ⛔ ERROR processing {mpn}: {err_msg}")
            errors.append({"mpn": mpn, "category": category, "error": err_msg})
            _append_progress_log(output_dir, mpn, category, 0.0, "error",
                                  error=err_msg[:80])

    # ── Final metrics ────────────────────────────────────────────────────────
    elapsed_wall_time = time.time() - start_wall_time
    total_processed = len(results_summary)
    avg_pct = (total_pct_sum / total_processed) if total_processed > 0 else 0.0
    avg_fields_found = (total_fields_found_sum / total_processed) if total_processed > 0 else 0.0

    total_done_overall = len(already_done) + total_processed
    remaining_rows = len(target_rows) - len(skipped) - total_processed
    calls_per_row = (RETRY_STATS["total_calls"] / total_processed) if total_processed > 0 else 2.0
    capacity_per_day = len(GEMINI_KEY_POOL) * 20
    est_days_remaining = (remaining_rows * calls_per_row / capacity_per_day) if remaining_rows > 0 else 0

    if skipped:
        print(f"\n  ℹ️  Skipped {len(skipped)} already-complete rows (resume mode)")

    key_usage = {f"key_{i+1}": KEY_STATS.get(i, 0) for i in range(len(GEMINI_KEY_POOL))}

    batch_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target_count": target_count,
        "total_attempted": len(target_rows),
        "total_processed_this_run": total_processed,
        "total_done_overall": total_done_overall,
        "total_remaining": max(0, target_count - total_done_overall),
        "total_errored": len(errors),
        "total_quota_exhausted": all_keys_429_count,
        "total_skipped": len(skipped),
        "skipped_mpns": skipped,
        "avg_found_pct": round(avg_pct, 1),
        "avg_fields_found_count": round(avg_fields_found, 1),
        "total_wall_clock_seconds": round(elapsed_wall_time, 2),
        "total_wall_clock_formatted": f"{int(elapsed_wall_time // 60)}m {int(elapsed_wall_time % 60)}s",
        "estimated_days_to_complete": round(est_days_remaining, 1),
        "review_status_counts": {
            "pending": pending_count,
            "flagged": flagged_count,
        },
        "retry_statistics": {
            "total_calls": RETRY_STATS["total_calls"],
            "total_retries": RETRY_STATS["total_retries"],
            "rows_requiring_retries_count": len(RETRY_STATS["rows_with_retries"]),
            "rows_requiring_retries_list": list(RETRY_STATS["rows_with_retries"]),
        },
        "key_usage_distribution": key_usage,
        "category_allocation": category_counts,
        "errors": errors,
        "rows": results_summary,
    }

    summary_file = os.path.join(output_dir, "batch_summary.json")
    with open(summary_file, "w", encoding="utf-8") as sf:
        json.dump(batch_report, sf, indent=2, ensure_ascii=False)

    print("\n" + "=" * 75)
    print("  BATCH ENRICHMENT COMPLETE — AGGREGATE METRICS")
    print("=" * 75)
    print(f"  Target Count       : {target_count}")
    print(f"  Total Attempted    : {len(target_rows)}")
    print(f"  Total Skipped      : {len(skipped)} (resume: already done)")
    print(f"  Total Processed    : {total_processed} (this run)")
    print(f"  Total Done Overall : {total_done_overall} / {target_count}")
    print(f"  Total Remaining    : {max(0, target_count - total_done_overall)}")
    print(f"  Quota Exhausted    : {all_keys_429_count} rows (will retry next run)")
    print(f"  Total Errors       : {len(errors) - all_keys_429_count} (non-quota)")
    print(f"  Avg Fields Found   : {avg_fields_found:.1f}")
    print(f"  Avg Completeness   : {avg_pct:.1f}%")
    print(f"  Status Counts      : {pending_count} pending, {flagged_count} flagged")
    print(f"  Total API Calls    : {RETRY_STATS['total_calls']}")
    print(f"  Total Retries      : {RETRY_STATS['total_retries']}")
    print(f"  Wall-Clock Time    : {int(elapsed_wall_time // 60)}m {int(elapsed_wall_time % 60)}s")
    print(f"  Est. Days to Done  : {est_days_remaining:.1f} days")
    print_key_usage_report()
    print(f"  Progress Log       : {log_path}")
    print(f"  Summary Saved      : {summary_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SpecSense batch enrichment runner")
    parser.add_argument("--count", type=int, default=70,
                        help="Number of rows to select (default: 70)")
    parser.add_argument("--legacy", action="store_true",
                        help="Use legacy 17-row hard-coded list instead of proportional selection")
    parser.add_argument("--no-resume", action="store_true",
                        help="Disable resume mode (reprocess already-done rows)")
    args = parser.parse_args()

    run_batch(
        target_count=args.count,
        resume=not args.no_resume,
        legacy_mode=args.legacy,
    )
