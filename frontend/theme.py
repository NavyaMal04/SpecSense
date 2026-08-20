"""
frontend/theme.py
==================
Minimal visual design & accessibility system for the SpecSense UI:
Multiple curated themes (Deep Navy, Minimal OLED Black, Nordic Slate, High Contrast, Light Studio),
discrete collapsed sidebar settings, keyboard focus rings, accessible ARIA labels, card metrics,
breadcrumbs, and provenance bars.
"""

import streamlit as st

# Curated Theme Presets
THEMES = {
    "dark_ops": {
        "name": "Deep Navy (Default)",
        "bg": "#080b12",
        "surface": "#0f1520",
        "border": "#1c2636",
        "text": "#f1f5f9",
        "muted": "#94a3b8",
        "accent": "#22d3ee",
        "mint": "#34d399",
        "coral": "#fb7185",
        "amber": "#fbbf24",
    },
    "minimal_dark": {
        "name": "Minimal OLED Black",
        "bg": "#000000",
        "surface": "#0c0c0e",
        "border": "#222226",
        "text": "#ffffff",
        "muted": "#a1a1aa",
        "accent": "#f4f4f5",
        "mint": "#4ade80",
        "coral": "#f87171",
        "amber": "#facc15",
    },
    "nordic_slate": {
        "name": "Nordic Slate",
        "bg": "#121316",
        "surface": "#1a1b20",
        "border": "#2c2e36",
        "text": "#f3f4f6",
        "muted": "#9ca3af",
        "accent": "#34d399",
        "mint": "#34d399",
        "coral": "#f87171",
        "amber": "#fbbf24",
    },
    "high_contrast": {
        "name": "High Contrast (WCAG AAA)",
        "bg": "#000000",
        "surface": "#050505",
        "border": "#ffffff",
        "text": "#ffffff",
        "muted": "#cbd5e1",
        "accent": "#38bdf8",
        "mint": "#4ade80",
        "coral": "#f87171",
        "amber": "#facc15",
    },
    "minimal_light": {
        "name": "Light Studio Mode",
        "bg": "#f8fafc",
        "surface": "#ffffff",
        "border": "#e2e8f0",
        "text": "#0f172a",
        "muted": "#64748b",
        "accent": "#0284c7",
        "mint": "#10b981",
        "coral": "#ef4444",
        "amber": "#f59e0b",
    },
}

# Module-level color constants for backward compatibility across pages
MINT = "#34d399"
CORAL = "#fb7185"
AMBER = "#fbbf24"
CYAN = "#22d3ee"
MUTED = "#94a3b8"
TEXT = "#f1f5f9"
BG = "#080b12"
SURFACE = "#0f1520"
BORDER = "#1c2636"

BADGE_COLORS = {
    "extracted": MINT,
    "verified": MINT,
    "inferred": CYAN,
    "unavailable": MUTED,
    "flagged": CORAL,
    "pending": AMBER,
    "approved": MINT,
}



def get_current_theme_key():
    return st.session_state.get("ss_theme_mode", "dark_ops")


def get_theme_tokens():
    key = get_current_theme_key()
    return THEMES.get(key, THEMES["dark_ops"])


