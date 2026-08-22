"""
pipeline/audit_sourcing.py
==========================
Read-only diagnostic + compliance cleanup for batch_output records.

Modes
-----
  (default)  python -m pipeline.audit_sourcing
             Audit-only: check all 25 JSON files, print per-record report.

  --prune    python -m pipeline.audit_sourcing --prune
             Prune non-compliant sources from all 25 JSON files in-place,
             then push the cleaned versions to Firestore.

  --report-only
             Alias for default audit-only mode.

All domain-check logic is inlined here so the script has no import side-effects
from enricher.py (no API keys needed, no banner printed).
"""

import os
import sys
import json
import re
import glob
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Force UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# Domain-check logic — kept in sync with enricher.py DOMAIN_BLOCKLIST / heuristic
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_BLOCKLIST: List[str] = [
    # General marketplaces & big box retailers
    "amazon.com", "ebay.com", "walmart.com", "target.com", "homedepot.com",
    "lowes.com", "menards.com", "bestbuy.com", "costco.com", "samsclub.com",
    "wayfair.com", "overstock.com", "bedbathandbeyond.com", "kohls.com",
    "jcpenney.com", "sears.com", "aliexpress.com", "rakuten.com", "etsy.com",
    "newegg.com", "cdw.com",
    # Appliance / kitchen / bath retailers & distributors
    "appliancesconnection.com", "abt.com", "us-appliance.com",
    "billandrodsappliance.com", "ajmadison.com", "pcrichard.com",
    "ferguson.com", "build.com", "faucetdirect.com", "prolinerangehoods.com",
    "appliancefactory.com", "grandappliance.com", "warnersstellian.com",
    "brayandoffice.com", "brandsmartusa.com", "supplyhouse.com",
    "plumbersstock.com", "supply.com", "webstaurantstore.com", "zoro.com",
    "grainger.com", "mcmaster.com", "mscdirect.com", "fastenal.com",
    "globalindustrial.com", "northerntool.com", "harborfreight.com",
    "toolnut.com", "toolbarn.com", "acmetools.com", "cpooutlets.com",
    "summitracing.com", "rockauto.com", "autozone.com", "oreillyauto.com",
    "advanceautoparts.com",
    # Replacement parts & repair distributors
    "searspartsdirect.com", "partselect.com", "partsselect.com",
    "repairclinic.com", "appliancepartspros.com", "marcone.com",
    "encompass.com", "ereplacementparts.com",
    # Generic spec / manual / datasheet aggregators
    "datasheetarchive.com", "alldatasheet.com", "datasheetcatalog.com",
    "manualslib.com", "manualzz.com", "retrevo.com", "fixya.com",
    "vosstv.com",
    # Social, encyclopedic, review & corporate aggregation sites
    "wikipedia.org", "sec.gov", "bloomberg.com", "fortune.com",
    "crunchbase.com", "consumerreports.org", "cnet.com", "reviewed.com",
    "thespruce.com", "bobvila.com", "thisoldhouse.com", "angi.com",
    "homeadvisor.com", "yelp.com", "yellowpages.com", "bbb.org",
    "trustpilot.com", "houzz.com", "pinterest.com", "youtube.com",
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "reddit.com", "quora.com", "google.com", "bing.com", "yahoo.com",
    "duckduckgo.com",
]

_STOP_WORDS = {
    "inc", "incorporated", "llc", "corp", "corporation", "co", "company",
    "the", "america", "usa", "us", "products", "product", "group",
    "holdings", "holding", "ltd", "limited", "international", "intl",
    "global", "industries", "industry", "gmbh", "electric", "manufacturing",
    "mfg", "service", "services", "supply", "supplies", "systems", "system",
    "technologies", "technology", "tools", "tool", "lighting", "light",
    "appliances", "appliance", "dealers", "cooperative"
}

