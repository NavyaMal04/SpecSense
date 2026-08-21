import json
import pandas as pd
import streamlit as st

from theme import (
    inject_css, badge, sidebar_header, breadcrumb, provenance_bar,
    MINT, CORAL, AMBER, CYAN, MUTED
)
import data_access as da

st.set_page_config(page_title="SpecSense — Product Detail", layout="wide", page_icon="🧾")
inject_css()

with st.sidebar:
    sidebar_header()

all_records = da.load_all_records()
all_mpns = [m for m, _r in all_records]

mpn = st.session_state.get("selected_mpn")
if not mpn and all_mpns:
    mpn = all_mpns[0]
    st.session_state["selected_mpn"] = mpn

if not mpn:
    st.markdown('<div class="ss-eyebrow">Review</div>', unsafe_allow_html=True)
    st.title("Product Detail")
    st.info("No product selected — pick one from the Product Browser first.")
    st.stop()

record = da.load_record(mpn)
if record is None:
    st.error(f"No record found for {mpn}.")
    st.stop()

breadcrumb([
    {"label": "SpecSense", "url": "/"},
    {"label": "Product Browser", "url": "/Product_Browser"},
    {"label": f"Product: {mpn}"}
])

# Product Prev/Next Switcher Bar
nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
curr_idx = all_mpns.index(mpn) if mpn in all_mpns else 0

with nav_col1:
    if st.button("← Previous Product", disabled=(curr_idx == 0)):
        st.session_state["selected_mpn"] = all_mpns[curr_idx - 1]
        st.rerun()

with nav_col2:
    selected_from_dropdown = st.selectbox(
        "Jump to Product",
        all_mpns,
        index=curr_idx,
        key="product_dropdown_switcher",
        label_visibility="collapsed",
    )
    if selected_from_dropdown != mpn:
        st.session_state["selected_mpn"] = selected_from_dropdown
        st.rerun()

with nav_col3:
    if st.button("Next Product →", disabled=(curr_idx >= len(all_mpns) - 1)):
        st.session_state["selected_mpn"] = all_mpns[curr_idx + 1]
        st.rerun()

fixed_fields = st.session_state.get("ss_sanitized", {}).get(mpn, [])

# --- Header Card ---
mfr = da.field_get(record, "manufacturer_name").get("value") or "Unknown Manufacturer"
brand = da.field_get(record, "brand_name").get("value") or ""
status = record.get("review_status", "pending")

st.markdown('<div class="ss-eyebrow">Catalog / Product Inspector</div>', unsafe_allow_html=True)
h1, h2 = st.columns([3, 1])
with h1:
    st.title(mpn)
    st.caption(f"**Manufacturer:** {mfr}" + (f"  |  **Brand:** {brand}" if brand else ""))
with h2:
    st.markdown(f"<div style='text-align:right; margin-top:15px;'>{badge(status, status)}</div>", unsafe_allow_html=True)

if fixed_fields:
    st.markdown(f"""
    <div class="ss-card" style="border-color:{AMBER}55;" role="alert">
        <span style="color:{AMBER}; font-family:'JetBrains Mono',monospace; font-size:0.8rem; font-weight:600;">
            ⚠ Auto-corrected malformed data on load: {', '.join(fixed_fields)}
        </span>
    </div>
    """, unsafe_allow_html=True)

# Metrics Summary Bar
c1, c2, c3 = st.columns(3)
c1.metric("Fields Found", f"{record.get('fields_found_count', 0)}/{record.get('fields_total_count', 0)}")
c2.metric("Completeness", f"{da.record_completeness(record)}%")
c3.metric("Attributes Captured", len(record.get("attributes") or []))

# Review Action Buttons
col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("✓ Approve Record", type="primary"):
        record["review_status"] = "approved"
        da.save_record(mpn, record)
        st.toast(f"Approved {mpn}!", icon="✅")
        st.rerun()
