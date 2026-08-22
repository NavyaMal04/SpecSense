import os
import sys
import io
import time
import json
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Force UTF-8 output so emoji/unicode in diagnostics don't crash on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from google import genai
from google.genai import types

from pipeline.schema import (
    ProductRecord,
    FieldValue,
    AttributeEntry,
    FeatureEntry,
    AssetLink,
    to_delivery_format_row,
)

# Load environment variables from .env file
load_dotenv()

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
    "duckduckgo.com"
]

# User-Agent header for direct page fetches
_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Common cross-category attribute labels used in Unilog's Delivery Format.
# These are COMMON labels only — not exhaustive. The extraction prompt should
# always supplement these with category-specific attributes it finds.
CORE_ATTRIBUTE_TAXONOMY: List[str] = [
    "Series",
    "Model",
    "Voltage Rating",
    "Amperage Rating",
    "Power Rating",
    "Frequency",
    "Mounting Type",
    "Size",
    "Height",
    "Width",
    "Depth",
    "Depth With Door Open",
    "Minimum Height",
    "Maximum Height",
    "Weight",
    "Color",
    "Material",
    "Sound Level",
    "Number of Wash Cycles",
    "Plug Type",
    "Certifications",
    "Country of Origin",
    "Warranty",
    "Operating Temperature Range",
    "Additional Information",
]


class EnrichmentError(Exception):
    """Custom exception raised when enrichment processing or LLM JSON parsing fails."""
    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(message)
        self.raw_response = raw_response


class GeminiRetryExhaustedError(EnrichmentError):
    """Raised when max retries are exhausted for transient Gemini API errors (503 / 429)."""
    pass


# ── Multi-key round-robin rotation ──────────────────────────────────────────
# Scans GEMINI_API_KEY_1 through GEMINI_API_KEY_10 — load any that are present
# and non-empty. Each free-tier key gives 20 req/day; total capacity scales
# linearly with the number of keys added to .env.

_PLACEHOLDER_KEYS = {
    "<YOUR_KEY_2_HERE>", "<YOUR_KEY_3_HERE>", "<YOUR_KEY_4_HERE>",
    "<YOUR_KEY_5_HERE>", "your_gemini_api_key_here", "",
}

def _load_key_pool() -> list:
    """Scan GEMINI_API_KEY_1..10 and load all non-empty, non-placeholder keys.

    Also accepts the bare GEMINI_API_KEY as a backwards-compatible fallback.
    To add more keys: simply set GEMINI_API_KEY_4, GEMINI_API_KEY_5, etc. in .env.
    No code changes needed.
    """
    pool = []
    seen = set()
    for i in range(1, 11):  # scan slots 1–10
        k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if k and k not in _PLACEHOLDER_KEYS and k not in seen:
            pool.append(k)
            seen.add(k)
    if not pool:
        # Backwards-compat: bare GEMINI_API_KEY
        k = os.getenv("GEMINI_API_KEY", "").strip()
        if k and k not in _PLACEHOLDER_KEYS:
            pool.append(k)
    if not pool:
        raise EnrichmentError(
            "No valid Gemini API keys found. Set GEMINI_API_KEY_1 (through GEMINI_API_KEY_10) "
            "or GEMINI_API_KEY in your .env file."
        )
    return pool


GEMINI_KEY_POOL: list = _load_key_pool()
_KEY_INDEX = 0  # module-level round-robin pointer

# Per-key call counters (key index → call count) for usage reporting
KEY_STATS: dict = {i: 0 for i in range(len(GEMINI_KEY_POOL))}

# Global diagnostic stats for retry monitoring
RETRY_STATS = {
    "total_calls": 0,
    "total_retries": 0,
    "rows_with_retries": set()
}


class AllKeys429Error(EnrichmentError):
    """Raised when every key in the pool returns 429 in the same retry cycle."""
    pass


def get_gemini_client() -> genai.Client:
    """
    Returns a Gemini client built from the *next* key in the round-robin pool.
    Advances the module-level index on each call (1 → 2 → 3 → 1 → ...).
    Also increments KEY_STATS[key_index] for the usage report.
    """
    global _KEY_INDEX
    idx = _KEY_INDEX % len(GEMINI_KEY_POOL)
    _KEY_INDEX += 1
    KEY_STATS[idx] = KEY_STATS.get(idx, 0) + 1
    return genai.Client(api_key=GEMINI_KEY_POOL[idx])


def _get_genai_client() -> genai.Client:
    """Backwards-compatible alias — returns the rotating client."""
    return get_gemini_client()


def print_key_usage_report() -> None:
    """Print a per-key call distribution table (call at end of batch)."""
    print("\n  Gemini Key Usage Distribution:")
    total = sum(KEY_STATS.values())
    for idx, count in sorted(KEY_STATS.items()):
        masked = GEMINI_KEY_POOL[idx][:8] + "..." if GEMINI_KEY_POOL[idx] else "(none)"
        print(f"    Key {idx + 1} ({masked}): {count} calls")
    print(f"    Total: {total} calls across {len(GEMINI_KEY_POOL)} key(s)")


def call_gemini_with_retry(
    client: genai.Client,
    model: str,
    contents: Any,
    config: Optional[types.GenerateContentConfig] = None,
    max_retries: int = 5,
    base_delay: float = 3.0,
    current_mpn: str = ""
) -> Any:
    """
    Executes generate_content with:
      - Immediate key rotation on 429 quota errors (tries next key before backoff)
      - Exponential backoff (respecting API-provided retryDelay) for 503 / transient errors
      - AllKeys429Error if every key in the pool returns 429 consecutively
    """
    import time
    import re
    RETRY_STATS["total_calls"] += 1
    last_error = None

    # Track which key indices we've already tried for 429 rotation
    keys_tried_for_quota = set()
    current_key_idx = (_KEY_INDEX - 1) % len(GEMINI_KEY_POOL)  # index used when client was obtained
    current_client = client

    for attempt in range(max_retries + 1):
        try:
            return current_client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
        except Exception as e:
            err_str = str(e)
            is_quota_429 = any(t in err_str.lower() for t in ["429", "resource_exhausted", "quota"])
            is_transient_503 = any(t in err_str.lower() for t in ["503", "unavailable", "high demand", "overloaded", "rate limit"])
            is_transient = is_quota_429 or is_transient_503

            if not is_transient:
                raise e

            last_error = e
            RETRY_STATS["total_retries"] += 1
            if current_mpn:
                RETRY_STATS["rows_with_retries"].add(current_mpn)

            if attempt >= max_retries:
                break

            # ── On 429/quota: rotate to next key immediately before sleeping ──
            if is_quota_429 and len(GEMINI_KEY_POOL) > 1:
                keys_tried_for_quota.add(current_key_idx)
                if len(keys_tried_for_quota) >= len(GEMINI_KEY_POOL):
                    # Every key has returned 429 — daily cap is genuinely exhausted
                    raise AllKeys429Error(
                        f"All {len(GEMINI_KEY_POOL)} Gemini API keys exhausted (daily quota). "
                        f"Last error: {err_str[:200]}"
                    )
                # Rotate to next fresh key
                next_idx = (current_key_idx + 1) % len(GEMINI_KEY_POOL)
                while next_idx in keys_tried_for_quota and len(keys_tried_for_quota) < len(GEMINI_KEY_POOL):
                    next_idx = (next_idx + 1) % len(GEMINI_KEY_POOL)
                current_key_idx = next_idx
                KEY_STATS[current_key_idx] = KEY_STATS.get(current_key_idx, 0) + 1
                current_client = genai.Client(api_key=GEMINI_KEY_POOL[current_key_idx])
                print(f"  [call_gemini_with_retry] 429 on key {list(keys_tried_for_quota)[-1]+1}, rotating to key {current_key_idx+1} (no sleep)")
                continue  # retry immediately with new key, no delay

            # ── For 503 or single-key setup: use timed exponential backoff ──
            delay = base_delay * (2 ** attempt)
            match = re.search(r'retry in (\d+(?:\.\d+)?)s', err_str, re.IGNORECASE)
            if match:
                delay = max(delay, float(match.group(1)) + 1.0)
            else:
                match_delay = re.search(r"retryDelay['\"?]\s*:\s*['\"?]?(\d+)s", err_str, re.IGNORECASE)
                if match_delay:
                    delay = max(delay, float(match_delay.group(1)) + 1.0)

            print(f"  [call_gemini_with_retry] Retry {attempt + 1}/{max_retries} after {delay:.1f}s due to: {err_str[:120]}")
            time.sleep(delay)

    raise GeminiRetryExhaustedError(f"Gemini API retries exhausted ({max_retries} attempts): {last_error}")


