import os

import requests
import streamlit as st

from theme import inject_css, metric_card, badge, system_status_pill, MINT, CORAL, CYAN, MUTED

st.set_page_config(page_title="SpecSense — Batch Processing", layout="wide", page_icon="📦")
inject_css()

API_URL = os.environ.get("SPECSENSE_API_URL", "http://localhost:8000")
CORE_FIELDS = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]

with st.sidebar:
    st.markdown("### ◈ SpecSense")
    st.caption("PRECISION OPERATIONS")
    system_status_pill()

st.markdown('<div class="ss-eyebrow">Ingestion / Batch</div>', unsafe_allow_html=True)
st.title("Batch Processing")
st.caption("Upload a folder of spec sheets to process a whole catalog in one run.")

st.markdown('<div class="ss-card" style="text-align:center; padding:36px 24px;">', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Product PDFs", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed"
)
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_files and st.button(f"▶ Process {len(uploaded_files)} Documents", type="primary"):
    with st.spinner(f"Processing {len(uploaded_files)} documents..."):
        files = [("files", (f.name, f.getvalue(), "application/pdf")) for f in uploaded_files]
        resp = requests.post(f"{API_URL}/batch", files=files)
    if resp.status_code != 200:
        st.error(f"Failed ({resp.status_code}): {resp.text}")
    else:
        st.session_state["batch_result"] = resp.json()

if "batch_result" in st.session_state:
    result = st.session_state["batch_result"]

    c1, c2, c3, c4 = st.columns(4)
    verified_pct = round(100 * result["fully_verified_count"] / result["processed_count"], 1) if result["processed_count"] else 0.0
    hours_saved = round(result["estimated_manual_minutes"] / 60, 1)

    with c1:
        metric_card("Total Processed", f"{result['processed_count']:,}", f"in {result['elapsed_seconds']}s", MINT)
    with c2:
        metric_card("Fully Verified", f"{verified_pct}%", "target: >95.0%", MINT if verified_pct >= 95 else CYAN)
    with c3:
        flagged_color = CORAL if result["flagged_field_total"] else MINT
        flagged_sub = "⚠ Action Required" if result["flagged_field_total"] else "◉ All clear"
        metric_card("Flagged for Review", f"{result['flagged_field_total']}", flagged_sub, flagged_color)
    with c4:
        metric_card("Compute Time Saved", f"{hours_saved}h", "est. vs manual entry", MINT)

    if result.get("errors"):
        st.markdown(f"""
        <div class="ss-card" style="border-color:{CORAL}55;">
            <span style="color:{CORAL}; font-family:'JetBrains Mono',monospace; font-size:0.85rem;">
                ⚠ {len(result['errors'])} document(s) failed to process
            </span>
        </div>
        """, unsafe_allow_html=True)
        for err in result["errors"]:
            st.caption(f"**{err['filename']}** — {err['error']}")

    st.markdown('<div class="ss-metric-label" style="margin-top:12px;">Recent Sequence Activity</div>', unsafe_allow_html=True)
    st.markdown('<div class="ss-card" style="padding:0;">', unsafe_allow_html=True)

    header = st.columns([2.2, 1.6, 1, 1.2])
    for col, label in zip(header, ["SOURCE FILE", "CATEGORY", "FLAGGED", "STATUS"]):
        col.markdown(f'<div class="ss-metric-label">{label}</div>', unsafe_allow_html=True)

    status_kind = {"pending": "pending", "approved": "verified", "flagged": "flagged"}
    for record in result["records"]:
        row = st.columns([2.2, 1.6, 1, 1.2])
        name = record["name"]["value"] or record["source_file"]
        flagged_ct = sum(1 for k in CORE_FIELDS if record[k]["source_type"] == "flagged")
        row[0].markdown(f"<span style='color:{CYAN};font-family:\"JetBrains Mono\",monospace;font-size:0.85rem;'>{name}</span>", unsafe_allow_html=True)
        row[1].markdown(f"<span style='font-size:0.85rem;color:{MUTED};'>{record['category']['value'] or '—'}</span>", unsafe_allow_html=True)
        row[2].markdown(f"<span style='font-size:0.85rem;'>{flagged_ct}</span>", unsafe_allow_html=True)
        row[3].markdown(badge(record["review_status"], status_kind.get(record["review_status"], "pending")), unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
