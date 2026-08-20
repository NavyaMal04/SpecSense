import streamlit as st

from theme import (
    inject_css, badge, sidebar_header, breadcrumb,
    MINT, CORAL, AMBER, CYAN, MUTED
)

st.set_page_config(page_title="SpecSense — Website User Manual", layout="wide", page_icon="📖")
inject_css()

with st.sidebar:
    sidebar_header()

breadcrumb([
    {"label": "SpecSense", "url": "/"},
    {"label": "Website User Manual"}
])

st.markdown('<div class="ss-eyebrow">User Guide</div>', unsafe_allow_html=True)
st.title("Website User Manual")
st.caption("Everything you need to know to browse, inspect, edit, compare, and export catalog products.")

tab_nav, tab_browse, tab_detail, tab_compare_export, tab_tips = st.tabs([
    "🧭 Site Overview",
    "🔎 Search & Bulk Actions",
    "🧾 Reviewing & Editing Specs",
    "⚔ Comparison & Export",
    "💡 User Tips & Support",
])

# === TAB 1: SITE OVERVIEW ===
with tab_nav:
    st.markdown('<div class="ss-metric-label">Welcome to SpecSense</div>', unsafe_allow_html=True)
    st.markdown("""
    **SpecSense** is your central product intelligence portal. It automatically organizes messy product datasheets into clean, formatted product catalogs ready for online commerce.
    """)

    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown("### 🗺 Website Navigation Guide")
    st.markdown("""
    Use the **navigation menu on the left sidebar** to switch between different sections of the website:

    - **◈ Dashboard**: View total product counts, average catalog completeness, and review status totals.
    - **🔎 Product Browser**: Search, filter, sort, and manage all product records in your catalog.
    - **🧾 Product Detail**: Inspect complete technical specs, edit product fields, view source citations, and preview marketing descriptions.
    - **⚔ Compare Products**: Select 2 or 3 products and compare their specifications side-by-side in a single table.
    - **⚙ Run Enrichment**: Run live enrichment on a single part number to pull specs from web sources.
    - **📤 Export Delivery Data**: Download your catalog as a formatted CSV spreadsheet or JSON data package.
    - **📖 User Manual**: This step-by-step website guide!
    """)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown("### 🎨 Customizing Your Display Theme")
    st.markdown("""
    To change how the website looks, open **🎨 Theme Preferences** in the bottom left sidebar:
    - **Deep Navy (Default)**: Dark navy interface with bright telemetry accents.
    - **Minimal OLED Black**: Sleek pure dark background with high-contrast text.
    - **Nordic Slate**: Soft slate gray theme with emerald green highlights.
    - **High Contrast (WCAG AAA)**: Maximum contrast theme designed for accessibility.
    - **Light Studio Mode**: Crisp white theme for bright workspace environments.
    """)
    st.markdown('</div>', unsafe_allow_html=True)

