import os

import requests
import streamlit as st

from theme import inject_css, flag_item, system_status_pill, MINT, CORAL, CYAN, AMBER, MUTED

st.set_page_config(page_title="SpecSense — Anomaly Review", layout="wide", page_icon="🚨")
inject_css()

API_URL = os.environ.get("SPECSENSE_API_URL", "http://localhost:8000")
CORE_FIELDS = ["name", "category", "dimensions", "material", "voltage", "certifications", "weight", "price"]

KIND_META = {
    "flagged": {"label": "⚠ CONFLICT", "accent": CORAL},
    "inferred": {"label": "◇ INFERRED", "accent": CYAN},
}

with st.sidebar:
    st.markdown("### ◈ SpecSense")
    st.caption("PRECISION OPERATIONS")
    system_status_pill()

try:
    resp = requests.get(f"{API_URL}/products", params={"review_status": "flagged"}, timeout=10)
    products = resp.json() if resp.status_code == 200 else []
    backend_error = None if resp.status_code == 200 else resp.text
except requests.exceptions.RequestException as e:
    products = []
    backend_error = str(e)

st.markdown(f'<div class="ss-eyebrow">Queue / <span style="color:{CYAN};">Anomaly Review</span></div>', unsafe_allow_html=True)
st.title("Anomaly Review")
st.caption(f"Items pending: {len(products)}")

if backend_error and not products:
    st.markdown(f"""
    <div class="ss-card" style="border-color:{CORAL}55;">
        <span style="color:{CORAL}; font-family:'JetBrains Mono',monospace; font-size:0.85rem;">
            ⚠ Could not reach the API at {API_URL}. Check the backend / Firestore config.
        </span>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not products:
    st.markdown(f"""
    <div class="ss-card" style="text-align:center; padding:40px;">
        <span class="ss-status-pill">◎ Nothing flagged — queue is clear</span>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

left, right = st.columns([1, 2])

with left:
    st.markdown('<div class="ss-metric-label">Flagged Items</div>', unsafe_allow_html=True)
    labels = []
    for p in products:
        name = p["name"]["value"] or p["source_file"]
        flagged_fields = [k for k in CORE_FIELDS if p[k]["source_type"] == "flagged"]
        labels.append(f"{name}  ·  {len(flagged_fields)} flagged")
    choice_idx = st.radio("Select a product", options=range(len(products)), format_func=lambda i: labels[i], label_visibility="collapsed")
    product = products[choice_idx]

with right:
    name = product["name"]["value"] or product["source_file"]
    st.markdown(f"""
    <div class="ss-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:{MUTED};">
                📄 SRC: {product['source_file']}
            </span>
            <span class="ss-status-pill">Review Status: {product['review_status']}</span>
        </div>
        <div style="font-family:'Space Grotesk',sans-serif; font-size:1.3rem; font-weight:700; margin-top:10px;">{name}</div>
    </div>
    """, unsafe_allow_html=True)

    flagged_or_inferred = [k for k in CORE_FIELDS if product[k]["source_type"] in ("flagged", "inferred")]

    if not flagged_or_inferred:
        st.info("No field-level anomalies on this record — it may only need a status approval.")

    for field_name in flagged_or_inferred:
        field = product[field_name]
        meta = KIND_META[field["source_type"]]
        flag_item(
            meta["label"], "",
            f"{field_name.replace('_', ' ').title()}: {field['value']}",
            field.get("source_location") or "No source citation — value was inferred from similar products.",
            meta["accent"],
        )

        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_a:
            approve = st.button("✓ Force Approve", key=f"approve_{field_name}", type="primary")
        with col_b:
            corrected = st.text_input("Override value", value=str(field["value"] or ""), key=f"correct_{field_name}", label_visibility="collapsed", placeholder="Override value")
        with col_c:
            submit_correction = st.button("Submit Correction", key=f"submit_{field_name}")

        if approve:
            r = requests.post(f"{API_URL}/products/{product['id']}/review/{field_name}", json={"accept_as_is": True})
            if r.status_code == 200:
                st.rerun()
            else:
                st.error(f"Update failed: {r.text}")
        if submit_correction:
            r = requests.post(
                f"{API_URL}/products/{product['id']}/review/{field_name}",
                json={"accept_as_is": False, "corrected_value": corrected},
            )
            if r.status_code == 200:
                st.rerun()
            else:
                st.error(f"Update failed: {r.text}")
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    for idx, attr in enumerate(product.get("additional_attributes", [])):
        if attr["source_type"] != "flagged":
            continue
        flag_item("⚠ CONFLICT", "", f"Additional: {attr['value']}", attr.get("source_location") or "", CORAL)
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_a:
            approve = st.button("✓ Force Approve", key=f"approve_addl_{idx}", type="primary")
        with col_b:
            corrected = st.text_input("Override value", value=attr["value"] or "", key=f"correct_addl_{idx}", label_visibility="collapsed", placeholder="Override value")
        with col_c:
            submit_correction = st.button("Submit Correction", key=f"submit_addl_{idx}")

        if approve:
            r = requests.post(
                f"{API_URL}/products/{product['id']}/review/_additional",
                json={"accept_as_is": True, "additional_attribute_index": idx},
            )
            if r.status_code == 200:
                st.rerun()
        if submit_correction:
            r = requests.post(
                f"{API_URL}/products/{product['id']}/review/_additional",
                json={"accept_as_is": False, "corrected_value": corrected, "additional_attribute_index": idx},
            )
            if r.status_code == 200:
                st.rerun()