with col_b:
    if st.button("⚠ Flag for Review"):
        record["review_status"] = "flagged"
        da.save_record(mpn, record)
        st.toast(f"Flagged {mpn} for review.", icon="⚠")
        st.rerun()
with col_c:
    if st.button("↺ Reset to Pending"):
        record["review_status"] = "pending"
        da.save_record(mpn, record)
        st.toast(f"Reset {mpn} to pending.", icon="↺")
        st.rerun()

st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

# --- Tabbed Navigation ---
tab_fields, tab_provenance, tab_copy, tab_json = st.tabs([
    "📋 Specification Editor",
    "🔍 Provenance & Citations",
    "✨ AI Grounded Copy Preview",
    "📄 Raw JSON View",
])

# === TAB 1: FIELD EDITOR ===
with tab_fields:
    with st.expander("Given Input (Read-Only)", expanded=False):
        df_input = pd.DataFrame([{"Field": label, "Value": record.get(key) or "—"} for key, label in da.IDENTITY_PASSTHROUGH])
        st.dataframe(df_input, hide_index=True, width='stretch')

    def render_section(section_name: str, fields: list):
        section_rows = []
        for key, label in fields:
            fv = da.field_get(record, key)
            section_rows.append({
                "Field": label,
                "_key": key,
                "Value": fv.get("value") if fv.get("value") is not None else "",
                "Type": fv.get("source_type", "unavailable"),
                "Confidence": round((fv.get("confidence") or 0.0) * 100),
                "Source": fv.get("source_url") or "",
            })
        df = pd.DataFrame(section_rows)

        st.markdown(f'<div class="ss-metric-label" style="margin-top:12px;">{section_name}</div>', unsafe_allow_html=True)
        edited = st.data_editor(
            df,
            column_config={
                "_key": None,
                "Field": st.column_config.TextColumn(disabled=True),
                "Value": st.column_config.TextColumn(),
                "Type": st.column_config.TextColumn(disabled=True),
                "Confidence": st.column_config.NumberColumn(disabled=True, format="%d%%"),
                "Source": st.column_config.LinkColumn(disabled=True),
            },
            hide_index=True,
            width='stretch',
            key=f"editor_{section_name}",
        )

        if st.button(f"Save {section_name}", key=f"save_{section_name}"):
            changed = False
            for _, row in edited.iterrows():
                key = row["_key"]
                original_val = df.loc[df["_key"] == key, "Value"].values[0]
                if row["Value"] != original_val:
                    fv = da.field_get(record, key)
                    fv["value"] = row["Value"] if row["Value"] != "" else None
                    fv["source_type"] = "extracted"
                    fv["confidence"] = 1.0
                    fv["source_url"] = None
                    fv["source_snippet"] = "Manually verified by reviewer"
                    record[key] = fv
                    changed = True
            if changed:
                da.save_record(mpn, record)
                st.toast(f"Saved changes to {section_name}.", icon="💾")
                st.rerun()
            else:
                st.info("No changes to save.")

    for section_name, fields in da.SCALAR_SECTIONS.items():
        if section_name in ("Dimensions", "Commercial"):
            continue  # Rendered below using dedicated ergonomic cards with UOM dropdowns
        render_section(section_name, fields)

    # --- Physical Dimensions Card with UOM Dropdowns ---
    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown('<div class="ss-metric-label">Physical Dimensions & Measurement Units</div>', unsafe_allow_html=True)

    length_units = ["in", "mm", "ft", "cm", "m"]
    weight_units = ["lbs", "oz", "kg", "g"]

    d_col1, d_col2 = st.columns(2)

    with d_col1:
        cur_l = da.field_get(record, "length").get("value")
        cur_l_uom = da.field_get(record, "length_uom").get("value") or "in"
        val_l = st.text_input("Length", value=str(cur_l) if cur_l is not None else "", placeholder="e.g. 18", key="input_l_val")
        uom_l = st.selectbox("Length Unit (UOM)", options=length_units, index=length_units.index(cur_l_uom) if cur_l_uom in length_units else 0, key="sel_l_uom")

        cur_w = da.field_get(record, "width").get("value")
        cur_w_uom = da.field_get(record, "width_uom").get("value") or "in"
        val_w = st.text_input("Width", value=str(cur_w) if cur_w is not None else "", placeholder="e.g. 6", key="input_w_val")
        uom_w = st.selectbox("Width Unit (UOM)", options=length_units, index=length_units.index(cur_w_uom) if cur_w_uom in length_units else 0, key="sel_w_uom")

    with d_col2:
        cur_h = da.field_get(record, "height").get("value")
        cur_h_uom = da.field_get(record, "height_uom").get("value") or "in"
        val_h = st.text_input("Height", value=str(cur_h) if cur_h is not None else "", placeholder="e.g. 2", key="input_h_val")
        uom_h = st.selectbox("Height Unit (UOM)", options=length_units, index=length_units.index(cur_h_uom) if cur_h_uom in length_units else 0, key="sel_h_uom")

        cur_wt = da.field_get(record, "weight").get("value")
        cur_wt_uom = da.field_get(record, "weight_uom").get("value") or "lbs"
        val_wt = st.text_input("Weight", value=str(cur_wt) if cur_wt is not None else "", placeholder="e.g. 1.5", key="input_wt_val")
        uom_wt = st.selectbox("Weight Unit (UOM)", options=weight_units, index=weight_units.index(cur_wt_uom) if cur_wt_uom in weight_units else 0, key="sel_wt_uom")

    if st.button("Save Physical Dimensions", key="save_dimensions_card"):
        def parse_val(v_str):
            if not v_str or not v_str.strip():
                return None
            try:
                return float(v_str.strip())
            except ValueError:
                return v_str.strip()

        def make_fv(val):
            return {
                "value": val,
                "source_type": "extracted" if val is not None else "unavailable",
                "confidence": 1.0 if val is not None else 0.0,
                "source_url": None,
                "source_snippet": "Manually verified by reviewer" if val is not None else None,
            }

        parsed_l = parse_val(val_l)
        record["length"] = make_fv(parsed_l)
        record["length_uom"] = make_fv(uom_l if parsed_l is not None else None)

        parsed_w = parse_val(val_w)
        record["width"] = make_fv(parsed_w)
        record["width_uom"] = make_fv(uom_w if parsed_w is not None else None)

        parsed_h = parse_val(val_h)
        record["height"] = make_fv(parsed_h)
        record["height_uom"] = make_fv(uom_h if parsed_h is not None else None)

        parsed_wt = parse_val(val_wt)
        record["weight"] = make_fv(parsed_wt)
        record["weight_uom"] = make_fv(uom_wt if parsed_wt is not None else None)

        da.save_record(mpn, record)
        st.toast("Saved physical dimensions!", icon="💾")
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # --- Commercial & Packaging Card with Selling UOM Dropdown ---
    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown('<div class="ss-metric-label">Commercial & Selling Information</div>', unsafe_allow_html=True)

    selling_uom_options = ["EA", "PK", "BOX", "RL", "SET", "CT", "BAG", "PAIR", "DOZ"]

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        cur_price = da.field_get(record, "list_price").get("value")
        val_price = st.text_input("List Price ($)", value=str(cur_price) if cur_price is not None else "", placeholder="e.g. 29.99", key="input_price")

        cur_sqty = da.field_get(record, "selling_qty").get("value")
        val_sqty = st.text_input("Selling Quantity", value=str(cur_sqty) if cur_sqty is not None else "", placeholder="e.g. 1", key="input_sqty")

    with c_col2:
        cur_suom = da.field_get(record, "selling_uom").get("value") or "EA"
        val_suom = st.selectbox(
            "Selling Unit (UOM)",
            options=selling_uom_options,
            index=selling_uom_options.index(cur_suom) if cur_suom in selling_uom_options else 0,
            key="sel_suom"
        )

        cur_warr = da.field_get(record, "warranty").get("value")
        val_warr = st.text_input("Warranty Information", value=str(cur_warr) if cur_warr is not None else "", placeholder="e.g. 1 Year Limited", key="input_warranty")

    if st.button("Save Commercial Specs", key="save_commercial_card"):
        def parse_price(v_str):
            if not v_str or not v_str.strip():
                return None
            try:
                return float(v_str.strip().replace("$", ""))
            except ValueError:
                return v_str.strip()

        parsed_p = parse_price(val_price)
        record["list_price"] = make_fv(parsed_p)

        record["selling_qty"] = make_fv(val_sqty if val_sqty.strip() else None)
        record["selling_uom"] = make_fv(val_suom if val_sqty.strip() else None)
        record["warranty"] = make_fv(val_warr if val_warr.strip() else None)

        da.save_record(mpn, record)
        st.toast("Saved commercial specs!", icon="💾")
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Item Features
    st.markdown('<div class="ss-metric-label" style="margin-top:14px;">Item Features</div>', unsafe_allow_html=True)
    features = record.get("item_features") or []
    feat_df = pd.DataFrame([{"Feature": (f.get("text") or {}).get("value") or ""} for f in features]) if features else pd.DataFrame({"Feature": []})
    feat_edited = st.data_editor(feat_df, num_rows="dynamic", hide_index=True, width='stretch', key="editor_features")
    if st.button("Save Item Features"):
        new_features = []
        for _, row in feat_edited.iterrows():
            text = row.get("Feature", "")
            if text:
                new_features.append({"text": {"value": text, "source_type": "extracted", "confidence": 1.0, "source_url": None, "source_snippet": "Manually verified by reviewer"}})
        record["item_features"] = new_features
        da.save_record(mpn, record)
        st.toast("Saved item features.", icon="💾")
        st.rerun()

    # Attributes
    st.markdown('<div class="ss-metric-label" style="margin-top:14px;">Attributes</div>', unsafe_allow_html=True)
    attrs = record.get("attributes") or []
    attr_rows = [{
        "Label": (a.get("label") or {}).get("value") or "",
        "Value": (a.get("value") or {}).get("value") or "",
        "UOM": (a.get("uom") or {}).get("value") or "",
    } for a in attrs]
    attr_df = pd.DataFrame(attr_rows) if attr_rows else pd.DataFrame({"Label": [], "Value": [], "UOM": []})
    
    uom_dropdown_options = ["", "in", "mm", "ft", "cm", "m", "lbs", "oz", "kg", "g", "V", "W", "A", "RPM", "PSI", "EA", "PK", "BOX", "RL", "SET", "CT", "BAG", "PAIR", "DOZ", "N/A"]
    attr_edited = st.data_editor(
        attr_df,
        column_config={
            "Label": st.column_config.TextColumn("Attribute Label"),
            "Value": st.column_config.TextColumn("Attribute Value"),
            "UOM": st.column_config.SelectboxColumn("Unit of Measure (UOM)", options=uom_dropdown_options, help="Select dropdown unit"),
        },
        num_rows="dynamic",
        hide_index=True,
        width='stretch',
        key="editor_attrs"
    )
    if st.button("Save Attributes"):
        def wrap(v):
            return {"value": v or None, "source_type": "extracted" if v else "unavailable", "confidence": 1.0 if v else 0.0, "source_url": None, "source_snippet": "Manually verified by reviewer" if v else None}
        new_attrs = []
        for _, row in attr_edited.iterrows():
            if row.get("Label") or row.get("Value"):
                new_attrs.append({"label": wrap(row.get("Label")), "value": wrap(row.get("Value")), "uom": wrap(row.get("UOM"))})
        record["attributes"] = new_attrs
        da.save_record(mpn, record)
        st.toast("Saved attributes.", icon="💾")
        st.rerun()


    # Assets
    st.markdown('<div class="ss-metric-label" style="margin-top:14px;">Digital Assets</div>', unsafe_allow_html=True)
    assets = record.get("assets") or []
    asset_rows = [{"Asset Type": a.get("asset_type") or "", "URL": (a.get("url") or {}).get("value") or ""} for a in assets]
    asset_df = pd.DataFrame(asset_rows) if asset_rows else pd.DataFrame({"Asset Type": [], "URL": []})
    asset_edited = st.data_editor(asset_df, num_rows="dynamic", hide_index=True, width='stretch', key="editor_assets")
    if st.button("Save Assets"):
        new_assets = []
        for _, row in asset_edited.iterrows():
            if row.get("Asset Type") and row.get("URL"):
                new_assets.append({
                    "asset_type": row["Asset Type"],
                    "url": {"value": row["URL"], "source_type": "extracted", "confidence": 1.0, "source_url": None, "source_snippet": "Manually verified by reviewer"},
                })
        record["assets"] = new_assets
        da.save_record(mpn, record)
        st.toast("Saved assets.", icon="💾")
        st.rerun()