def inject_css():
    t = get_theme_tokens()
    is_hc = (get_current_theme_key() == "high_contrast")
    is_light = (get_current_theme_key() == "minimal_light")

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: {t['text']};
    }}

    .ss-sr-only {{
        position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
        overflow: hidden; clip: rect(0,0,0,0); border: 0;
    }}

    .stApp {{
        background: {t['bg']};
    }}

    section[data-testid="stSidebar"] {{
        background: {t['bg']};
        border-right: {2 if is_hc else 1}px solid {t['border']};
    }}
    section[data-testid="stSidebar"] * {{
        font-family: 'JetBrains Mono', monospace;
    }}

    h1, h2, h3 {{
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
        color: {t['text']} !important;
    }}

    /* Visible keyboard focus indicators for accessibility */
    *:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible {{
        outline: 3px solid {t['accent']} !important;
        outline-offset: 2px !important;
    }}

    .ss-eyebrow {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {t['accent'] if is_hc else t['muted']};
        font-weight: 600;
        margin-bottom: 0.2rem;
    }}

    .ss-breadcrumb {{
        display: flex; align-items: center; gap: 8px;
        font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
        color: {t['muted']}; margin-bottom: 12px;
    }}
    .ss-breadcrumb a {{
        color: {t['accent']}; text-decoration: none; font-weight: 600;
    }}
    .ss-breadcrumb a:hover {{ text-decoration: underline; }}

    .ss-card {{
        background: {t['surface']};
        border: {2 if is_hc else 1}px solid {t['border']};
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: {'0 2px 8px rgba(0,0,0,0.04)' if is_light else ('none' if is_hc else '0 4px 12px rgba(0,0,0,0.3)')};
    }}

    .ss-metric-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: {t['muted']};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
        margin-bottom: 6px;
        display: flex; align-items: center; gap: 6px;
    }}

    .ss-metric-value {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: {t['text']};
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
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 3px 10px;
        border-radius: 999px;
        border: {2 if is_hc else 1}px solid currentColor;
    }}

    .ss-status-pill {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
        color: {t['mint']};
        border: 1px solid {t['mint']};
        background: {'rgba(16,185,129,0.1)' if is_light else 'rgba(52,211,153,0.12)'};
        border-radius: 6px;
        padding: 5px 10px;
        display: inline-block;
        font-weight: 600;
    }}

    .ss-tooltip-icon {{
        display: inline-flex; align-items: center; justify-content: center;
        width: 16px; height: 16px; border-radius: 50%;
        background: {t['border']}; color: {t['text']};
        font-size: 0.68rem; font-weight: 700; cursor: help; margin-left: 4px;
    }}

    div[data-testid="stDataFrame"] {{
        border: {2 if is_hc else 1}px solid {t['border']};
        border-radius: 8px;
    }}

    div[data-testid="stFileUploader"] section {{
        background: {t['surface']};
        border: 2px dashed {t['border']};
        border-radius: 8px;
    }}

    div.stButton > button {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        letter-spacing: 0.02em;
        border-radius: 6px;
        min-height: 42px;
    }}

    div.stButton > button[kind="primary"] {{
        background: {t['accent']};
        color: {'#ffffff' if (is_light or t['accent'] in ('#f4f4f5', '#ffffff')) else '#000000'};
        font-weight: 700;
        border: none;
    }}

    hr {{ border-color: {t['border']}; }}
    </style>
    """, unsafe_allow_html=True)


def theme_selector():
    """Renders discrete theme radio controls inside a collapsed sidebar expander."""
    with st.sidebar.expander("🎨 Theme Preferences", expanded=False):
        current_key = get_current_theme_key()
        options = list(THEMES.keys())
        labels = [THEMES[k]["name"] for k in options]
        
        idx = options.index(current_key) if current_key in options else 0
        selected_label = st.radio(
            "Appearance",
            options=labels,
            index=idx,
            key="theme_radio_discrete",
        )
        
        selected_key = options[labels.index(selected_label)]
        if selected_key != current_key:
            st.session_state["ss_theme_mode"] = selected_key
            st.rerun()



def breadcrumb(items: list):
    """Renders accessible breadcrumb list with aria labels."""
    html_parts = []
    for idx, item in enumerate(items):
        if idx == len(items) - 1:
            html_parts.append(f'<span aria-current="page" style="font-weight:700;">{item["label"]}</span>')
        else:
            html_parts.append(f'<span>{item["label"]}</span> <span>/</span>')

    st.markdown(f'''
    <nav aria-label="Breadcrumb" class="ss-breadcrumb">
        {" ".join(html_parts)}
    </nav>
    ''', unsafe_allow_html=True)


def metric_card(label: str, value: str, sub: str = "", sub_color: str = None, help_text: str = None):
    t = get_theme_tokens()
    color_used = sub_color or t["muted"]
    help_html = f'<span class="ss-tooltip-icon" title="{help_text}">?</span>' if help_text else ""
    st.markdown(f"""
    <div class="ss-card" role="region" aria-label="{label} metric">
        <div class="ss-metric-label">{label}{help_html}</div>
        <div class="ss-metric-value">{value}</div>
        <div class="ss-metric-sub" style="color:{color_used};">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def badge(text: str, kind: str = "pending") -> str:
    t = get_theme_tokens()
    is_hc = (get_current_theme_key() == "high_contrast")
    
    badge_colors = {
        "extracted": t["mint"],
        "verified": t["mint"],
        "inferred": t["accent"],
        "unavailable": t["muted"],
        "flagged": t["coral"],
        "pending": t["amber"],
        "approved": t["mint"],
    }
    color = badge_colors.get(kind.lower(), t["muted"])
    bg = "rgba(255,255,255,0.15)" if is_hc else f"{color}20"
    return f'<span class="ss-badge" role="status" style="color:{color};background:{bg};">{text}</span>'


