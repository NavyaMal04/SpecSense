import os
import streamlit as st

from theme import (
    inject_css, sidebar_header, breadcrumb,
    MINT, CORAL, AMBER, CYAN, MUTED
)
import data_access as da

st.set_page_config(page_title="SpecSense — Run Enrichment", layout="wide", page_icon="⚙")
inject_css()

with st.sidebar:
    sidebar_header()

breadcrumb([{"label": "SpecSense", "url": "/"}, {"label": "Run Live Enrichment"}])

st.markdown('<div class="ss-eyebrow">Pipeline Execution</div>', unsafe_allow_html=True)
st.title("Run Enrichment")
st.caption("Enrich a single part number live using web search + Gemini LLM extraction.")

key_set = bool(os.getenv("GEMINI_API_KEY")) or bool(os.getenv("GEMINI_API_KEY_1"))
if not key_set:
    st.markdown(f"""
    <div class="ss-card" style="border-color:{AMBER}55;" role="alert">
        <span style="color:{AMBER}; font-family:'JetBrains Mono',monospace; font-size:0.82rem; font-weight:600;">
            ⚠ No Gemini API key detected in process environment. Set GEMINI_API_KEY (or GEMINI_API_KEY_1/2/3)
            in .env and restart Streamlit before running a live enrichment.
        </span>
    </div>
    """, unsafe_allow_html=True)

# Preset Samples Toolbar
st.markdown('<div class="ss-metric-label">Quick Sample Presets</div>', unsafe_allow_html=True)
sp1, sp2, sp3 = st.columns(3)
if sp1.button("Pre-fill Wera 05134545001"):
    st.session_state["p_mpn"] = "05134545001"
    st.session_state["p_desc"] = "9516 Kneeling Pad & Bottle Opener"
    st.session_state["p_mfr"] = "Wera Tools NA Inc (WERTO)"
    st.session_state["p_brand"] = "Wera"

if sp2.button("Pre-fill Milwaukee 49-94-0013"):
    st.session_state["p_mpn"] = "49-94-0013"
    st.session_state["p_desc"] = "Diamond Cut-Off Wheel 3in"
    st.session_state["p_mfr"] = "Milwaukee Electric Tool"
    st.session_state["p_brand"] = "Milwaukee"

if sp3.button("Pre-fill DEWALT DCB518ASTS06G"):
    st.session_state["p_mpn"] = "DCB518ASTS06G"
    st.session_state["p_desc"] = "18in Sanding Belt 6pc"
    st.session_state["p_mfr"] = "Freud Inc"
    st.session_state["p_brand"] = "DEWALT"

st.markdown("")

with st.form("enrich_form"):
    c1, c2 = st.columns(2)
    with c1:
        mfg_part_num = st.text_input(
            "Mfg Part Num *",
            value=st.session_state.get("p_mpn", ""),
            placeholder="e.g. DCB518ASTS06G"
        )
        part_desc = st.text_input(
            "Part Desc",
            value=st.session_state.get("p_desc", ""),
            placeholder="e.g. 18\" Sanding Belt 6pc"
        )
    with c2:
        part_manuf = st.text_input(
            "Part Manuf",
            value=st.session_state.get("p_mfr", ""),
            placeholder="e.g. Freud Inc (2435)"
        )
        e1_brand = st.text_input(
            "E1 Brand",
            value=st.session_state.get("p_brand", "-- Unbranded --")
        )
    submitted = st.form_submit_button("▶ Run Live Pipeline", type="primary")

if submitted:
    if not mfg_part_num.strip():
        st.error("Mfg Part Num is required.")
    else:
        raw_row = {
            "Mfg_Part_Num": mfg_part_num.strip(),
            "Part_Desc": part_desc.strip(),
            "Part_Manuf": part_manuf.strip(),
            "E1_Brand": e1_brand.strip(),
            "Unilog_Brand": "-- No Unilog Brand --",
            "DIB_Brand": "-- No DIB Brand --",
        }
        with st.spinner(f"Executing 5-step pipeline for {mfg_part_num}... (15-30s)"):
            try:
                rec = da.run_single_enrichment(raw_row, source_row_index=0)
                safe_mpn = "".join(c if c.isalnum() or c in "-_" else "_" for c in mfg_part_num.strip())
                da.save_record(safe_mpn, rec.model_dump())
                st.session_state["selected_mpn"] = safe_mpn
                st.toast(f"Successfully enriched {safe_mpn}!", icon="✨")
                st.success(f"Enriched and saved as {safe_mpn}. Found {rec.fields_found_count}/{rec.fields_total_count} fields ({da.record_completeness(rec.model_dump())}%).")
                if st.button("→ View Enriched Product Detail"):
                    st.switch_page("pages/2_Product_Detail.py")
            except Exception as e:
                st.markdown(f"""
                <div class="ss-card" style="border-color:{CORAL}55;" role="alert">
                    <span style="color:{CORAL}; font-family:'JetBrains Mono',monospace; font-size:0.82rem; font-weight:600;">
                        ⛔ Enrichment failed: {str(e)[:400]}
                    </span>
                </div>
                """, unsafe_allow_html=True)

st.markdown("")

# Pipeline Step Visualizer
st.markdown('<div class="ss-card">', unsafe_allow_html=True)
st.markdown('<div class="ss-metric-label">Pipeline Execution Workflow</div>', unsafe_allow_html=True)
p_cols = st.columns(5)
p_cols[0].markdown(f"**1. Input Validation**<br><span style='color:{MUTED};font-size:0.75rem;'>Sanitize raw MPN</span>", unsafe_allow_html=True)
p_cols[1].markdown(f"**2. Web Search**<br><span style='color:{MUTED};font-size:0.75rem;'>Gather PDF & web sources</span>", unsafe_allow_html=True)
p_cols[2].markdown(f"**3. Gemini LLM**<br><span style='color:{MUTED};font-size:0.75rem;'>Structured extraction</span>", unsafe_allow_html=True)
p_cols[3].markdown(f"**4. Inference Engine**<br><span style='color:{MUTED};font-size:0.75rem;'>Predict missing fields</span>", unsafe_allow_html=True)
p_cols[4].markdown(f"**5. Unilog Validation**<br><span style='color:{MUTED};font-size:0.75rem;'>Delivery format check</span>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