# === TAB 2: PROVENANCE & CITATIONS ===
with tab_provenance:
    st.markdown('<div class="ss-metric-label">Field-Level Data Provenance Inspector</div>', unsafe_allow_html=True)
    
    prov_single = da.calculate_provenance_stats([(mpn, record)])
    provenance_bar(prov_single["extracted_pct"], prov_single["inferred_pct"], prov_single["unavailable_pct"])

    st.markdown("")
    st.caption("Detailed Web & LLM extraction citations for populated fields:")

    citations = []
    for section, fields in da.SCALAR_SECTIONS.items():
        for key, label in fields:
            fv = da.field_get(record, key)
            if fv.get("value") is not None:
                citations.append({
                    "Section": section,
                    "Field": label,
                    "Value": str(fv.get("value"))[:60],
                    "Source Type": fv.get("source_type", "unavailable"),
                    "Confidence": f"{round((fv.get('confidence') or 0.0) * 100)}%",
                    "Source URL": fv.get("source_url") or "—",
                    "Snippet": fv.get("source_snippet") or "—",
                })

    if citations:
        df_cit = pd.DataFrame(citations)
        st.dataframe(
            df_cit,
            column_config={
                "Source URL": st.column_config.LinkColumn(),
            },
            hide_index=True,
            width="stretch"
        )
    else:
        st.info("No field citations recorded for this product.")

