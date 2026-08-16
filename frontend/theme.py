"""
frontend/theme.py
==================
Shared visual system for the SpecSense UI: dark ops/telemetry aesthetic —
deep navy background, cyan accent, monospace data labels, card-based
metrics, status chips. Import inject_css() at the top of every page and
use the helper functions below instead of raw st.markdown HTML so the
look stays consistent across pages.

Palette:
  bg        #080b12   near-black navy, page background
  surface   #0f1520   card background
  border    #1c2636   card border / hairlines
  cyan      #22d3ee   primary accent (verified, links, active nav)
  mint      #34d399   positive / inferred
  coral     #fb7185   negative / flagged
  amber     #fbbf24   warning / pending
  text      #e5edf5   primary text
  muted     #7d8ba0   secondary text / labels
"""

import streamlit as st

BG = "#080b12"
SURFACE = "#0f1520"
BORDER = "#1c2636"
CYAN = "#22d3ee"
MINT = "#34d399"
CORAL = "#fb7185"
AMBER = "#fbbf24"
TEXT = "#e5edf5"
MUTED = "#7d8ba0"

BADGE_COLORS = {
    "extracted": MINT,
    "verified": MINT,
    "inferred": CYAN,
    "flagged": CORAL,
    "pending": AMBER,
    "approved": MINT,
    "processing": CYAN,
}


def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Space Grotesk', sans-serif;
    }}

    .stApp {{
        background:
            radial-gradient(circle at 1px 1px, rgba(34,211,238,0.06) 1px, transparent 0) 0 0 / 28px 28px,
            {BG};
    }}

    section[data-testid="stSidebar"] {{
        background: {BG};
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] * {{
        font-family: 'JetBrains Mono', monospace;
    }}

    h1, h2, h3 {{
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
    }}

    .ss-eyebrow {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {MUTED};
        margin-bottom: 0.25rem;
    }}

    .ss-card {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 20px 22px;
        margin-bottom: 14px;
    }}

    .ss-metric-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: {MUTED};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }}
    .ss-metric-value {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: {TEXT};
        line-height: 1.1;
    }}
    .ss-metric-sub {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        margin-top: 6px;
    }}

    .ss-badge {{
        display: inline-block;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 3px 10px;
        border-radius: 999px;
        border: 1px solid currentColor;
    }}

    .ss-flag-item {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-left: 3px solid var(--accent, {CYAN});
        border-radius: 6px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }}
    .ss-flag-title {{
        font-weight: 600;
        font-size: 1rem;
        color: {TEXT};
        margin: 4px 0 4px 0;
    }}
    .ss-flag-desc {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: {MUTED};
    }}

    .ss-status-pill {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: {MINT};
        border: 1px solid {MINT}55;
        background: {MINT}11;
        border-radius: 6px;
        padding: 6px 12px;
        display: inline-block;
    }}

    div[data-testid="stFileUploader"] section {{
        background: {SURFACE};
        border: 1px dashed {BORDER};
        border-radius: 10px;
    }}

    div.stButton > button {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        letter-spacing: 0.03em;
        border-radius: 6px;
    }}
    div.stButton > button[kind="primary"] {{
        background: {CYAN};
        color: #05131a;
        border: none;
    }}

    hr {{ border-color: {BORDER}; }}
    </style>
    """, unsafe_allow_html=True)


def metric_card(label: str, value: str, sub: str = "", sub_color: str = MUTED):
    st.markdown(f"""
    <div class="ss-card">
        <div class="ss-metric-label">{label}</div>
        <div class="ss-metric-value">{value}</div>
        <div class="ss-metric-sub" style="color:{sub_color};">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def badge(text: str, kind: str = "pending") -> str:
    color = BADGE_COLORS.get(kind.lower(), MUTED)
    return f'<span class="ss-badge" style="color:{color};background:{color}18;">{text}</span>'


def flag_item(kind_label: str, timer: str, title: str, desc: str, accent: str):
    st.markdown(f"""
    <div class="ss-flag-item" style="--accent:{accent};">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="color:{accent}; font-family:'JetBrains Mono',monospace; font-size:0.72rem; font-weight:600; letter-spacing:0.04em;">{kind_label}</span>
            <span style="color:{MUTED}; font-family:'JetBrains Mono',monospace; font-size:0.72rem;">{timer}</span>
        </div>
        <div class="ss-flag-title">{title}</div>
        <div class="ss-flag-desc">{desc}</div>
    </div>
    """, unsafe_allow_html=True)


def donut_ring(pct: int, label: str, color: str = CYAN, size: int = 220):
    """CSS-only conic-gradient ring (no chart lib dependency)."""
    thickness = int(size * 0.12)
    st.markdown(f"""
    <div style="width:{size}px; height:{size}px; border-radius:50%;
                background: conic-gradient({color} {pct * 3.6}deg, {BORDER} 0deg);
                display:flex; align-items:center; justify-content:center;
                margin: 0 auto; box-shadow: 0 0 24px {color}33;">
        <div style="width:{size - thickness*2}px; height:{size - thickness*2}px; border-radius:50%;
                    background:{BG}; display:flex; flex-direction:column;
                    align-items:center; justify-content:center;">
            <div style="font-family:'Space Grotesk',sans-serif; font-size:2.4rem; font-weight:700; color:{color};">{pct}<span style="font-size:1.2rem;">%</span></div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:{MUTED}; text-transform:uppercase; letter-spacing:0.05em;">{label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def progress_row(label: str, pct: float, color: str):
    st.markdown(f"""
    <div style="margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:{TEXT}; margin-bottom:4px;">
            <span>{label}</span><span>{pct:.0f}%</span>
        </div>
        <div style="height:5px; background:{BORDER}; border-radius:3px;">
            <div style="height:5px; width:{pct}%; background:{color}; border-radius:3px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def system_status_pill():
    st.markdown('<div class="ss-status-pill">● System Status: Optimal</div>', unsafe_allow_html=True)