# === TAB 2: SEARCH & BULK ACTIONS ===
with tab_browse:
    st.markdown('<div class="ss-metric-label">Product Browser Guide</div>', unsafe_allow_html=True)
    
    st.markdown("""
    The **Product Browser** is where you view, search, and manage all catalog products.
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="ss-card">', unsafe_allow_html=True)
        st.markdown("#### 🔍 Finding Products")
        st.markdown("""
        1. **Search Bar**: Type any **Part Number (MPN)**, **Manufacturer name** (e.g. *Wera*, *Milwaukee*, *DEWALT*), or **Brand name**.
        2. **Filter by Status**:
           - **Pending**: Products waiting for human verification.
           - **Approved**: Verified products ready for export.
           - **Flagged**: Products marked for review due to missing or conflicting data.
        3. **Sorting**: Sort catalog rows by **Completeness %**, **MPN (A-Z)**, or **Manufacturer (A-Z)**.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="ss-card">', unsafe_allow_html=True)
        st.markdown("#### ⚡ Bulk Management Toolbar")
        st.markdown("""
        Instead of editing products one by one, use the checkboxes on the left of each row:

        - **✓ Bulk Approve**: Select multiple products and approve them all at once.
        - **⚠ Bulk Flag**: Select multiple products to flag them for team review.
        - **↺ Bulk Reset**: Revert selected products back to `Pending` status.
        - **⚔ Compare (2-3)**: Check 2 or 3 products to compare them side-by-side.
        - **⬇ Export Selected**: Download a JSON backup file containing only checked products.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

# === TAB 3: REVIEWING & EDITING SPECS ===
with tab_detail:
    st.markdown('<div class="ss-metric-label">Product Detail & Editor Guide</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Clicking **Inspect →** on any product opens its full **Product Detail** page.
    """)

    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown("#### 🏷 Understanding Field Badges & Provenance")
    st.markdown(f"""
    Every specification field displays a status badge indicating where the data came from:

    <br>

    - {badge('EXTRACTED', 'extracted')} **Extracted (Green)**: Directly found on official manufacturer spec sheets or supplier websites.
    - {badge('INFERRED', 'inferred')} **Inferred (Cyan)**: Intelligently predicted based on similar products in the catalog.
    - {badge('FLAGGED', 'flagged')} **Flagged (Red)**: Marked for review because value had low confidence or required verification.
    - {badge('UNAVAILABLE', 'unavailable')} **Unavailable (Gray)**: Specification not found in source documentation.
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.markdown("#### ✏ How to Edit & Verify Product Data")
    st.markdown("""
    1. **Edit Specifications**: Double-click any cell in the specification tables (e.g. Dimensions, Pricing, Model, Descriptions) to update values.
    2. **Save Changes**: Click **Save Section** under the table to permanently update the product on disk.
    3. **Review Tabs**:
       - **📋 Specification Editor**: Edit all catalog fields, features, and physical attributes.
       - **🔍 Provenance & Citations**: View source website links and text snippets for verified specs.
       - **✨ AI Grounded Copy Preview**: View ready-to-use e-commerce titles, short descriptions, and bullet points.
       - **📄 Raw JSON View**: View or download the raw product file.
    4. **Change Status**: Click **✓ Approve Record** when finished, or **⚠ Flag for Review** if errors exist.
    """)
    st.markdown('</div>', unsafe_allow_html=True)

# === TAB 4: COMPARISON & EXPORT ===
with tab_compare_export:
    st.markdown('<div class="ss-metric-label">Product Comparison & Export Guide</div>', unsafe_allow_html=True)

    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown('<div class="ss-card">', unsafe_allow_html=True)
        st.markdown("#### ⚔ Comparing Products Side-by-Side")
        st.markdown("""
        1. Go to **Compare Products** in the left sidebar (or select 2-3 products in the Product Browser).
        2. Use the dropdown to choose **2 or 3 products**.
        3. Scroll down to view side-by-side comparison matrices for:
           - **Overview & Completeness %**
           - **Identity & Part Numbers**
           - **Dimensions & Weights**
           - **Pricing & Packaging**
           - **Captured Attributes**
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="ss-card">', unsafe_allow_html=True)
        st.markdown("#### 📤 Exporting Catalog Files")
        st.markdown("""
        1. Navigate to **Export Delivery Data** in the sidebar.
        2. Choose your filter: check **Only include approved records** if you only want ready products.
        3. Select your export format:
           - **Unilog Delivery CSV (252 Columns)**: Formatted CSV spreadsheet ready for website import.
           - **Full Catalog JSON Package**: Complete JSON data file containing all attributes and descriptions.
        4. Click **▶ Build File** and press **⬇ Download**.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

# === TAB 5: TIPS & SUPPORT ===
with tab_tips:
    st.markdown('<div class="ss-metric-label">User Tips & FAQs</div>', unsafe_allow_html=True)

    st.markdown("**💡 Quick User Tips:**")
    st.markdown("""
    - **Navigating Products Quickly**: In Product Detail, use the **← Previous Product** and **Next Product →** buttons at the top of the page to move sequentially through products without going back to the browser.
    - **Hovering for Tooltips**: Look for the small **?** icons next to metric titles to read quick explanations of what each metric means.
    - **Copying Marketing Copy**: In Product Detail under **✨ AI Grounded Copy Preview**, hover over description boxes to copy text with 1 click.
    """)

    st.markdown("---")
    st.markdown("**❓ Frequently Asked Questions:**")
    st.markdown("""
    - **What does Completeness % mean?**
      It shows the percentage of schema fields populated for a product. Higher percentages mean more detailed catalog entries.
    - **How do I know if a product is ready for delivery?**
      Look for the **Approved** green status badge. You can filter the export page to download only approved records.
    - **Can I undo an approval or flag?**
      Yes! At any time, click **↺ Reset to Pending** in the Product Detail header or use **Bulk Reset** in the Product Browser.
    """)
