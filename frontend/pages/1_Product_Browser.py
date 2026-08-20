import streamlit as st

from theme import inject_css, badge, sidebar_header, breadcrumb, MINT, CORAL, AMBER, CYAN, MUTED
import data_access as da

st.set_page_config(page_title="SpecSense — Product Browser", layout="wide", page_icon="🔎")
inject_css()

with st.sidebar:
    sidebar_header()

breadcrumb([{"label": "SpecSense", "url": "/"}, {"label": "Product Browser"}])

st.markdown('<div class="ss-eyebrow">Catalog Explorer</div>', unsafe_allow_html=True)
st.title("Product Browser")
st.caption("Search, filter, bulk manage, and inspect catalog products.")

records = da.load_all_records()

if not records:
    st.markdown("""
    <div class="ss-card" style="text-align:center; padding:40px;" role="alert">
        No products found in data/batch_output/ yet.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- Search & Filter & Sort Bar ---
col_search, col_filter, col_sort = st.columns([2.2, 1, 1.2])
with col_search:
    query = st.text_input("Search by Part Number, Manufacturer, or Brand", "", placeholder="e.g. Wera, Milwaukee, 05134...")
with col_filter:
    status_filter = st.selectbox("Review Status", ["All", "pending", "approved", "flagged"])
with col_sort:
    sort_by = st.selectbox("Sort By", ["Completeness (High → Low)", "Completeness (Low → High)", "MPN (A-Z)", "Manufacturer (A-Z)"])

rows = []
for mpn, rec in records:
    mfr = da.field_get(rec, "manufacturer_name").get("value") or ""
    brand = da.field_get(rec, "brand_name").get("value") or ""
    status = rec.get("review_status", "pending")

    if status_filter != "All" and status != status_filter:
        continue
    if query and query.lower() not in f"{mpn} {mfr} {brand}".lower():
        continue

    rows.append({
        "mpn": mpn,
        "part_desc": (rec.get("part_desc") or "")[:65],
        "manufacturer": mfr or "—",
        "brand": brand or "—",
        "completeness": da.record_completeness(rec),
        "status": status,
        "raw_record": rec,
    })

# Sorting logic
if sort_by == "Completeness (High → Low)":
    rows.sort(key=lambda x: x["completeness"], reverse=True)
elif sort_by == "Completeness (Low → High)":
    rows.sort(key=lambda x: x["completeness"])
elif sort_by == "MPN (A-Z)":
    rows.sort(key=lambda x: x["mpn"].lower())
elif sort_by == "Manufacturer (A-Z)":
    rows.sort(key=lambda x: x["manufacturer"].lower())

st.caption(f"Displaying {len(rows)} of {len(records)} catalog records")

# --- Bulk Action Toolbar ---
st.markdown('<div class="ss-card" style="padding:14px 20px; margin-bottom:12px;">', unsafe_allow_html=True)
b1, b2, b3, b4, b5 = st.columns([1.2, 1.2, 1.2, 1.4, 1.4])

selected_mpns = st.session_state.get("browser_selected_mpns", set())

with b1:
    if st.button("✓ Bulk Approve", help="Approve all selected records"):
        if selected_mpns:
            count = da.bulk_update_status(list(selected_mpns), "approved")
            st.toast(f"Approved {count} selected records!", icon="✅")
            st.rerun()
        else:
            st.warning("No records checked.")

with b2:
    if st.button("⚠ Bulk Flag", help="Flag all selected records for review"):
        if selected_mpns:
            count = da.bulk_update_status(list(selected_mpns), "flagged")
            st.toast(f"Flagged {count} selected records!", icon="⚠")
            st.rerun()
        else:
            st.warning("No records checked.")

with b3:
    if st.button("↺ Bulk Reset", help="Reset selected records to pending"):
        if selected_mpns:
            count = da.bulk_update_status(list(selected_mpns), "pending")
            st.toast(f"Reset {count} selected records to pending.", icon="↺")
            st.rerun()
        else:
            st.warning("No records checked.")

with b4:
    if st.button("⚔ Compare (2-3)", help="Compare selected products side by side"):
        if 2 <= len(selected_mpns) <= 3:
            st.session_state["compare_mpns"] = list(selected_mpns)
            st.switch_page("pages/5_Compare_Products.py")
        else:
            st.warning("Select exactly 2 or 3 products to compare.")

with b5:
    if selected_mpns:
        export_recs = [(m, da.load_record(m)) for m in selected_mpns if da.load_record(m)]
        json_bytes = da.export_records_json(export_recs)
        st.download_button(
            "⬇ Export Selected (JSON)",
            data=json_bytes,
            file_name="selected_products.json",
            mime="application/json",
            key="dl_selected_json",
        )
st.markdown('</div>', unsafe_allow_html=True)

status_kind = {"pending": "pending", "approved": "approved", "flagged": "flagged"}

# --- Table View ---
st.markdown('<div class="ss-card" style="padding:0;">', unsafe_allow_html=True)
header = st.columns([0.4, 1.4, 2.4, 1.6, 1.4, 1, 1.1, 0.9])
for col, label in zip(header, ["", "PART NUMBER", "DESCRIPTION", "MANUFACTURER", "BRAND", "COMPLETE", "STATUS", ""]):
    col.markdown(f'<div class="ss-metric-label">{label}</div>', unsafe_allow_html=True)

new_selected = set()
for row in rows:
    mpn = row["mpn"]
    r = st.columns([0.4, 1.4, 2.4, 1.6, 1.4, 1, 1.1, 0.9])
    
    is_checked = r[0].checkbox(f"Select {mpn}", value=(mpn in selected_mpns), key=f"chk_{mpn}", label_visibility="collapsed")
    if is_checked:
        new_selected.add(mpn)
        
    r[1].markdown(f"<span style='font-family:\"JetBrains Mono\",monospace; font-size:0.85rem; font-weight:600;'>{mpn}</span>", unsafe_allow_html=True)
    r[2].markdown(f"<span style='font-size:0.85rem;'>{row['part_desc']}</span>", unsafe_allow_html=True)
    r[3].markdown(f"<span style='font-size:0.85rem;'>{row['manufacturer']}</span>", unsafe_allow_html=True)
    r[4].markdown(f"<span style='font-size:0.85rem;'>{row['brand']}</span>", unsafe_allow_html=True)
    pct_color = MINT if row["completeness"] >= 60 else (AMBER if row["completeness"] >= 30 else CORAL)
    r[5].markdown(f"<span style='color:{pct_color}; font-family:\"JetBrains Mono\",monospace; font-weight:700;'>{row['completeness']}%</span>", unsafe_allow_html=True)
    r[6].markdown(badge(row["status"], status_kind.get(row["status"], "pending")), unsafe_allow_html=True)
    if r[7].button("Inspect →", key=f"view_{mpn}"):
        st.session_state["selected_mpn"] = mpn
        st.switch_page("pages/2_Product_Detail.py")

st.session_state["browser_selected_mpns"] = new_selected
st.markdown('</div>', unsafe_allow_html=True)