def provenance_bar(extracted_pct: float, inferred_pct: float, unavailable_pct: float):
    """Renders an accessible 3-part provenance bar breakdown."""
    t = get_theme_tokens()
    st.markdown(f"""
    <div role="img" aria-label="Data Provenance Ratio: {extracted_pct:.0f}% Extracted, {inferred_pct:.0f}% Inferred, {unavailable_pct:.0f}% Missing" style="margin: 10px 0;">
        <div style="display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:0.78rem; margin-bottom:4px;">
            <span><span style="color:{t['mint']};">●</span> Extracted: {extracted_pct:.0f}%</span>
            <span><span style="color:{t['accent']};">●</span> Inferred: {inferred_pct:.0f}%</span>
            <span><span style="color:{t['muted']};">●</span> Unavailable: {unavailable_pct:.0f}%</span>
        </div>
        <div style="height:8px; background:{t['border']}; border-radius:4px; display:flex; overflow:hidden;">
            <div style="width:{extracted_pct}%; background:{t['mint']};" title="Extracted: {extracted_pct:.0f}%"></div>
            <div style="width:{inferred_pct}%; background:{t['accent']};" title="Inferred: {inferred_pct:.0f}%"></div>
            <div style="width:{unavailable_pct}%; background:{t['muted']};" title="Unavailable: {unavailable_pct:.0f}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def donut_ring(pct: int, label: str, color: str = None, size: int = 180):
    t = get_theme_tokens()
    accent_color = color or t["accent"]
    thickness = int(size * 0.12)
    st.markdown(f"""
    <div role="img" aria-label="{label}: {pct}%" style="width:{size}px; height:{size}px; border-radius:50%;
                background: conic-gradient({accent_color} {pct * 3.6}deg, {t['border']} 0deg);
                display:flex; align-items:center; justify-content:center;
                margin: 0 auto; box-shadow: 0 0 16px {accent_color}22;">
        <div style="width:{size - thickness*2}px; height:{size - thickness*2}px; border-radius:50%;
                    background:{t['bg']}; display:flex; flex-direction:column; align-items:center; justify-content:center;">
            <div style="font-family:'Space Grotesk',sans-serif; font-size:1.9rem; font-weight:700; color:{accent_color};">{pct}<span style="font-size:1.1rem;">%</span></div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.68rem; color:{t['muted']}; text-transform:uppercase; letter-spacing:0.05em; font-weight:600;">{label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def progress_row(label: str, pct: float, color: str):
    t = get_theme_tokens()
    st.markdown(f"""
    <div style="margin-bottom:8px;">
        <div style="display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:0.78rem; color:{t['text']}; margin-bottom:4px; font-weight:600;">
            <span>{label}</span><span>{pct:.0f}%</span>
        </div>
        <div style="height:5px; background:{t['border']}; border-radius:3px; overflow:hidden;">
            <div style="height:5px; width:{pct}%; background:{color}; border-radius:3px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def system_status_pill(text: str = "System Status: Optimal"):
    st.markdown(f'<div class="ss-status-pill" role="status">● {text}</div>', unsafe_allow_html=True)


def sidebar_header():
    st.markdown("### ◈ SpecSense")
    st.caption("PRODUCT INTELLIGENCE PIPELINE")
    system_status_pill()
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    theme_selector()