_BRAND_AFFILIATES: Dict[str, List[str]] = {
    "frigidaire": ["electrolux", "electroluxmedia", "frigidaire"],
    "electrolux": ["frigidaire", "electroluxmedia", "electrolux"],
    "diablo": ["freud", "freudtools", "diablotools", "diablo"],
    "freud": ["diablo", "diablotools", "freudtools", "freud"],
    "nuvo": ["satco", "nuvo"],
    "satco": ["nuvo", "satco"],
    "kitchenaid": ["whirlpool", "kitchenaid", "whirlpoolcorp"],
    "maytag": ["whirlpool", "maytag", "whirlpoolcorp"],
    "whirlpool": ["kitchenaid", "maytag", "whirlpool", "whirlpoolcorp"],
    "dewalt": ["stanleyblackdecker", "stanley", "dewalt"],
    "timbertech": ["azek", "timbertech"],
    "azek": ["timbertech", "azek"],
}


def _is_blocked_domain(url: str) -> bool:
    if not url:
        return False
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return any(blocked in netloc for blocked in DOMAIN_BLOCKLIST)
    except Exception:
        return False


def _extract_domain_tokens(name: str) -> List[str]:
    if not name:
        return []
    clean = re.sub(r'[®™©\(\)\[\],.:;\'"\/\\-]', ' ', name).lower()
    tokens = []
    for w in clean.split():
        w_s = w.strip()
        if w_s in ("3m", "ge"):
            tokens.append(w_s)
        elif len(w_s) >= 3 and w_s not in _STOP_WORDS:
            tokens.append(w_s)
    alnum = re.sub(r'[^a-z0-9]', '', clean)
    if len(alnum) >= 3 and alnum not in _STOP_WORDS and alnum not in tokens:
        tokens.append(alnum)
    expanded = list(tokens)
    for tok in tokens:
        if tok in _BRAND_AFFILIATES:
            for aff in _BRAND_AFFILIATES[tok]:
                if aff not in expanded:
                    expanded.append(aff)
    return expanded


def _is_manufacturer_domain(url: str, manufacturer_name: str, brand_name: str = "") -> bool:
    if not url or _is_blocked_domain(url):
        return False
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        domain_clean = re.sub(r'[^a-z0-9]', '', netloc)
        tokens = set(_extract_domain_tokens(manufacturer_name) + _extract_domain_tokens(brand_name))
        if not tokens:
            return False
        for tok in tokens:
            tok_clean = re.sub(r'[^a-z0-9]', '', tok)
            if tok_clean and (tok_clean in domain_clean or tok in netloc):
                return True
        return False
    except Exception:
        return False


def _url_passes(url: str, mfr_name: str, brand_name: str) -> bool:
    """True iff the URL is not blocked AND passes the manufacturer heuristic."""
    if not url:
        return True  # null URL = unavailable, not a violation
    return (not _is_blocked_domain(url)) and _is_manufacturer_domain(url, mfr_name, brand_name)


# ─────────────────────────────────────────────────────────────────────────────
# Field inventory — all keys in a ProductRecord that carry a FieldValue dict
# ─────────────────────────────────────────────────────────────────────────────

ROOT_FV_FIELDS = [
    "manufacturer_name", "brand_name", "trade_name", "manufacturer_part_number",
    "alternate_part_number", "classpath", "mfr_url", "mobile_desc", "invoice_desc",
    "short_desc", "long_desc1", "retail_desc", "marketing_description",
    "with_features", "standard_approvals", "prop_65", "application", "includes",
    "product_name", "upc", "ean", "gtin", "unspsc", "warranty", "list_price",
    "selling_qty", "selling_uom", "length", "length_uom", "height", "height_uom",
    "width", "width_uom", "weight", "weight_uom", "volume", "volume_uom",
    "country_of_origin", "discontinued", "actual_image_yn",
]

_BLANK_FV = {
    "value": None,
    "source_type": "unavailable",
    "confidence": 0.0,
    "source_url": None,
    "source_snippet": None,
}


def _fv_has_value(fv: Any) -> bool:
    if not isinstance(fv, dict):
        return False
    val = fv.get("value")
    return val is not None and str(val).strip() not in ("", "None", "null", "N/A", "n/a")


