import streamlit as st

from theme import inject_css, sidebar_header, breadcrumb, MINT, CORAL, MUTED
import data_access as da

st.set_page_config(page_title="SpecSense — Export Catalog", layout="wide", page_icon="📤")
inject_css()

with st.sidebar:
    sidebar_header()

breadcrumb([{"label": "SpecSense", "url": "/"}, {"label": "Export Delivery Catalog"}])

st.markdown('<div class="ss-eyebrow">Delivery & Export</div>', unsafe_allow_html=True)
st.title("Export Delivery Data")
st.caption("Build and download the 252-column Unilog Delivery Format CSV or raw JSON package.")

records = da.load_all_records()

if not records:
    st.info("No products to export yet.")
    st.stop()

c1, c2 = st.columns(2)
with c1:
    st.metric("Total Products Available", len(records))
with c2:
    only_approved = st.checkbox("Only include approved records", value=False)

export_records = records
if only_approved:
    export_records = [(mpn, rec) for mpn, rec in records if rec.get("review_status") == "approved"]
    st.caption(f"{len(export_records)} of {len(records)} records are approved.")

st.markdown("")

export_format = st.radio(
    "Select Export Format",
    options=["Unilog Delivery CSV (252 Columns)", "Full Catalog JSON Package"],
    horizontal=True,
)

if "CSV" in export_format:
    if st.button("▶ Build Delivery CSV", type="primary"):
        csv_bytes, failed = da.build_delivery_csv_bytes(export_records)
        st.session_state["export_csv_bytes"] = csv_bytes
        st.session_state["export_failed"] = failed
        st.toast("Generated Unilog Delivery CSV!", icon="📤")

    if "export_csv_bytes" in st.session_state:
        csv_bytes = st.session_state["export_csv_bytes"]
        failed = st.session_state.get("export_failed", [])

        rows_written = len(export_records) - len(failed)
        st.markdown(f"""
        <div class="ss-card">
            <div class="ss-metric-label">Export Status</div>
            <div class="ss-metric-value">{rows_written} <span style="font-size:1.1rem;color:{MUTED};">rows ready</span></div>
            <div class="ss-metric-sub" style="color:{MINT if not failed else CORAL};">
                {'All records exported cleanly.' if not failed else f'{len(failed)} record(s) failed validation — see below.'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if failed:
            st.markdown(f"""
            <div class="ss-card" style="border-color:{CORAL}55;" role="alert">
                <span style="color:{CORAL}; font-family:'JetBrains Mono',monospace; font-size:0.82rem; font-weight:600;">
                    ⚠ Skipped records with schema errors — review in Product Detail before re-exporting:
                </span>
            </div>
            """, unsafe_allow_html=True)
            for mpn, err in failed:
                st.caption(f"**{mpn}** — {err}")

        st.download_button(
            "⬇ Download delivery_format.csv",
            data=csv_bytes,
            file_name="delivery_format.csv",
            mime="text/csv",
            type="primary",
        )
else:
    json_bytes = da.export_records_json(export_records)
    st.markdown(f"""
    <div class="ss-card">
        <div class="ss-metric-label">JSON Export Ready</div>
        <div class="ss-metric-value">{len(export_records)} <span style="font-size:1.1rem;color:{MUTED};">product objects</span></div>
        <div class="ss-metric-sub" style="color:{MINT};">
            Full nested product records including attributes, assets, provenance, and AI commerce copy.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.download_button(
        "⬇ Download spec_sense_catalog.json",
        data=json_bytes,
        file_name="spec_sense_catalog.json",
        mime="application/json",
        type="primary",
    )

