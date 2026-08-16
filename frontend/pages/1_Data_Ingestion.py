import os

import requests
import streamlit as st

from theme import inject_css, badge, system_status_pill, MINT, CORAL, CYAN, MUTED

st.set_page_config(page_title="SpecSense — Data Ingestion", layout="wide", page_icon="📥")
inject_css()

API_URL = os.environ.get("SPECSENSE_API_URL", "http://localhost:8000")
CORE_FIELDS = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]
BADGE_KIND = {"extracted": "verified", "inferred": "inferred", "flagged": "flagged"}

with st.sidebar:
    st.markdown("### ◈ SpecSense")
    st.caption("PRECISION OPERATIONS")
    system_status_pill()

st.markdown('<div class="ss-eyebrow">Ingestion / Single Document</div>', unsafe_allow_html=True)
st.title("Data Ingestion")
st.caption("Secure node uplink ready. Awaiting payload.")

st.markdown('<div class="ss-card" style="text-align:center; padding:48px 24px;">', unsafe_allow_html=True)
st.markdown(
    f'<div style="font-size:2.2rem;">☁</div>'
    f'<div style="font-family:\'Space Grotesk\',sans-serif; font-size:1.4rem; font-weight:700; margin-top:10px;">Initialize Payload Transfer</div>'
    f'<div style="font-family:\'JetBrains Mono\',monospace; font-size:0.82rem; color:{MUTED}; margin-top:6px;">'
    f'Drop a spec sheet PDF, or browse your local directory below.</div>',
    unsafe_allow_html=True,
)
uploaded = st.file_uploader(" ", type=["pdf"], label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

if uploaded and st.button("▶ Process Payload", type="primary"):
    with st.spinner("Extracting, tagging, inferring, and generating copy..."):
        resp = requests.post(
            f"{API_URL}/upload",
            files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
        )
    if resp.status_code != 200:
        st.error(f"Failed ({resp.status_code}): {resp.text}")
    else:
        st.session_state["last_record"] = resp.json()

if "last_record" in st.session_state:
    record = st.session_state["last_record"]
    st.markdown("")
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <div class="ss-eyebrow">Target Entity / Component Analysis</div>
            <div style="font-family:'Space Grotesk',sans-serif; font-size:1.5rem; font-weight:700;">
                {record['name']['value'] or record['source_file']}
            </div>
        </div>
        <div class="ss-status-pill">◎ SCAN COMPLETE</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    cols = st.columns(4)
    for i, field_name in enumerate(CORE_FIELDS):
        field = record[field_name]
        kind = BADGE_KIND.get(field["source_type"], "pending")
        val = field["value"] if field["value"] is not None else "—"
        with cols[i % 4]:
            st.markdown(f"""
            <div class="ss-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="ss-metric-label" style="margin-bottom:0;">{field_name.upper()}</span>
                    {badge(field['source_type'], kind)}
                </div>
                <div style="font-family:'Space Grotesk',sans-serif; font-size:1.3rem; font-weight:700; margin-top:8px;">{val}</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:{MUTED}; margin-top:4px;">
                    {'Confidence: ' + f"{field['confidence']:.0%}" if field['confidence'] is not None else ''}
                    {' · ' + field['source_location'] if field.get('source_location') else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)

    if record.get("additional_attributes"):
        st.markdown('<div class="ss-metric-label" style="margin-top:8px;">Additional Attributes</div>', unsafe_allow_html=True)
        cols2 = st.columns(4)
        for i, attr in enumerate(record["additional_attributes"]):
            kind = BADGE_KIND.get(attr["source_type"], "pending")
            with cols2[i % 4]:
                st.markdown(f"""
                <div class="ss-card">
                    {badge(attr['source_type'], kind)}
                    <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; margin-top:8px;">{attr['value']}</div>
                </div>
                """, unsafe_allow_html=True)

    if record.get("title", {}).get("value"):
        st.markdown("")
        st.markdown(f"""
        <div class="ss-card">
            <div class="ss-eyebrow">✦ Synthesized Commerce Copy</div>
            <div style="font-family:'Space Grotesk',sans-serif; font-size:1.1rem; font-weight:700; margin:6px 0;">{record['title']['value']}</div>
            <div style="font-size:0.92rem; color:{MUTED}; line-height:1.6;">{record['short_description']['value']}</div>
        </div>
        """, unsafe_allow_html=True)

        if record.get("feature_bullets", {}).get("value"):
            st.markdown('<div class="ss-metric-label">Feature Bullets</div>', unsafe_allow_html=True)
            for b in record["feature_bullets"]["value"]:
                st.markdown(f"- {b}")

        if record.get("faq", {}).get("value"):
            st.markdown('<div class="ss-metric-label" style="margin-top:10px;">FAQ</div>', unsafe_allow_html=True)
            for item in record["faq"]["value"]:
                with st.expander(item["question"]):
                    st.write(item["answer"])
    elif any(record[k]["source_type"] == "flagged" for k in CORE_FIELDS):
        st.markdown(f"""
        <div class="ss-card" style="border-color:{CORAL}55;">
            <span style="color:{CORAL}; font-family:'JetBrains Mono',monospace; font-size:0.85rem;">
                ⚠ Commerce copy withheld — resolve flagged fields in Anomaly Review, then re-run ingestion.
            </span>
        </div>
        """, unsafe_allow_html=True)
