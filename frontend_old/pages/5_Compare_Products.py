import pandas as pd
import streamlit as st

from theme import (
    inject_css, badge, sidebar_header, breadcrumb, provenance_bar,
    MINT, CORAL, AMBER, CYAN, MUTED
)
import data_access as da

st.set_page_config(page_title="SpecSense — Compare Products", layout="wide", page_icon="⚔")
inject_css()

with st.sidebar:
    sidebar_header()

breadcrumb([
    {"label": "SpecSense", "url": "/"},
    {"label": "Product Browser", "url": "/Product_Browser"},
    {"label": "Compare Products"}
])

st.markdown('<div class="ss-eyebrow">Catalog Analysis</div>', unsafe_allow_html=True)
st.title("Product Comparison")
st.caption("Side-by-side specification, provenance, and attribute comparison matrix.")

all_records = da.load_all_records()
all_mpns = [m for m, _r in all_records]

if not all_mpns:
    st.info("No products available to compare.")
    st.stop()

default_selected = st.session_state.get("compare_mpns", [])
if not default_selected and len(all_mpns) >= 2:
    default_selected = all_mpns[:2]

selected_mpns = st.multiselect(
    "Select 2 or 3 products to compare",
    options=all_mpns,
    default=default_selected,
    max_selections=3,
    key="compare_multiselect",
)

if len(selected_mpns) < 2:
    st.info("Please select at least 2 products to display the comparison matrix.")
    st.stop()

compared_records = da.compare_records(selected_mpns)

# --- Summary Comparison Cards ---
cols = st.columns(len(compared_records))
for idx, (mpn, rec) in enumerate(compared_records):
    mfr = da.field_get(rec, "manufacturer_name").get("value") or "Unknown"
    brand = da.field_get(rec, "brand_name").get("value") or "Unbranded"
    completeness = da.record_completeness(rec)
    status = rec.get("review_status", "pending")
    
    with cols[idx]:
        st.markdown('<div class="ss-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="ss-metric-label">{mpn}</div>', unsafe_allow_html=True)
        st.markdown(f"**{mfr}** · {brand}")
        st.markdown(f"Status: {badge(status, status)}", unsafe_allow_html=True)
        st.markdown(f"Completeness: **{completeness}%**")
        prov_single = da.calculate_provenance_stats([(mpn, rec)])
        provenance_bar(prov_single["extracted_pct"], prov_single["inferred_pct"], prov_single["unavailable_pct"])
        if st.button(f"Inspect {mpn} →", key=f"btn_comp_{mpn}"):
            st.session_state["selected_mpn"] = mpn
            st.switch_page("pages/2_Product_Detail.py")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Helper to build comparison dataframe for a list of field tuples
def build_comparison_df(fields: list):
    matrix = []
    for key, label in fields:
        row = {"Specification": label}
        for mpn, rec in compared_records:
            fv = da.field_get(rec, key)
            val = fv.get("value")
            stype = fv.get("source_type", "unavailable")
            
            if val is not None:
                row[mpn] = f"{val} ({stype})"
            else:
                row[mpn] = "—"
        matrix.append(row)
    return pd.DataFrame(matrix)

# --- Section Matrices ---
for section_name, fields in da.SCALAR_SECTIONS.items():
    st.markdown(f'<div class="ss-metric-label" style="margin-top:14px;">{section_name}</div>', unsafe_allow_html=True)
    df_sec = build_comparison_df(fields)
    st.dataframe(df_sec, hide_index=True, width="stretch")

# --- Attributes Comparison ---
st.markdown('<div class="ss-metric-label" style="margin-top:14px;">Captured Attributes Comparison</div>', unsafe_allow_html=True)
all_labels = set()
for _mpn, rec in compared_records:
    for a in rec.get("attributes") or []:
        lbl = (a.get("label") or {}).get("value")
        if lbl:
            all_labels.add(lbl)

if all_labels:
    attr_matrix = []
    for lbl in sorted(all_labels):
        row = {"Attribute": lbl}
        for mpn, rec in compared_records:
            val_found = "—"
            for a in rec.get("attributes") or []:
                if (a.get("label") or {}).get("value") == lbl:
                    val_str = (a.get("value") or {}).get("value") or ""
                    uom_str = (a.get("uom") or {}).get("value") or ""
                    val_found = f"{val_str} {uom_str}".strip() or "✓ Present"
                    break
            row[mpn] = val_found
        attr_matrix.append(row)
    st.dataframe(pd.DataFrame(attr_matrix), hide_index=True, width="stretch")
else:
    st.info("No common attributes captured for comparison.")