def _is_blocked_domain(url: str) -> bool:
    """Checks if a given URL belongs to a distributor/marketplace in DOMAIN_BLOCKLIST."""
    if not url:
        return False
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return any(blocked in netloc for blocked in DOMAIN_BLOCKLIST)
    except Exception:
        return False


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


def _extract_domain_tokens(name: str) -> List[str]:
    """Extracts alphanumeric brand/mfr tokens suitable for domain matching."""
    if not name:
        return []
    clean = re.sub(r'[®™©\(\)\[\],.:;\'\"/\\-]', ' ', name).lower()
    tokens = []
    for w in clean.split():
        w_s = w.strip()
        if w_s in ["3m", "ge"]:
            tokens.append(w_s)
        elif len(w_s) >= 3 and w_s not in _STOP_WORDS:
            tokens.append(w_s)
    alnum = re.sub(r'[^a-z0-9]', '', clean)
    if len(alnum) >= 3 and alnum not in _STOP_WORDS and alnum not in tokens:
        tokens.append(alnum)

    # Expand known corporate parent / affiliate brand tokens (e.g. Frigidaire <-> Electrolux)
    expanded = list(tokens)
    for tok in tokens:
        if tok in _BRAND_AFFILIATES:
            for aff in _BRAND_AFFILIATES[tok]:
                if aff not in expanded:
                    expanded.append(aff)
    return expanded


def _is_manufacturer_domain(url: str, manufacturer_name: str, brand_name: str = "") -> bool:
    """
    Heuristic check: verifies whether a URL domain contains the resolved manufacturer_name
    or brand_name (or a close variant) anywhere in its domain string.
    Rejects any URL in DOMAIN_BLOCKLIST or whose domain does not contain any manufacturer/brand tokens.
    """
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


def normalize_fraction_hyphenation(text: str) -> str:
    """
    Finds any pattern of '{whole number} {fraction}' followed by inch designations
    or dimension connectors (e.g., '33 3/4 in', '33 3/4 inch', '33 3/4\"', '33 3/4 to')
    and converts the space between the whole number and fraction into a hyphen ('33-3/4 in').
    Only applies to the specific pattern (digit, space, digit/digit) followed by dimension units
    without modifying any other spaces in the text.
    """
    if not isinstance(text, str) or not text.strip():
        return text
    pattern = r'\b(\d+)\s+(\d+/\d+)(\s*(?:in\b|in\.|inch\b|inches\b|\"|\'\'|\bto\b|\bx\b|\bby\b|\bH\b|\bW\b|\bD\b|\bL\b))'
    def _repl(m):
        whole = m.group(1)
        frac = m.group(2)
        suffix = m.group(3)
        return f"{whole}-{frac}{suffix}"
    return re.sub(pattern, _repl, text, flags=re.IGNORECASE)


def _clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """Safely extracts JSON from LLM markdown code blocks and parses it."""
    if not raw_text:
        raise EnrichmentError("Empty response from LLM")
    cleaned = raw_text.strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise EnrichmentError(f"Failed to parse LLM response as JSON: {e}", raw_response=raw_text)


# Startup security & cost-safety confirmation banner
print("=" * 70)
print("[SpecSense Enricher] Search Grounding Safety Check:")
print("  • Gemini Search Grounding Tools: DISABLED (Zero-Cost Free Tier Mode)")
print("  • Free Web Search: ENABLED (duckduckgo-search / ddgs)")
print(f"  • Gemini Key Pool: {len(GEMINI_KEY_POOL)} key(s) loaded (scanned GEMINI_API_KEY_1..10)")
print(f"  • Round-Robin Rotation: ACTIVE — ~{len(GEMINI_KEY_POOL) * 20} req/day total free-tier capacity")
print("  • Gemini Call Sites:")
print("      1. identify_manufacturer    -> plain text prompt (grounding tools: DISABLED)")
print("      2. find_manufacturer_page   -> pure search + blocklist (Gemini: NONE)")
print("      3. fetch_and_extract_fields -> plain text prompt (grounding tools: DISABLED)")
print("=" * 70)


def web_search_free(query: str, max_results: int = 5) -> list[dict]:
    """
    Performs a free web search using DuckDuckGo (no API key required).
    Returns a list of dicts with keys: 'title', 'url', 'snippet'.
    Returns an empty list on failure or rate limiting to allow graceful fallback.
    """
    if not query or not str(query).strip():
        return []

    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return []

    cleaned_q = str(query).strip()
    for attempt in range(2):
        results = []
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(cleaned_q, max_results=max_results))
                for r in raw_results:
                    title = r.get("title") or ""
                    url = r.get("href") or r.get("url") or ""
                    snippet = r.get("body") or r.get("snippet") or ""
                    if url:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
            if results:
                return results
        except Exception as e:
            if attempt == 0:
                time.sleep(1.5)
            else:
                print(f"  [web_search_free] Warning: search query '{cleaned_q[:60]}' failed/rate-limited: {e}")
    return []


def identify_manufacturer(part_manuf: str, part_desc: str, mfg_part_num: str) -> dict:
    """
    Identifies the real manufacturer company and brand name from part info using free web search
    and a plain Gemini text prompt (no paid search grounding tools).
    Handles raw Part_Manuf fields that are distributors/resellers (e.g. Appliance Dealers Cooperative).

    Returns:
        dict: {"manufacturer_name": ..., "brand_name": ..., "confidence": ..., "source_url": ..., "source_snippet": ...}
    """
    # 1. Perform free DuckDuckGo search
    search_query = f"{mfg_part_num} {part_desc} manufacturer".strip()
    search_results = web_search_free(search_query, max_results=5)

    formatted_snippets = []
    if search_results:
        for idx, r in enumerate(search_results, 1):
            formatted_snippets.append(
                f"Result {idx}:\n"
                f"  Title: {r.get('title')}\n"
                f"  URL: {r.get('url')}\n"
                f"  Snippet: {r.get('snippet')}\n"
            )
        search_context = "\n".join(formatted_snippets)
    else:
        search_context = "(No web search results returned. Infer best-effort from the provided raw part description.)"

    client = _get_genai_client()
    prompt = f"""You are identifying the real product manufacturer and brand for an industrial/appliance catalogue row.
Raw Part Manufacturer: {part_manuf} (Note: this raw value is often a reseller or distributor like 'Appliance Dealers Cooperative').
Raw Part Description: {part_desc}
Mfg Part Num: {mfg_part_num}

Search Results from Free Web Search:
--------------------------------------------------------------------------------
{search_context}
--------------------------------------------------------------------------------

Instructions:
1. Determine the REAL manufacturer parent company (e.g., 'Rheem Manufacturing', 'Whirlpool Corporation', 'Stanley Black & Decker', 'Milwaukee Electric Tool', '3M Company', 'Freud America, Inc. / Diablo') and brand name (e.g., 'FRIGIDAIRE®', 'Whirlpool®', 'DEWALT®', 'Milwaukee®', '3M™', 'Diablo®') FROM THE SEARCH RESULTS ABOVE.
2. Cite the specific source_url and source_snippet from the search results that supports your answer.
3. Do NOT invent details. If no confident match can be determined from the search results or part info, return null.

Return ONLY a valid JSON object wrapped in ```json ... ``` with the exact shape:
{{
  "manufacturer_name": "Full Manufacturer Name or null",
  "brand_name": "Brand Name with registration mark if applicable or null",
  "confidence": 0.95,
  "source_url": "URL from the search results or null",
  "source_snippet": "Supporting quote from search snippet or null"
}}

If no confident match is found, return "manufacturer_name": null, "brand_name": null."""

    try:
        res = call_gemini_with_retry(
            client=client,
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            contents=prompt,
            config=None,  # STRICT: Plain text prompt, zero tools
            current_mpn=mfg_part_num
        )
        data = _clean_and_parse_json(res.text)
        src_url = data.get("source_url")
        if src_url:
            mfr_n = data.get("manufacturer_name") or ""
            brd_n = data.get("brand_name") or ""
            if _is_blocked_domain(src_url) or not _is_manufacturer_domain(src_url, mfr_n, brd_n):
                print(f"Rejected non-manufacturer source: {src_url}")
                data["source_url"] = None
        return data
    except Exception as e:
        if isinstance(e, EnrichmentError):
            raise e
        raise EnrichmentError(f"identify_manufacturer failed: {e}")