def _recompute_fields_found(data: dict) -> int:
    """Count FieldValue entries (root + attribute labels/values) that have a non-None value."""
    count = 0
    for key in ROOT_FV_FIELDS:
        if _fv_has_value(data.get(key)):
            count += 1
    for attr in (data.get("attributes") or []):
        if not isinstance(attr, dict):
            continue
        if _fv_has_value(attr.get("label")):
            count += 1
        if _fv_has_value(attr.get("value")):
            count += 1
        if _fv_has_value(attr.get("uom")):
            count += 1
    for feat in (data.get("item_features") or []):
        if _fv_has_value(feat):
            count += 1
    return count


# ─────────────────────────────────────────────────────────────────────────────
# PART 1 — prune_noncompliant_sources
# ─────────────────────────────────────────────────────────────────────────────

def prune_noncompliant_sources(record_dict: dict) -> dict:
    """
    Returns a *new* dict (does not mutate the original) with all FieldValues
    whose source_url fails the current sourcing rules zeroed out to unavailable,
    and ref_urls filtered to compliant URLs only.

    Also recomputes fields_found_count and sets sourcing_compliance_note.
    """
    import copy
    data = copy.deepcopy(record_dict)

    mfr_fv = data.get("manufacturer_name") or {}
    brand_fv = data.get("brand_name") or {}
    # Use raw input names for heuristic; if mfr_name itself is sourced from a bad URL
    # we still need *some* name — fall back to part_manuf/e1_brand.
    mfr_name = (
        (mfr_fv.get("value") if isinstance(mfr_fv, dict) else "")
        or data.get("part_manuf") or ""
    )
    brand_name = (
        (brand_fv.get("value") if isinstance(brand_fv, dict) else "")
        or data.get("e1_brand") or ""
    )

    pruned_count = 0

    def prune_fv(fv: Any) -> Any:
        nonlocal pruned_count
        if not isinstance(fv, dict):
            return fv
        src_url = fv.get("source_url")
        if src_url and not _url_passes(src_url, mfr_name, brand_name):
            pruned_count += 1
            return dict(_BLANK_FV)
        return fv

    # Prune root FieldValue fields
    for key in ROOT_FV_FIELDS:
        if key in data:
            data[key] = prune_fv(data[key])

    # Prune attribute FieldValues
    for attr in (data.get("attributes") or []):
        if not isinstance(attr, dict):
            continue
        if "label" in attr:
            attr["label"] = prune_fv(attr["label"])
        if "value" in attr:
            attr["value"] = prune_fv(attr["value"])
        if "uom" in attr:
            attr["uom"] = prune_fv(attr["uom"])

    # Prune item_features
    pruned_features = []
    for feat in (data.get("item_features") or []):
        if isinstance(feat, dict):
            pruned_features.append(prune_fv(feat))
        else:
            pruned_features.append(feat)
    data["item_features"] = pruned_features

    # Filter ref_urls
    old_refs = data.get("ref_urls") or []
    new_refs = [u for u in old_refs if isinstance(u, str) and _url_passes(u, mfr_name, brand_name)]
    data["ref_urls"] = new_refs

    # Recompute fields_found_count
    data["fields_found_count"] = _recompute_fields_found(data)

    # Set compliance note
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["sourcing_compliance_note"] = (
        f"Pruned {pruned_count} non-compliant field(s) on {ts} "
        f"per manufacturer-only sourcing rule. "
        f"{len(old_refs) - len(new_refs)} ref_url(s) removed."
    )

    return data


# ─────────────────────────────────────────────────────────────────────────────
# PART 1 — apply prune to all 25 + push to Firestore
# ─────────────────────────────────────────────────────────────────────────────