# === TAB 3: AI GROUNDED COMMERCE COPY ===
with tab_copy:
    st.markdown('<div class="ss-metric-label">Grounded E-Commerce Copy Preview</div>', unsafe_allow_html=True)
    st.caption("AI-generated titles, bullet points, descriptions, and FAQs grounded in verified product specs.")

    m_desc = da.field_get(record, "mobile_desc").get("value") or "Not generated"
    s_desc = da.field_get(record, "short_desc").get("value") or "Not generated"
    l_desc = da.field_get(record, "long_desc1").get("value") or "Not generated"
    mkt_desc = da.field_get(record, "marketing_description").get("value") or "Not generated"

    st.markdown("**Mobile Optimized Description**")
    st.code(m_desc, language="text")

    st.markdown("**Short Commerce Description**")
    st.code(s_desc, language="text")

    st.markdown("**Long Feature Description**")
    st.code(l_desc, language="text")

    st.markdown("**Marketing Highlights**")
    st.code(mkt_desc, language="text")

    st.markdown("**Key Feature Bullet Points**")
    if features:
        for idx, feat in enumerate(features, 1):
            text_val = (feat.get("text") or {}).get("value", "")
            st.markdown(f"- **{text_val}**")
    else:
        st.caption("No feature bullets recorded.")

# === TAB 4: RAW JSON VIEW ===
with tab_json:
    st.markdown('<div class="ss-metric-label">Raw Record JSON</div>', unsafe_allow_html=True)
    st.json(record)
    
    json_bytes = json.dumps(record, indent=2, ensure_ascii=False).encode("utf-8")
    st.download_button(
        f"⬇ Download {mpn}.json",
        data=json_bytes,
        file_name=f"{mpn}.json",
        mime="application/json",
        type="primary",
    )