def find_manufacturer_page(
    manufacturer_name: str,
    mfg_part_num: str,
    part_desc: str = "",
    brand_name: str = ""
) -> dict:
    """
    Finds the manufacturer's official product page and candidate reference URLs
    (including PDF spec sheets and manuals) using broadened multi-query free search
    and strict domain filtering (no Gemini API call needed).
    Explicitly filters out marketplace/distributor domains in DOMAIN_BLOCKLIST AND
    enforces that domains must contain manufacturer/brand name tokens.

    Returns:
        dict: {"mfr_url": ..., "candidate_ref_urls": [...]}
    """
    if not manufacturer_name and not mfg_part_num:
        return {"mfr_url": None, "candidate_ref_urls": []}

    clean_mpn = mfg_part_num.split("-")[-1] if "3MABR-" in (mfg_part_num or "") else (mfg_part_num or "")
    mfr_str = (manufacturer_name or "").strip()
    brand_str = (brand_name or "").strip()

    # Extract short descriptive keywords (e.g. "Cubitron II Stikit Film" or "Metal Cut Off Disc")
    clean_desc = re.sub(r'[^a-zA-Z0-9\s/.-]', ' ', part_desc or "")
    desc_words = [w for w in clean_desc.split() if len(w) > 2 and w.lower() not in ["display", "only", "the", "and", "for", "with", "from", "unbranded"]][:5]
    desc_str = " ".join(desc_words)

    # 3 Varied queries for broad discovery (general, specs, pdf spec sheets/manuals)
    queries = [
        f"{mfr_str} {clean_mpn} {desc_str}".strip(),
        f"{clean_mpn} {desc_str} specifications".strip(),
        f"{mfr_str} {clean_mpn} spec sheet OR datasheet OR manual filetype:pdf".strip(),
    ]

    all_raw_results = []
    for q in queries:
        if q:
            all_raw_results.extend(web_search_free(q, max_results=6))

    clean_urls = []
    for r in all_raw_results:
        url = r.get("url") or ""
        if not url or url in clean_urls:
            continue

        # Check blocklist and manufacturer-name-in-domain heuristic
        if _is_blocked_domain(url) or not _is_manufacturer_domain(url, mfr_str, brand_str):
            print(f"Rejected non-manufacturer source: {url}")
            continue

        clean_urls.append(url)

    mfr_url = None
    candidate_ref_urls = []

    # Prioritize a non-PDF URL from clean_urls
    for url in clean_urls:
        if not url.lower().endswith(".pdf"):
            mfr_url = url
            break

    # If all clean URLs are PDFs, take the first clean URL
    if not mfr_url and clean_urls:
        mfr_url = clean_urls[0]

    # Collect remaining clean URLs as candidate refs (up to 8 candidates, keeping PDF spec sheets)
    for url in clean_urls:
        if url != mfr_url and len(candidate_ref_urls) < 8:
            candidate_ref_urls.append(url)

    return {"mfr_url": mfr_url, "candidate_ref_urls": candidate_ref_urls}