def apply_prune_all(batch_dir: str = "data/batch_output") -> None:
    """
    Prunes all JSON files in batch_dir in-place, then re-migrates to Firestore.
    """
    pattern = os.path.join(batch_dir, "*.json")
    files = sorted([
        f for f in glob.glob(pattern)
        if os.path.basename(f) not in ("batch_summary.json",)
    ])

    if not files:
        print(f"ERROR: No JSON files found in {batch_dir}")
        sys.exit(1)

    W = 105
    print("=" * W)
    print("  PART 1 — PRUNING NON-COMPLIANT SOURCES FROM ALL RECORDS (in-place)")
    print("=" * W)
    print(f"  {'MPN':<22} {'Before':>8} {'After':>8} {'Δ Fields':>9} {'Pruned FVs':>11} {'Compliance Note'}")
    print("  " + "-" * (W - 2))

    prune_results = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            original = json.load(f)

        mpn = original.get("mfg_part_num") or original.get("part_number") or os.path.basename(fp)[:-5]
        before_count = original.get("fields_found_count", 0)
        before_total = original.get("fields_total_count", 0)

        pruned = prune_noncompliant_sources(original)

        after_count = pruned["fields_found_count"]
        delta = after_count - before_count

        # Count pruned FVs (anything that changed source_type to unavailable by us)
        note = pruned.get("sourcing_compliance_note", "")
        import re as _re
        m = _re.search(r"Pruned (\d+) non-compliant field", note)
        pruned_fv_count = int(m.group(1)) if m else 0

        before_pct = (before_count / before_total * 100) if before_total else 0.0
        after_pct = (after_count / before_total * 100) if before_total else 0.0

        print(
            f"  {mpn:<22} {before_pct:>6.1f}%  {after_pct:>6.1f}%  "
            f"{delta:>+9}  {pruned_fv_count:>11}  {'✅ no change' if pruned_fv_count == 0 else '⚠️  pruned'}"
        )

        # Overwrite JSON file in-place
        with open(fp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(pruned, f, indent=2, ensure_ascii=False)

        prune_results.append({
            "file": os.path.basename(fp),
            "mpn": mpn,
            "before_count": before_count,
            "after_count": after_count,
            "before_total": before_total,
            "delta": delta,
            "pruned_fv_count": pruned_fv_count,
        })

    total_pruned_fvs = sum(r["pruned_fv_count"] for r in prune_results)
    print("  " + "-" * (W - 2))
    print(f"  Total fields pruned across all records: {total_pruned_fvs}")
    print(f"  All {len(files)} JSON files overwritten in {batch_dir}/")

    # ── Push to Firestore ──
    print("\n" + "=" * W)
    print("  PUSHING PRUNED RECORDS TO FIRESTORE (upsert by existing doc ID)")
    print("=" * W)

    try:
        from pipeline.schema import ProductRecord
        from pipeline.firestore_client import save_product_record
    except ImportError as e:
        print(f"  ❌ Cannot import Firestore client: {e}")
        print("  Skipping Firestore push — JSON files are already updated locally.")
        return

    fs_ok = 0
    fs_err = 0
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        mpn = data.get("mfg_part_num") or data.get("part_number") or os.path.basename(fp)[:-5]
        try:
            # model_validate will ignore extra keys like sourcing_compliance_note
            record = ProductRecord.model_validate(data)
            if not record.id:
                record.id = mpn
            doc_id = save_product_record(record)
            after_pct = (
                (data["fields_found_count"] / data["fields_total_count"] * 100)
                if data.get("fields_total_count") else 0.0
            )
            print(f"  ✅ {mpn:<22} → doc_id={doc_id!r:<24} | {after_pct:.1f}% completeness")
            fs_ok += 1
        except Exception as exc:
            print(f"  ❌ {mpn:<22} FAILED: {exc}")
            fs_err += 1

    print(f"\n  Firestore push complete: {fs_ok} succeeded, {fs_err} failed.")


# ─────────────────────────────────────────────────────────────────────────────
# Audit-only report (read-only, same as before)
# ─────────────────────────────────────────────────────────────────────────────

def _url_verdict(url: str, mfr_name: str, brand_name: str) -> Dict[str, Any]:
    if not url:
        return {"url": url, "is_valid": None, "reason": "no url"}
    is_blocked = _is_blocked_domain(url)
    is_mfr = _is_manufacturer_domain(url, mfr_name, brand_name)
    is_valid = (not is_blocked) and is_mfr
    reason = "ok" if is_valid else ("blocklisted" if is_blocked else "failed mfr heuristic")
    return {"url": url, "is_valid": is_valid, "is_blocked": is_blocked,
            "failed_mfr_heuristic": not is_mfr, "reason": reason}


def audit_record(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    mpn = data.get("mfg_part_num") or data.get("part_number") or \
          os.path.basename(filepath).replace(".json", "")
    part_desc = data.get("part_desc") or ""
    mfr_fv = data.get("manufacturer_name") or {}
    brand_fv = data.get("brand_name") or {}
    mfr_name = ((mfr_fv.get("value") if isinstance(mfr_fv, dict) else "") or data.get("part_manuf") or "")
    brand_name = ((brand_fv.get("value") if isinstance(brand_fv, dict) else "") or data.get("e1_brand") or "")

    field_results: List[Dict[str, Any]] = []

    def audit_fv(field_name: str, fv: Any):
        if not isinstance(fv, dict):
            return
        src_url = fv.get("source_url")
        val = fv.get("value")
        src_type = fv.get("source_type") or "unavailable"
        if not src_url:
            return
        verdict = _url_verdict(src_url, mfr_name, brand_name)
        has_value = (val is not None and str(val).strip() not in ("", "None", "null", "N/A", "n/a"))
        field_results.append({
            "field_name": field_name, "value_preview": str(val)[:60] if val is not None else None,
            "source_type": src_type, "has_value": has_value, "source_url": src_url, **verdict,
        })

    for key in ROOT_FV_FIELDS:
        audit_fv(key, data.get(key))

    for attr in (data.get("attributes") or []):
        if not isinstance(attr, dict):
            continue
        lbl_fv = attr.get("label") or {}
        val_fv = attr.get("value") or {}
        uom_fv = attr.get("uom") or {}
        lbl_name = (lbl_fv.get("value") if isinstance(lbl_fv, dict) else "") or "?"
        audit_fv(f"attribute[{lbl_name}].label", lbl_fv)
        audit_fv(f"attribute[{lbl_name}].value", val_fv)
        audit_fv(f"attribute[{lbl_name}].uom", uom_fv)

    for i, feat in enumerate(data.get("item_features") or []):
        if isinstance(feat, dict):
            audit_fv(f"item_feature[{i}]", feat)

    ref_url_results: List[Dict[str, Any]] = []
    for u in (data.get("ref_urls") or []):
        if isinstance(u, str) and u.strip():
            ref_url_results.append(_url_verdict(u, mfr_name, brand_name))

    rejected_fvs = [r for r in field_results if not r["is_valid"]]
    accepted_fvs = [r for r in field_results if r["is_valid"]]
    fields_flipping = [r for r in rejected_fvs if r["has_value"] and r["source_type"] in ("extracted", "inferred")]

    all_sourced_urls = list(dict.fromkeys([r["source_url"] for r in field_results] + [r["url"] for r in ref_url_results]))
    rejected_urls = list(dict.fromkeys([r["source_url"] for r in rejected_fvs] + [r["url"] for r in ref_url_results if not r["is_valid"]]))
    rejected_ref_count = len([r for r in ref_url_results if not r["is_valid"]])

    fields_found_count = data.get("fields_found_count") or len([r for r in field_results if r["has_value"]])
    is_compliant = (len(rejected_fvs) == 0 and rejected_ref_count == 0)

    return {
        "file": os.path.basename(filepath), "mpn": mpn, "part_desc": part_desc,
        "mfr_name": mfr_name, "brand_name": brand_name, "is_compliant": is_compliant,
        "total_urls_audited": len(all_sourced_urls), "rejected_urls": rejected_urls,
        "rejected_url_count": len(rejected_urls),
        "accepted_url_count": len(all_sourced_urls) - len(rejected_urls),
        "total_field_values_audited": len(field_results), "rejected_field_values": rejected_fvs,
        "fields_flipping_to_unavailable": fields_flipping, "fields_flipping_count": len(fields_flipping),
        "rejected_ref_urls_count": rejected_ref_count, "fields_found_count": fields_found_count,
    }


def run_audit(batch_dir: str = "data/batch_output") -> None:
    base_dir = "."
    for candidate in [".", "..", os.path.dirname(__file__), os.path.join(os.path.dirname(__file__), "..")]:
        if os.path.isdir(os.path.join(candidate, "data", "batch_output")):
            base_dir = candidate
            break
    batch_dir = os.path.join(base_dir, "data", "batch_output")

    pattern = os.path.join(batch_dir, "*.json")
    files = sorted([f for f in glob.glob(pattern) if os.path.basename(f) not in ("batch_summary.json",)])

    if not files:
        print(f"ERROR: No JSON files found at {pattern!r}")
        sys.exit(1)

    results = [audit_record(fp) for fp in files]
    compliant = [r for r in results if r["is_compliant"]]
    non_compliant = [r for r in results if not r["is_compliant"]]

    W = 110
    print("=" * W)
    print("  SPECSENSE SOURCING RULE AUDIT (read-only)")
    print(f"  Records scanned: {len(results)}  |  Compliant: {len(compliant)}  |  Non-compliant: {len(non_compliant)}")
    print("=" * W)
    print(f"\n  {'MPN':<22} {'Manufacturer':<26} {'URLs':<6} {'Rej':<5} {'Fields→Unavail':<16} {'Status'}")
    print("  " + "-" * (W - 2))

    for r in results:
        mfr_short = (r["mfr_name"] or "")[:24]
        status = "✅ COMPLIANT" if r["is_compliant"] else "⚠️  NON-COMPLIANT"
        print(
            f"  {r['mpn']:<22} {mfr_short:<26} "
            f"{r['total_urls_audited']:<6} {r['rejected_url_count']:<5} "
            f"{r['fields_flipping_count']:<16} {status}"
        )

    if non_compliant:
        print("\n" + "=" * W)
        print("  DETAILED BREAKDOWN — NON-COMPLIANT RECORDS")
        print("=" * W)
        for r in non_compliant:
            print(f"\n  {'─'*(W-2)}")
            print(f"  📌 {r['mpn']}  |  {r['part_desc']}")
            print(f"     Manufacturer: {r['mfr_name']!r}  |  Brand: {r['brand_name']!r}")
            print(f"  Rejected source URLs ({r['rejected_url_count']}):")
            for u in r["rejected_urls"]:
                v = _url_verdict(u, r["mfr_name"], r["brand_name"])
                tag = "BLOCKED" if v["is_blocked"] else "HEURISTIC FAIL"
                print(f"    ❌ [{tag}] {u}")
            if r["fields_flipping_to_unavailable"]:
                print(f"  Fields flipping to 'unavailable' ({r['fields_flipping_count']}):")
                for fv in r["fields_flipping_to_unavailable"][:10]:
                    tag = "BLOCKED" if fv["is_blocked"] else "HEURISTIC FAIL"
                    print(f"    • {fv['field_name']:<38} [{tag}]  ← {fv['source_url'][:60]}")
                    print(f"      value: {fv['value_preview']!r}")
                if len(r["fields_flipping_to_unavailable"]) > 10:
                    print(f"    ... and {len(r['fields_flipping_to_unavailable']) - 10} more")
            else:
                print("  Fields flipping to unavailable: none (ref_urls only)")
            if r["rejected_ref_urls_count"]:
                print(f"  Additionally, {r['rejected_ref_urls_count']} ref_url(s) would be removed.")

    total_flipping = sum(r["fields_flipping_count"] for r in results)
    heavy = [r for r in non_compliant if r["fields_found_count"] > 0 and (r["fields_flipping_count"] / r["fields_found_count"]) > 0.30]

    print("\n" + "=" * W)
    print("  EXECUTIVE SUMMARY")
    print("=" * W)
    print(f"  Total records audited          : {len(results)}")
    print(f"  100% compliant                 : {len(compliant)} / {len(results)}")
    print(f"  Non-compliant                  : {len(non_compliant)} / {len(results)}")
    print(f"  Total fields → 'unavailable'   : {total_flipping}")
    print(f"  Heavily affected (>30% fields) : {len(heavy)}")
    print(f"\n  ✅ Compliant: {', '.join(r['mpn'] for r in compliant)}")
    print(f"  ⚠️  Non-compliant: {', '.join(r['mpn'] for r in non_compliant)}")
    print("=" * W)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--prune" in args:
        # Resolve batch_dir
        base_dir = "."
        for candidate in [".", "..", os.path.dirname(__file__), os.path.join(os.path.dirname(__file__), "..")]:
            if os.path.isdir(os.path.join(candidate, "data", "batch_output")):
                base_dir = candidate
                break
        apply_prune_all(os.path.join(base_dir, "data", "batch_output"))
    else:
        run_audit()
