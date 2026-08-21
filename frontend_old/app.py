from collections import Counter

import streamlit as st

from theme import (
    inject_css, metric_card, donut_ring, progress_row, sidebar_header,
    breadcrumb, provenance_bar, MINT, CORAL, CYAN, AMBER, MUTED
)
import data_access as da

st.set_page_config(page_title="SpecSense — Catalog Dashboard", layout="wide", page_icon="◈")
inject_css()

with st.sidebar:
    sidebar_header()

breadcrumb([{"label": "SpecSense", "url": "/"}, {"label": "Catalog Dashboard"}])

st.markdown('<div class="ss-eyebrow">Telemetry & Overview</div>', unsafe_allow_html=True)
st.title("Catalog Dashboard")
st.caption("Real-time AI enrichment telemetry, provenance analytics, and catalog audit metrics.")

records = da.load_all_records()
summary = da.load_batch_summary()

sanitized = st.session_state.get("ss_sanitized", {})
if sanitized:
    st.markdown(f"""
    <div class="ss-card" style="border-color:{AMBER}55;" role="alert">
        <span style="color:{AMBER}; font-family:'JetBrains Mono',monospace; font-size:0.82rem; font-weight:600;">
            ⚠ {len(sanitized)} record(s) had malformed field types auto-corrected on load
            (e.g. list/bool instead of string) — check Product Detail for: {', '.join(sanitized.keys())}
        </span>
    </div>
    """, unsafe_allow_html=True)

total = len(records)
status_counts = Counter(rec.get("review_status", "pending") for _mpn, rec in records)
avg_completeness = round(sum(da.record_completeness(rec) for _mpn, rec in records) / total, 1) if total else 0.0

prov_stats = da.calculate_provenance_stats(records)
sec_completeness = da.calculate_section_completeness(records)

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(
        "Total Products", f"{total:,}", "catalog records on disk", MINT,
        help_text="Total number of product records saved in data/batch_output/"
    )
with c2:
    metric_card(
        "Avg Completeness", f"{avg_completeness}%", "fields found / total schema", MINT if avg_completeness >= 50 else AMBER,
        help_text="Average percentage of required schema fields populated per product"
    )
with c3:
    flagged = status_counts.get("flagged", 0)
    metric_card(
        "Flagged Records", f"{flagged}", "⚠ requires human review" if flagged else "◉ all clear", CORAL if flagged else MINT,
        help_text="Products flagged by reviewers due to low confidence or conflicting data"
    )
with c4:
    approved = status_counts.get("approved", 0)
    metric_card(
        "Approved Records", f"{approved}", f"of {total} total records", MINT,
        help_text="Products verified and marked ready for delivery export"
    )

st.markdown("")

# Provenance Breakdown Card
st.markdown('<div class="ss-card">', unsafe_allow_html=True)
st.markdown('<div class="ss-metric-label">Catalog Provenance & Confidence Distribution</div>', unsafe_allow_html=True)
provenance_bar(prov_stats["extracted_pct"], prov_stats["inferred_pct"], prov_stats["unavailable_pct"])
st.markdown('</div>', unsafe_allow_html=True)

left, right = st.columns([1.6, 1])

with left:
    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown('<div class="ss-metric-label">Completeness by Product (%)</div>', unsafe_allow_html=True)
    if records:
        chart_data = {mpn: da.record_completeness(rec) for mpn, rec in records}
        st.bar_chart(chart_data, color=CYAN, height=280)
    else:
        st.markdown(
            f'<div style="font-family:\'JetBrains Mono\',monospace; color:{MUTED}; font-size:0.85rem; padding:40px 0; text-align:center;">'
            f'No products in data/batch_output/ yet — run a batch or single enrichment.</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # Section Fill Rate Breakdown
    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown('<div class="ss-metric-label">Schema Section Fill Rates</div>', unsafe_allow_html=True)
    for sec_name, pct in sec_completeness.items():
        bar_color = MINT if pct >= 60 else (CYAN if pct >= 30 else AMBER)
        progress_row(sec_name, pct, bar_color)
    st.markdown('</div>', unsafe_allow_html=True)

    if summary:
        st.markdown('<div class="ss-card">', unsafe_allow_html=True)
        st.markdown('<div class="ss-metric-label">Last Batch Run Telemetry</div>', unsafe_allow_html=True)
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.markdown(f"**{summary.get('total_attempted', 0)}**<br><span style='color:{MUTED};font-size:0.75rem;'>attempted</span>", unsafe_allow_html=True)
        sc2.markdown(f"**{summary.get('total_processed', 0)}**<br><span style='color:{MUTED};font-size:0.75rem;'>processed</span>", unsafe_allow_html=True)
        sc3.markdown(f"**{summary.get('total_errored', 0)}**<br><span style='color:{CORAL if summary.get('total_errored') else MUTED};font-size:0.75rem;'>errored</span>", unsafe_allow_html=True)
        sc4.markdown(f"**{summary.get('total_wall_clock_formatted', '—')}**<br><span style='color:{MUTED};font-size:0.75rem;'>wall time</span>", unsafe_allow_html=True)

        errors = summary.get("errors", [])
        if errors:
            st.markdown(f"<div style='margin-top:10px; color:{CORAL}; font-family:\"JetBrains Mono\",monospace; font-size:0.8rem;'>⚠ {len(errors)} error(s) in last run:</div>", unsafe_allow_html=True)
            for err in errors[:5]:
                st.caption(f"**{err.get('mpn')}** — {err.get('error', '')[:120]}")
            if len(errors) > 5:
                st.caption(f"...and {len(errors) - 5} more")
        st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown('<div class="ss-metric-label" style="text-align:center;">Review Status</div>', unsafe_allow_html=True)
    pending_pct = round(100 * status_counts.get("pending", 0) / total) if total else 0
    donut_ring(pending_pct, "PENDING", AMBER)
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    progress_row("Pending", 100 * status_counts.get("pending", 0) / total if total else 0, AMBER)
    progress_row("Approved", 100 * status_counts.get("approved", 0) / total if total else 0, MINT)
    progress_row("Flagged", 100 * status_counts.get("flagged", 0) / total if total else 0, CORAL)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("")
st.caption("Accessible catalog interface · High-contrast options available in the sidebar.")


