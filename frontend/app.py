import os
from collections import Counter

import requests
import streamlit as st

from theme import inject_css, metric_card, donut_ring, progress_row, system_status_pill, MINT, CORAL, CYAN

st.set_page_config(page_title="SpecSense — Catalog Dashboard", layout="wide", page_icon="◈")
inject_css()

API_URL = os.environ.get("SPECSENSE_API_URL", "http://localhost:8000")
CORE_FIELDS = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]
EST_MANUAL_MINUTES_PER_PRODUCT = 12

with st.sidebar:
    st.markdown("### ◈ SpecSense")
    st.caption("PRECISION OPERATIONS")
    system_status_pill()
    st.markdown("")

st.markdown('<div class="ss-eyebrow">Overview</div>', unsafe_allow_html=True)
st.title("Catalog Dashboard")
st.caption("Live pipeline telemetry across every processed spec sheet.")

try:
    resp = requests.get(f"{API_URL}/products", timeout=10)
    products = resp.json() if resp.status_code == 200 else []
    backend_error = None if resp.status_code == 200 else resp.text
except requests.exceptions.RequestException as e:
    products = []
    backend_error = str(e)

if backend_error and not products:
    st.markdown(f"""
    <div class="ss-card" style="border-color:{CORAL}55;">
        <div class="ss-metric-label" style="color:{CORAL};">Uplink unavailable</div>
        <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#7d8ba0;">
            Could not reach the SpecSense API at {API_URL}, or Firestore isn't configured yet.
            Process a document from Data Ingestion, or check your backend / .env.
        </div>
    </div>
    """, unsafe_allow_html=True)

total = len(products)
field_counts = Counter()
for p in products:
    for k in CORE_FIELDS:
        field_counts[p[k]["source_type"]] += 1

total_fields = sum(field_counts.values()) or 1
extracted_pct = round(100 * field_counts["extracted"] / total_fields)
inferred_pct = round(100 * field_counts["inferred"] / total_fields)
flagged_pct = 100 - extracted_pct - inferred_pct

pending_anomalies = sum(1 for p in products if p["review_status"] == "flagged")
accuracy = round(100 * (1 - field_counts["flagged"] / total_fields), 1) if total_fields else 0.0
hours_saved = round(total * EST_MANUAL_MINUTES_PER_PRODUCT / 60, 1)

category_counts = Counter(
    (p["category"]["value"] or "Uncategorized") for p in products if p["category"]["value"]
)

# --- top stat row -----------------------------------------------------------
c1, c2, c3 = st.columns(3)
with c1:
    metric_card("Total Assets", f"{total:,}", "▲ live catalog count", MINT)
with c2:
    metric_card("Accuracy Rate", f"{accuracy}%", "◉ non-flagged field ratio", MINT)
with c3:
    sub_color = CORAL if pending_anomalies else MINT
    sub_text = "⚠ Action Required" if pending_anomalies else "◉ All clear"
    metric_card("Pending Anomalies", f"{pending_anomalies}", sub_text, sub_color)

st.markdown("")

# --- category breakdown + data integrity ring --------------------------------
left, right = st.columns([1.6, 1])

with left:
    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown('<div class="ss-metric-label">Products by Category</div>', unsafe_allow_html=True)
    if category_counts:
        st.bar_chart(category_counts, color=CYAN, height=300)
    else:
        st.markdown(
            '<div style="font-family:\'JetBrains Mono\',monospace; color:#7d8ba0; font-size:0.85rem; padding:40px 0; text-align:center;">'
            'No categorized products yet — process a spec sheet to populate this chart.</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown('<div class="ss-metric-label" style="text-align:center;">Data Integrity</div>', unsafe_allow_html=True)
    donut_ring(extracted_pct, "PROCESSED", CYAN)
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    progress_row("Extracted", extracted_pct, MINT)
    progress_row("Inferred", inferred_pct, CYAN)
    progress_row("Flagged", flagged_pct, CORAL)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown('<div class="ss-metric-label">Efficiency Delta</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ss-metric-value">{hours_saved} <span style="font-size:1.1rem;color:#7d8ba0;">hrs</span></div>'
        f'<div class="ss-metric-sub" style="color:{MINT};">Est. manual entry time saved</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("")
st.caption("Use the sidebar to ingest new spec sheets, run a batch, or resolve flagged anomalies.")