def _fetch_page_content_direct(url: str, timeout: int = 10) -> dict:
    """
    Directly fetches a URL via HTTP and returns full text content (HTML or PDF) with diagnostics.
    Extracts text from HTML via tag stripping or from PDF via pdfplumber.

    Returns:
        dict: {"char_count": int, "preview": str (first 300 chars), "text": str,
               "status_code": int|None, "error": str|None, "is_short": bool}
    """
    import urllib.request
    import urllib.error
    import html as _html
    import re as _re
    import io as _io

    result = {
        "char_count": 0,
        "preview": "",
        "text": "",
        "status_code": None,
        "error": None,
        "is_short": False
    }

    if not url or not url.startswith("http"):
        result["error"] = "Invalid URL"
        result["is_short"] = True
        return result

    raw_bytes = None
    status_code = None
    content_type = ""

    # Attempt 1: Standard urllib with browser headers
    try:
        req = urllib.request.Request(url, headers=_FETCH_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            content_type = resp.headers.get("Content-Type", "").lower()
            raw_bytes = resp.read()
    except urllib.error.HTTPError as e:
        status_code = e.code
        # On 403 / 401 / 429 bot-block, attempt primp fallback if available
        if e.code in [403, 401, 429]:
            try:
                import primp
                client = primp.Client(impersonate="chrome_131")
                resp = client.get(url, timeout=timeout)
                status_code = resp.status_code
                content_type = resp.headers.get("content-type", "").lower()
                raw_bytes = resp.content
            except Exception as primp_err:
                result["error"] = f"HTTPError {e.code}: {e.reason} (fallback: {primp_err})"
        else:
            result["error"] = f"HTTPError {e.code}: {e.reason}"
    except Exception as e:
        # Try primp on connection errors
        try:
            import primp
            client = primp.Client(impersonate="chrome_131")
            resp = client.get(url, timeout=timeout)
            status_code = resp.status_code
            content_type = resp.headers.get("content-type", "").lower()
            raw_bytes = resp.content
        except Exception:
            result["error"] = str(e)

    result["status_code"] = status_code

    if raw_bytes:
        is_pdf = url.lower().endswith(".pdf") or "application/pdf" in content_type or raw_bytes.startswith(b"%PDF")
        if is_pdf:
            # Extract PDF text using pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(_io.BytesIO(raw_bytes)) as pdf:
                    pages_text = []
                    for page in pdf.pages[:10]:  # up to 10 pages
                        txt = page.extract_text()
                        if txt:
                            pages_text.append(txt)
                    clean_text = "\n".join(pages_text).strip()
            except Exception as pdf_err:
                clean_text = ""
                result["error"] = f"PDF extraction error: {pdf_err}"
        else:
            # Extract HTML text
            try:
                raw_html = raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                raw_html = raw_bytes.decode("latin-1", errors="replace")

            # Strip script, style, header, nav, footer, svg tags
            clean_html = _re.sub(
                r'<(script|style|noscript|header|footer|nav|svg|aside)[^>]*>.*?</\1>',
                ' ',
                raw_html,
                flags=_re.DOTALL | _re.IGNORECASE
            )
            clean_text = _re.sub(r'<[^>]+>', ' ', clean_html)
            clean_text = _html.unescape(clean_text)
            clean_text = _re.sub(r'\s+', ' ', clean_text).strip()

        result["char_count"] = len(clean_text)
        result["preview"] = clean_text[:300]
        result["text"] = clean_text
        result["is_short"] = result["char_count"] < 500
    else:
        result["is_short"] = True

    return result


def fetch_and_extract_fields(
    mfr_url: str,
    ref_urls: list,
    part_desc: str,
    mfg_part_num: str,
) -> dict:
    """
    Fetches full page/PDF content from official URLs and candidate references,
    skipping short (<500 chars) responses, and extracts all findable delivery format
    fields using a single plain (non-grounded) Gemini prompt over the aggregated real content.

    Returns:
        dict with keys:
          - all extracted field data
          - "_content_diagnostics": list of per-URL fetch diagnostic dicts
    """
    client = _get_genai_client()
    candidate_urls = []
    if mfr_url and not _is_blocked_domain(mfr_url):
        candidate_urls.append(mfr_url)
    for u in (ref_urls or []):
        if u and not _is_blocked_domain(u) and u not in candidate_urls:
            candidate_urls.append(u)

    # ── Fetch content from candidate URLs, falling back past short/broken URLs ──
    content_diagnostics = []
    collected_text_blocks = []
    rich_sources_count = 0

    for url in candidate_urls:
        diag = _fetch_page_content_direct(url)
        diag["url"] = url
        content_diagnostics.append(diag)

        if not diag.get("is_short") and diag.get("text"):
            page_text = diag["text"][:15000]
            is_pdf = url.lower().endswith(".pdf")
            source_tag = f"=== SOURCE ({'PDF SPEC SHEET' if is_pdf else 'WEB PAGE'}: {url}) ==="
            collected_text_blocks.append(f"{source_tag}\n{page_text}\n")
            rich_sources_count += 1
            if rich_sources_count >= 5:  # Gather up to 5 full rich sources
                break

    # If all direct page/PDF fetches returned short or failed, try one more targeted spec query (strictly manufacturer sources only)
    if not collected_text_blocks and mfr_url:
        spec_search_results = web_search_free(f"{mfg_part_num} specifications features dimensions", max_results=5)
        for r in spec_search_results:
            fallback_u = r.get("url")
            if fallback_u and not _is_blocked_domain(fallback_u) and fallback_u not in [d.get("url") for d in content_diagnostics]:
                diag = _fetch_page_content_direct(fallback_u)
                diag["url"] = fallback_u
                content_diagnostics.append(diag)
                if not diag.get("is_short") and diag.get("text"):
                    collected_text_blocks.append(f"=== SOURCE (WEB PAGE: {fallback_u}) ===\n{diag['text'][:15000]}\n")
                    break

    combined_context_text = "\n\n".join(collected_text_blocks)
    if not combined_context_text.strip():
        combined_context_text = f"Product MPN: {mfg_part_num}\nDescription: {part_desc}\n(No full-page web content could be retrieved.)"

    taxonomy_list = "\n".join(f"  - {lbl}" for lbl in CORE_ATTRIBUTE_TAXONOMY)

    prompt = f"""You are a product specification extraction AI.
Target Product MPN: {mfg_part_num}
Description: {part_desc}
Target Source URLs: {json.dumps([d['url'] for d in content_diagnostics if not d.get('is_short')])}

Below is the FULL text content extracted directly from official manufacturer web pages, specification sheets, and PDF documentation for this product:
--------------------------------------------------------------------------------
{combined_context_text}
--------------------------------------------------------------------------------

Analyze the provided full text content above to extract genuine product specifications and delivery format fields.

=== STEP 1: STANDARD TAXONOMY ATTRIBUTES (check these first) ===
For the following standard Unilog attribute labels, check if the provided text provides a value.
If the data is present, use EXACTLY these label names even if the source text uses different wording.
Examples of required normalization:
  - Source says "Model Number" -> use label "Model"
  - Source says "Colour" or "Color/Finish" -> if only color info, use label "Color";
    if BOTH color and material info are present in one field, split into TWO separate attributes:
    one with label "Color" and one with label "Material"
  - Separate Height / Width / Depth dimension values -> ALSO produce ONE attribute with label "Size"
    formatted as "{{H}} in H x {{W}} in W x {{D}} in D" using the numeric values found.
    (Still also populate the scalar dimension fields height/width/length below.)
  - Source says "dBA" noise level -> use label "Sound Level"

Standard labels to check:
{taxonomy_list}

=== STEP 2: CATEGORY-SPECIFIC ATTRIBUTES (extract freely) ===
After covering the standard labels above, also extract any additional product-specific attributes
visible in the provided text. Use clear Title Case label names with no manufacturer jargon.

=== STEP 3: ADDITIONAL INFORMATION CATCH-ALL ATTRIBUTE ===
Finally, scan the provided text (bullet points, feature lists, marketing copy, options, technologies):
  - Look for notable product features, options, cycles, systems, included items, or technical capabilities
    mentioned in the text that were NOT captured in the structured taxonomy attributes above
    (for example: "Folding Tines, Leak Detection System, Moisture Repellent Silverware Basket, Normal Cycle, Quick Wash Cycle, Sani Rinse Option, Sensor Cycle, Triple Wash Spray").
  - Compile all these extra uncaptured features/options into a SINGLE comma-separated attribute entry
    with EXACT label "Additional Information", e.g.:
    {{ "label": "Additional Information", "value": "Folding Tines, Leak Detection System, Moisture Repellent Silverware Basket, Sensor Cycle, Sani Rinse Option", "uom": null }}
  - If NO extra features or options exist beyond what is already captured, set "value": null for "Additional Information".

=== OUTPUT FIELDS ===
Extract as many of the following delivery format fields as genuinely present in the provided text:
- trade_name, classpath, with_features, standard_approvals, prop_65, application, includes, product_name
- item_features (list of up to 20 feature bullet strings)
- attributes (list of up to 50 objects: {{ "label": "...", "value": "...", "uom": "..." }})
  NOTE: include standard taxonomy attributes, category-specific attributes, AND the "Additional Information" catch-all attribute.
- identifiers: upc, ean, gtin, unspsc
- commercial: warranty, list_price (float), selling_qty, selling_uom, standard_packaging_info
- dimensions (scalar fields for dedicated dimension columns):
    length (float), length_uom, height (float), height_uom, width (float), width_uom,
    weight (float), weight_uom, volume (float), volume_uom
- assets (list of objects: {{ "asset_type": "product_image|specification_sheet|installation_manual|owners_manual|energy_guide|etc", "url": "..." }})
- misc: country_of_origin, discontinued (Yes/No), actual_image_yn (Yes/No)

=== PROVENANCE RULE ===
For EVERY simple field (or attribute/feature/asset item), return an object with the shape:
{{
  "value": <extracted_value or null if not found>,
  "source_snippet": <short exact quote supporting it or null>,
  "source_url": <the specific official page or PDF URL where found or null>,
  "confidence": 0.95
}}

Do NOT fabricate or infer values not stated in the provided text. If a field is not found, set "value": null.

Return ONLY a valid JSON object wrapped in ```json ... ```."""

    try:
        res = call_gemini_with_retry(
            client=client,
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            contents=prompt,
            config=None,  # STRICT: No tools / no grounding attached!
            current_mpn=mfg_part_num
        )
        data = _clean_and_parse_json(res.text)
        data["_content_diagnostics"] = content_diagnostics
        return data
    except Exception as e:
        if isinstance(e, EnrichmentError):
            raise e
        raise EnrichmentError(f"fetch_and_extract_fields failed: {e}")



def generate_description_formats(record: ProductRecord) -> ProductRecord:
    """
    Generates structured buyer-facing description fields (invoice_desc, mobile_desc, short_desc,
    long_desc1, retail_desc, marketing_description) strictly using already verified record fields.
    Sets source_type="inferred" with calculated confidence scores.
    """
    mfr = record.manufacturer_name.value or record.part_manuf or ""
    brand = record.brand_name.value or record.e1_brand or mfr
    mpn = record.mfg_part_num or record.manufacturer_part_number.value or ""
    p_name = record.product_name.value or record.part_desc or "Product"

    # Extract top attributes for descriptions
    top_attrs = []
    for attr in record.attributes:
        if attr.label.value and attr.value.value:
            uom_str = f" {attr.uom.value}" if attr.uom.value else ""
            top_attrs.append(f"{attr.label.value}: {attr.value.value}{uom_str}")

    # Compute average confidence from attributes
    conf_scores = [a.value.confidence for a in record.attributes if a.value.confidence > 0]
    avg_conf = (sum(conf_scores) / len(conf_scores)) if conf_scores else 0.90

    def _inferred_val(val_str: str) -> FieldValue[str]:
        return FieldValue(
            value=val_str,
            source_type="inferred",
            confidence=round(avg_conf, 2),
            source_url=None,
            source_snippet=None
        )

    # 1. invoice_desc: ALL CAPS, ~40 char max, heavily abbreviated
    abbrev_parts = [p_name.upper()]
    for attr in record.attributes[:3]:
        if attr.value.value:
            v = str(attr.value.value).upper()
            u = f" {attr.uom.value.upper()}" if attr.uom.value else ""
            abbrev_parts.append(f"{v}{u}")
    inv_str = " ".join(abbrev_parts)[:40]
    record.invoice_desc = _inferred_val(inv_str)

    # 2. mobile_desc: "{Manufacturer}, {Brand}, {Item Type}, {MPN}"
    mob_parts = [p for p in [mfr, brand, p_name, mpn] if p]
    record.mobile_desc = _inferred_val(", ".join(mob_parts))

    # 3. short_desc: "{Brand}® {MPN} {Item Type} With {with_features}, {top attributes}"
    with_feat = record.with_features.value or ""
    short_parts = [f"{brand} {mpn}".strip(), p_name]
    if with_feat:
        short_parts.append(f"With {with_feat}")
    if top_attrs:
        short_parts.extend(top_attrs[:2])
    record.short_desc = _inferred_val(", ".join(short_parts))

    # 4. long_desc1: Full expansion with comma-separated specs and additional info
    long_parts = [f"{brand} {p_name}".strip()]
    if top_attrs:
        long_parts.extend(top_attrs)
    if record.item_features:
        feat_texts = [f.text.value for f in record.item_features if f.text.value]
        if feat_texts:
            long_parts.append(f"Additional Information: {', '.join(feat_texts[:5])}")
    record.long_desc1 = _inferred_val(", ".join(long_parts))

    # 5. retail_desc: Customer-facing item description
    retail_parts = [p_name]
    if top_attrs:
        retail_parts.extend(top_attrs[:3])
    record.retail_desc = _inferred_val(", ".join(retail_parts))

    # 6. marketing_description: Feature overview
    if record.item_features:
        feats = [f.text.value for f in record.item_features if f.text.value]
        record.marketing_description = _inferred_val(" ".join(feats[:3]))
    elif not record.marketing_description.value:
        record.marketing_description = _inferred_val(f"High quality {p_name} from {brand}.")

    return record


def _map_field(data: Optional[Any], fallback_url: Optional[str] = None) -> FieldValue:
    """Converts a raw JSON field (dict or primitive string/number) into a validated FieldValue instance."""
    if data is None or data == "" or str(data).lower() in ["null", "none"]:
        return FieldValue(value=None, source_type="unavailable", confidence=0.0)

    if isinstance(data, dict):
        val = data.get("value")
        if val is None or val == "" or str(val).lower() in ["null", "none"]:
            return FieldValue(value=None, source_type="unavailable", confidence=0.0)
        url = data.get("source_url") or fallback_url
        snippet = data.get("source_snippet")
        conf = float(data.get("confidence", 0.95)) if data.get("confidence") is not None else 0.95
        return FieldValue(
            value=val,
            source_type="extracted",
            confidence=conf,
            source_url=url,
            source_snippet=snippet
        )
    else:
        # Primitive type (str, int, float, bool)
        return FieldValue(
            value=data,
            source_type="extracted",
            confidence=0.95,
            source_url=fallback_url,
            source_snippet=None
        )


def _extract_attr_entry(a: Dict[str, Any], fallback_url: Optional[str] = None) -> Optional[AttributeEntry]:
    """Parses a dictionary item into an AttributeEntry, supporting varied LLM key names."""
    if not isinstance(a, dict):
        return None

    raw_label = a.get("label") if "label" in a else (a.get("name") or a.get("attribute_name") or a.get("key"))
    raw_value = a.get("value") if "value" in a else (a.get("val") or a.get("attribute_value"))
    raw_uom = a.get("uom") if "uom" in a else (a.get("unit") or a.get("attribute_uom"))

    lbl = _map_field(raw_label, fallback_url)
    val = _map_field(raw_value, fallback_url)
    uom = _map_field(raw_uom, fallback_url)

    if lbl.value or val.value:
        return AttributeEntry(label=lbl, value=val, uom=uom)
    return None


# Hardcoded label normalization map: manufacturer-variant names -> Unilog standard names.
# Grow this dict as new variant patterns are discovered during testing.
_LABEL_NORMALIZATION_MAP: Dict[str, str] = {
    # Model variants
    "model number": "Model",
    "model no": "Model",
    "model no.": "Model",
    "part number": "Model",
    # Color variants
    "colour": "Color",
    "color/finish": "Color",
    "color / finish": "Color",
    "finish color": "Color",
    # Material variants
    "material type": "Material",
    "construction material": "Material",
    "housing material": "Material",
    # Voltage variants
    "voltage": "Voltage Rating",
    "operating voltage": "Voltage Rating",
    "rated voltage": "Voltage Rating",
    "supply voltage": "Voltage Rating",
    # Amperage variants
    "amperage": "Amperage Rating",
    "current rating": "Amperage Rating",
    "rated current": "Amperage Rating",
    "max current": "Amperage Rating",
    # Sound variants
    "noise level": "Sound Level",
    "decibel level": "Sound Level",
    "dba rating": "Sound Level",
    # Mounting variants
    "mount type": "Mounting Type",
    "installation type": "Mounting Type",
    "mounting style": "Mounting Type",
    # Weight variants
    "product weight": "Weight",
    "net weight": "Weight",
    "shipping weight": "Weight",
    # Country of origin variants
    "country of manufacture": "Country of Origin",
    "made in": "Country of Origin",
    "origin": "Country of Origin",
    # Series variants
    "product series": "Series",
    "product line": "Series",
    "line": "Series",
    # Certification variants
    "certifications/listings": "Certifications",
    "listings": "Certifications",
    "approvals": "Certifications",
    "ul listing": "Certifications",
}


def normalize_attribute_labels(attributes: List[AttributeEntry]) -> List[AttributeEntry]:
    """
    Post-processing safety net: maps raw extracted attribute label variants to Unilog standard names.
    Applied after LLM extraction in case prompt-level normalization missed cases.
    Logs any normalization applied to stdout for visibility during testing.
    """
    normalized: List[AttributeEntry] = []
    for attr in attributes:
        raw_label = attr.label.value
        if raw_label:
            key = raw_label.strip().lower()
            standard = _LABEL_NORMALIZATION_MAP.get(key)
            if standard and standard != raw_label:
                print(f"  [normalize_attribute_labels] '{raw_label}' -> '{standard}'")
                # Replace only the label value, keep all provenance metadata intact
                new_label_fv = FieldValue(
                    value=standard,
                    source_type=attr.label.source_type,
                    confidence=attr.label.confidence,
                    source_url=attr.label.source_url,
                    source_snippet=attr.label.source_snippet,
                )
                attr = AttributeEntry(label=new_label_fv, value=attr.value, uom=attr.uom)
        normalized.append(attr)
    return normalized


def log_unresolved_taxonomy_labels(attributes: List[AttributeEntry]) -> List[str]:
    """
    Returns a list of label names for attributes where value.value is None or empty/null.
    Preserves diagnostic visibility into taxonomy labels that were checked but not found.
    """
    unresolved: List[str] = []
    for attr in attributes:
        lbl = attr.label.value if attr.label else None
        if lbl:
            val = attr.value.value if attr.value else None
            val_str = str(val).strip() if val is not None else ""
            if not val_str or val_str.lower() in ["none", "null", "n/a", ""]:
                unresolved.append(lbl)
    return unresolved


def filter_null_attributes(attributes: List[AttributeEntry]) -> List[AttributeEntry]:
    """
    Removes any AttributeEntry where value.value is None, empty string, or 'null'/'none'/'n/a'.
    Drops empty slots so real attributes aren't crowded out of the 50-slot limit.
    """
    valid: List[AttributeEntry] = []
    for attr in attributes:
        if attr.value and attr.value.value is not None:
            val_str = str(attr.value.value).strip()
            if val_str and val_str.lower() not in ["none", "null", "n/a", ""]:
                valid.append(attr)
    return valid


def decimal_to_fraction_inches(value: str) -> str:
    """
    Converts decimal inch measurements in a string to fractional inch notation (nearest 1/16").
    e.g. '33.625' -> '33-5/8', '50.188 in' -> '50-3/16 in',
         '33.625 in H x 23.8 in W x 26.75 in D' -> '33-5/8 in H x 23-13/16 in W x 26-3/4 in D'.
    """
    import math, re

    if not isinstance(value, str) or not value.strip():
        return value

    def _convert_match(match):
        num_str = match.group(1)
        try:
            val_float = float(num_str)
        except ValueError:
            return match.group(0)

        if val_float <= 0:
            return match.group(0)

        whole = int(math.floor(val_float))
        frac = val_float - whole
        sixteenths = int(round(frac * 16))
        if sixteenths == 16:
            whole += 1
            sixteenths = 0

        if sixteenths == 0:
            converted = str(whole)
        else:
            g = math.gcd(sixteenths, 16)
            num = sixteenths // g
            den = 16 // g
            if whole == 0:
                converted = f"{num}/{den}"
            else:
                converted = f"{whole}-{num}/{den}"

        suffix = match.group(2) if match.lastindex and match.lastindex >= 2 and match.group(2) else ""
        return f"{converted}{suffix}"

    pattern = r'\b(\d+\.\d+)(\s*(?:in\b|in\.|inch\b|inches\b))?'
    return re.sub(pattern, _convert_match, value, flags=re.IGNORECASE)


def enrich_product_record(raw_row: dict, source_row_index: int) -> ProductRecord:
    """
    Top-level orchestration function:
    Raw row -> Identify manufacturer -> Find official URLs -> Extract fields -> Map FieldValues
    -> Generate descriptions -> Compute count metrics -> Set status & timestamps.
    """
    # 1. Initialize record with given raw inputs
    record = ProductRecord(
        source_row_index=source_row_index,
        part_number=str(raw_row.get("PART_NUMBER") or raw_row.get("Mfg_Part_Num") or ""),
        dept=raw_row.get("Dept"),
        product_class=raw_row.get("Class"),
        fine_class=raw_row.get("Fine"),
        sku=raw_row.get("SKU - MY_PART_NUMBER"),
        mfg_part_num=str(raw_row.get("Mfg_Part_Num") or ""),
        part_desc=raw_row.get("Part_Desc"),
        e1_brand=raw_row.get("E1_Brand"),
        unilog_brand=raw_row.get("Unilog_Brand"),
        dib_brand=raw_row.get("DIB_Brand"),
        part_manuf=raw_row.get("Part_Manuf"),
    )

    # 2. Identify real manufacturer & brand
    mfr_info = identify_manufacturer(
        part_manuf=record.part_manuf or "",
        part_desc=record.part_desc or "",
        mfg_part_num=record.mfg_part_num or ""
    )
    if mfr_info.get("manufacturer_name"):
        record.manufacturer_name = FieldValue(
            value=mfr_info["manufacturer_name"],
            source_type="extracted",
            confidence=mfr_info.get("confidence", 0.95),
            source_url=mfr_info.get("source_url"),
            source_snippet=mfr_info.get("source_snippet")
        )
    if mfr_info.get("brand_name"):
        record.brand_name = FieldValue(
            value=mfr_info["brand_name"],
            source_type="extracted",
            confidence=mfr_info.get("confidence", 0.95),
            source_url=mfr_info.get("source_url"),
            source_snippet=mfr_info.get("source_snippet")
        )

    # 3. Find official product/support page & reference URLs
    effective_mfr = record.manufacturer_name.value or record.part_manuf or ""
    effective_brand = record.brand_name.value or record.e1_brand or ""
    mfr_page_info = find_manufacturer_page(
        manufacturer_name=effective_mfr,
        mfg_part_num=record.mfg_part_num or "",
        part_desc=record.part_desc or "",
        brand_name=effective_brand
    )

    if mfr_page_info.get("mfr_url"):
        record.mfr_url = FieldValue(
            value=mfr_page_info["mfr_url"],
            source_type="extracted",
            confidence=0.95,
            source_url=mfr_page_info["mfr_url"],
            source_snippet="Official Manufacturer Product Page"
        )
    if mfr_page_info.get("candidate_ref_urls"):
        record.ref_urls = mfr_page_info["candidate_ref_urls"]

    # 4. Fetch and extract structured fields
    mfr_url_val = record.mfr_url.value or ""
    extracted_data = fetch_and_extract_fields(
        mfr_url=mfr_url_val,
        ref_urls=record.ref_urls,
        part_desc=record.part_desc or "",
        mfg_part_num=record.mfg_part_num or ""
    )
    # Store content diagnostics for external inspection
    record.content_diagnostics = extracted_data.pop("_content_diagnostics", [])

    # Map single fields
    record.trade_name = _map_field(extracted_data.get("trade_name"), mfr_url_val)
    record.classpath = _map_field(extracted_data.get("classpath"), mfr_url_val)
    record.with_features = _map_field(extracted_data.get("with_features"), mfr_url_val)
    record.standard_approvals = _map_field(extracted_data.get("standard_approvals"), mfr_url_val)
    record.prop_65 = _map_field(extracted_data.get("prop_65"), mfr_url_val)
    record.application = _map_field(extracted_data.get("application"), mfr_url_val)
    record.includes = _map_field(extracted_data.get("includes"), mfr_url_val)
    record.product_name = _map_field(extracted_data.get("product_name"), mfr_url_val)

    record.upc = _map_field(extracted_data.get("upc"), mfr_url_val)
    record.ean = _map_field(extracted_data.get("ean"), mfr_url_val)
    record.gtin = _map_field(extracted_data.get("gtin"), mfr_url_val)
    record.unspsc = _map_field(extracted_data.get("unspsc"), mfr_url_val)

    record.warranty = _map_field(extracted_data.get("warranty"), mfr_url_val)
    record.list_price = _map_field(extracted_data.get("list_price"), mfr_url_val)
    record.selling_qty = _map_field(extracted_data.get("selling_qty"), mfr_url_val)
    record.selling_uom = _map_field(extracted_data.get("selling_uom"), mfr_url_val)
    record.standard_packaging_info = _map_field(extracted_data.get("standard_packaging_info"), mfr_url_val)

    record.length = _map_field(extracted_data.get("length"), mfr_url_val)
    record.length_uom = _map_field(extracted_data.get("length_uom"), mfr_url_val)
    record.height = _map_field(extracted_data.get("height"), mfr_url_val)
    record.height_uom = _map_field(extracted_data.get("height_uom"), mfr_url_val)
    record.width = _map_field(extracted_data.get("width"), mfr_url_val)
    record.width_uom = _map_field(extracted_data.get("width_uom"), mfr_url_val)
    record.weight = _map_field(extracted_data.get("weight"), mfr_url_val)
    record.weight_uom = _map_field(extracted_data.get("weight_uom"), mfr_url_val)
    record.volume = _map_field(extracted_data.get("volume"), mfr_url_val)
    record.volume_uom = _map_field(extracted_data.get("volume_uom"), mfr_url_val)

    record.country_of_origin = _map_field(extracted_data.get("country_of_origin"), mfr_url_val)
    record.discontinued = _map_field(extracted_data.get("discontinued"), mfr_url_val)
    record.actual_image_yn = _map_field(extracted_data.get("actual_image_yn"), mfr_url_val)

    # Map item features (up to 20)
    raw_feats = extracted_data.get("item_features", [])
    feat_entries = []
    for f in raw_feats[:20]:
        if isinstance(f, dict):
            feat_entries.append(FeatureEntry(text=_map_field(f, mfr_url_val)))
        elif isinstance(f, str) and f.strip():
            feat_entries.append(FeatureEntry(text=FieldValue(value=f.strip(), source_type="extracted", confidence=0.95, source_url=mfr_url_val)))
    # Map attributes (up to 50), normalize labels, track unresolved taxonomy labels, and filter nulls
    raw_attrs = extracted_data.get("attributes", [])
    attr_entries = []
    for a in raw_attrs[:50]:
        entry = _extract_attr_entry(a, mfr_url_val)
        if entry:
            attr_entries.append(entry)
    normalized_attrs = normalize_attribute_labels(attr_entries)
    record.unresolved_taxonomy_labels = log_unresolved_taxonomy_labels(normalized_attrs)
    record.attributes = filter_null_attributes(normalized_attrs)

    # Map digital assets
    raw_assets = extracted_data.get("assets", [])
    asset_entries = []
    for asset_item in raw_assets:
        if isinstance(asset_item, dict) and asset_item.get("asset_type"):
            url_val = asset_item.get("url")
            url_fv = _map_field(url_val, mfr_url_val) if isinstance(url_val, dict) else FieldValue(value=str(url_val), source_type="extracted", confidence=0.95, source_url=mfr_url_val)
            asset_entries.append(AssetLink(asset_type=asset_item["asset_type"], url=url_fv))
    record.assets = asset_entries

    # 5. Generate descriptions from enriched attributes
    generate_description_formats(record)

    # 5b. Post-process decimal inch measurements to fractional notation
    LENGTH_ATTR_KEYS = {
        "size", "depth", "height", "width", "minimum height", "maximum height",
        "depth with door open", "belt width", "belt length", "arbor size",
        "thickness", "diameter", "wheel diameter", "overall diameter"
    }

    for attr in record.attributes:
        if attr.value and attr.value.value:
            lbl_key = (attr.label.value or "").strip().lower()
            val_str = str(attr.value.value)
            if lbl_key in LENGTH_ATTR_KEYS or " in" in val_str.lower() or "inch" in val_str.lower() or re.search(r'\b\d+\.\d+\b', val_str):
                if not any(non_len in lbl_key for non_len in ["voltage", "amperage", "power", "weight", "frequency", "sound", "rpm", "speed", "temp", "quantity", "price", "year"]):
                    new_val = decimal_to_fraction_inches(val_str)
                    if new_val != val_str:
                        attr.value.value = new_val

    for dim_field in ["length", "height", "width"]:
        fv = getattr(record, dim_field, None)
        if fv and fv.value is not None:
            val_str = str(fv.value)
            if "." in val_str:
                new_val = decimal_to_fraction_inches(val_str)
                if new_val != val_str:
                    fv.value = new_val

    # 5c. Normalize fraction hyphenation across all generated description fields
    for desc_field in ["mobile_desc", "invoice_desc", "short_desc", "long_desc1", "retail_desc", "marketing_description"]:
        fv = getattr(record, desc_field, None)
        if fv and fv.value and isinstance(fv.value, str):
            norm_desc = normalize_fraction_hyphenation(fv.value)
            if norm_desc != fv.value:
                fv.value = norm_desc

    # 6. Compute counts and pipeline metadata
    all_fvs: List[FieldValue] = [
        record.manufacturer_name, record.brand_name, record.trade_name, record.classpath,
        record.mfr_url, record.mobile_desc, record.invoice_desc, record.short_desc,
        record.long_desc1, record.retail_desc, record.marketing_description,
        record.with_features, record.standard_approvals, record.prop_65,
        record.application, record.includes, record.product_name, record.upc,
        record.ean, record.gtin, record.unspsc, record.warranty, record.list_price,
        record.selling_qty, record.selling_uom, record.standard_packaging_info,
        record.length, record.length_uom, record.height, record.height_uom,
        record.width, record.width_uom, record.weight, record.weight_uom,
        record.volume, record.volume_uom, record.country_of_origin,
        record.discontinued, record.actual_image_yn
    ]
    for a in record.attributes:
        all_fvs.extend([a.label, a.value, a.uom])
    for f in record.item_features:
        all_fvs.append(f.text)

    fields_found = sum(1 for fv in all_fvs if fv.value is not None and fv.source_type in ["extracted", "inferred"])
    fields_total = len(all_fvs)

    record.fields_found_count = fields_found
    record.fields_total_count = fields_total
    record.processed_at = datetime.now(timezone.utc).isoformat()

    # Review status flag threshold (< 30% found = flagged)
    if fields_total > 0 and (fields_found / fields_total) < 0.30:
        record.review_status = "flagged"
    else:
        record.review_status = "pending"

    return record


# ─── Ground truth attributes for Whirlpool WDTS7024RZ (from expected output CSV) ───
WHIRLPOOL_GROUND_TRUTH_ATTRS = [
    {"label": "Series",            "value": "Eco Series",   "uom": ""},
    {"label": "Model",             "value": "WDTS7024RZ",   "uom": ""},
    {"label": "Number of Wash Cycles", "value": "",         "uom": ""},
    {"label": "Voltage Rating",    "value": "120",          "uom": "V"},
    {"label": "Amperage Rating",   "value": "10",           "uom": "A"},
    {"label": "Mounting Type",     "value": "Built-in",     "uom": ""},
    {"label": "Plug Type",         "value": "",             "uom": ""},
    {"label": "Size",              "value": "33-7/16 in H x 23-7/8 in W x 22-5/8 in D", "uom": ""},
    {"label": "Depth With Door Open", "value": "50-3/16",  "uom": "in"},
    {"label": "Minimum Height",    "value": "33-7/16",      "uom": "in"},
    {"label": "Maximum Height",    "value": "",             "uom": ""},
    {"label": "Sound Level",       "value": "41",           "uom": "dBA"},
    {"label": "Material",          "value": "Stainless Steel", "uom": ""},
    {"label": "Color",             "value": "Stainless Steel", "uom": ""},
    {"label": "Additional Information",
     "value": "Folding Tines, Leak Detection System, Moisture Repellent Silverware Basket, Normal Cycle, Quick Wash Cycle, Sani Rinse Option, Sensor Cycle, Triple Wash Spray",
     "uom": ""},
]


def _print_row_result(label: str, rec, row_index: int) -> None:
    """Print standard diagnostic summary for an enriched row."""
    print(f"\n{'='*70}")
    print(f"ROW {row_index}: {label}")
    print(f"{'='*70}")
    print(f"  Manufacturer : {rec.manufacturer_name.value!r}  (confidence={rec.manufacturer_name.confidence:.2f})")
    print(f"  Brand        : {rec.brand_name.value!r}  (confidence={rec.brand_name.confidence:.2f})")
    print(f"  MFR URL      : {rec.mfr_url.value}")
    print(f"  Fields Found : {rec.fields_found_count} / {rec.fields_total_count}")
    print(f"  Review Status: {rec.review_status}")
    print(f"  Attributes ({len(rec.attributes)} total):")
    for attr in rec.attributes:
        val_str = str(attr.value.value) if attr.value.value is not None else ""
        uom_str = str(attr.uom.value) if attr.uom.value else ""
        if uom_str and not val_str.lower().endswith(uom_str.lower()):
            disp = f"{val_str} {uom_str}"
        else:
            disp = val_str
        print(f"    • {attr.label.value} = {disp}")

    # ── Unresolved taxonomy labels diagnostic ──
    unresolved = rec.unresolved_taxonomy_labels or []
    print(f"\n  Unresolved Taxonomy Labels ({len(unresolved)} checked but not found):")
    if unresolved:
        print(f"    • {', '.join(unresolved)}")
    else:
        print("    • (none)")

    # ── Content-length diagnostics ──
    diags = rec.content_diagnostics or []
    print(f"\n  Content-Length Diagnostics ({len(diags)} URL(s) fetched):")
    for d in diags:
        flag = " ⚠️  SUSPICIOUSLY SHORT" if d.get("is_short") else ""
        err  = f"  ERROR: {d['error']}" if d.get("error") else ""
        print(f"    URL      : {d.get('url')}")
        print(f"    HTTP     : {d.get('status_code')} | Chars: {d.get('char_count')}{flag}{err}")
        if d.get("is_short"):
            print(f"    Preview  : {d.get('preview')!r}")


def _whirlpool_side_by_side(rec) -> None:
    """Print side-by-side comparison of ground truth vs. pipeline output for Whirlpool WDTS7024RZ."""
    print(f"\n{'─'*70}")
    print("  WHIRLPOOL WDTS7024RZ — Ground Truth Side-by-Side Comparison")
    print(f"{'─'*70}")
    print(f"  {'GROUND TRUTH LABEL':<38} {'GT VALUE':<22} {'PIPELINE RESULT'}")
    print(f"  {'-'*36} {'-'*20} {'-'*24}")

    # Build lookup from pipeline attributes
    pipeline_lookup: Dict[str, tuple] = {}
    for attr in rec.attributes:
        if attr.label.value:
            key = attr.label.value.lower().strip()
            val = attr.value.value or ""
            uom = attr.uom.value or ""
            pipeline_lookup[key] = (val, uom)

    for gt in WHIRLPOOL_GROUND_TRUTH_ATTRS:
        gt_label = gt["label"]
        gt_val   = gt["value"]
        gt_uom   = gt["uom"]
        gt_display = f"{gt_val} {gt_uom}".strip() if gt_val else "(no value in GT)"

        key = gt_label.lower().strip()
        if key in pipeline_lookup:
            p_val, p_uom = pipeline_lookup[key]
            if p_uom and not p_val.lower().endswith(p_uom.lower()):
                p_display = f"{p_val} {p_uom}".strip()
            else:
                p_display = p_val.strip()
            # Check match
            if p_val and gt_val:
                match = "✅ FOUND" if gt_val.lower() in p_val.lower() or p_val.lower() in gt_val.lower() else "⚠️  DIFFERENT"
            elif p_val:
                match = "✅ FOUND (GT blank)"
            else:
                match = "❌ FOUND LABEL but NULL value"
            status = f"{match} → {p_display!r}"
        else:
            status = "❌ MISSING"

        print(f"  {gt_label:<38} {gt_display:<22} {status}")

    # Show any extra attributes the pipeline found that aren't in ground truth
    gt_keys = {gt["label"].lower().strip() for gt in WHIRLPOOL_GROUND_TRUTH_ATTRS}
    extras = [(a.label.value, a.value.value, a.uom.value) for a in rec.attributes
              if a.label.value and a.label.value.lower().strip() not in gt_keys]
    if extras:
        print(f"\n  Pipeline found {len(extras)} EXTRA attribute(s) not in ground truth:")
        for lbl, val, uom in extras:
            uom_s = f" {uom}" if uom else ""
            print(f"    + {lbl} = {val}{uom_s}")


if __name__ == "__main__":
    # ── Test rows ────────────────────────────────────────────────────────────
    TEST_ROWS = [
        # Row 0: Whirlpool Dishwasher — we have ground truth for this
        {
            "Mfg_Part_Num": "WDTS7024RZ",
            "Part_Desc": "WDTS7024RZ Dishwasher SS - Display Only",
            "E1_Brand": "-- Unbranded --",
            "Unilog_Brand": "-- No Unilog Brand --",
            "DIB_Brand": "-- No DIB Brand --",
            "Part_Manuf": "Appliance Dealers Cooperative (APPDE)",
        },
        # Row 1: Frigidaire Dishwasher — tests strict retailer domain rejection & fraction hyphenation
        {
            "Mfg_Part_Num": "PDSH4816AF",
            "Part_Desc": "PDSH4816AF Dishwasher SS - Display Only",
            "E1_Brand": "-- Unbranded --",
            "Unilog_Brand": "-- No Unilog Brand --",
            "DIB_Brand": "-- No DIB Brand --",
            "Part_Manuf": "Appliance Dealers Cooperative (APPDE)",
        },
        # Row 2: Milwaukee Metal Cut-Off Disc (tool accessory)
        {
            "Mfg_Part_Num": "49-94-0013",
            "Part_Desc": '49-94-0013 Milw 5"x.045"x7/8" Metal Cut Off Disc',
            "E1_Brand": "-- Unbranded --",
            "Unilog_Brand": "-- No Unilog Brand --",
            "DIB_Brand": "-- No DIB Brand --",
            "Part_Manuf": "Milwaukee Accessory (4031)",
        },
        # Row 3: 3M Cubitron II Stikit Film Disc (abrasive)
        {
            "Mfg_Part_Num": "3MABR-7100075678",
            "Part_Desc": "3M 775L Stikit Film P150 - Cubitron II 50 Disc/Box",
            "E1_Brand": "-- Unbranded --",
            "Unilog_Brand": "-- No Unilog Brand --",
            "DIB_Brand": "-- No DIB Brand --",
            "Part_Manuf": "Jam Industrial Supply LLC (JAMIN)",
        },
        # Row 4: Diablo / Freud Sanding Belt (abrasive/cutting tool)
        {
            "Mfg_Part_Num": "DCB518ASTS06G",
            "Part_Desc": 'DCB518ASTS06G Diablo 1/2"x18" - Sanding Belt 6pc',
            "E1_Brand": "-- Unbranded --",
            "Unilog_Brand": "-- No Unilog Brand --",
            "DIB_Brand": "-- No DIB Brand --",
            "Part_Manuf": "Freud Inc (2435)",
        },
    ]

    print("=" * 70)
    print("  VALIDATION PASS — Broad Multi-Category Enrichment Test")
    print("=" * 70)

    results = []
    for idx, row in enumerate(TEST_ROWS):
        label = f"{row['Mfg_Part_Num']} | {row['Part_Desc'][:50]}"
        print(f"\n[{idx+1}/{len(TEST_ROWS)}] Enriching: {label} ...")
        try:
            rec = enrich_product_record(row, source_row_index=idx)
            results.append((label, rec, None))
        except Exception as exc:
            print(f"  ⛔ ERROR: {exc}")
            results.append((label, None, exc))
        import time
        time.sleep(3.0)

    # ── Print summaries for all rows ──
    for idx, (label, rec, err) in enumerate(results):
        if err:
            print(f"\n{'='*70}\nROW {idx}: {label}\n  ⛔ FAILED: {err}")
            continue
        _print_row_result(label, rec, idx)
        if idx == 0:  # Whirlpool — print side-by-side ground truth comparison
            _whirlpool_side_by_side(rec)
