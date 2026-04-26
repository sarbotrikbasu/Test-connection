from __future__ import annotations
from typing import Optional, List

import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ──────────────────────────────────────────────────────────────
# Config & Constants
# ──────────────────────────────────────────────────────────────

API_BASE = "https://test-connection-six.vercel.app"
PERIOD_KEYS   = ["1d", "1w", "1m", "3m", "6m"]
PERIOD_LABELS = ["1 Day", "1 Week", "1 Month", "3 Months", "6 Months"]

st.set_page_config(
    page_title="MF Portfolio Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────
# Premium CSS
# ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #0b0f19; }

/* Header */
.hero {
    background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0d1f3c 100%);
    border-bottom: 1px solid #1e293b;
    padding: 2rem 0 1.5rem;
    text-align: center;
    margin-bottom: 2rem;
}
.hero h1 {
    font-size: 2.6rem; font-weight: 700;
    background: linear-gradient(90deg, #00d4aa, #3b82f6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0;
}
.hero p { color: #94a3b8; font-size: 1rem; margin-top: 0.4rem; }

/* Section labels */
.section-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
    color: #00d4aa; text-transform: uppercase; margin-bottom: 0.6rem;
}

/* Fund search result card */
.fund-card {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.2s;
}
.fund-card:hover { border-color: #00d4aa44; }
.fund-name { font-size: 0.95rem; font-weight: 600; color: #e2e8f0; }
.fund-meta { font-size: 0.78rem; color: #64748b; margin-top: 0.2rem; }
.fund-code-badge {
    display: inline-block;
    background: #0d1f3c; color: #3b82f6;
    border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 2px 8px; font-size: 0.72rem; font-weight: 600;
    margin-top: 0.4rem;
}

/* Portfolio item */
.pf-item {
    background: #111827; border: 1px solid #1e293b;
    border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 0.5rem;
}
.pf-item-name { font-size: 0.88rem; font-weight: 600; color: #e2e8f0; }
.pf-item-meta { font-size: 0.75rem; color: #64748b; }
.pf-amount { font-size: 0.9rem; font-weight: 700; color: #00d4aa; }

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #111827, #0d1f3c);
    border: 1px solid #1e293b; border-radius: 14px;
    padding: 1.2rem 1.4rem; text-align: center;
}
.metric-label { font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }
.metric-value { font-size: 1.8rem; font-weight: 700; color: #e2e8f0; margin: 0.2rem 0; }
.metric-sub { font-size: 0.8rem; color: #94a3b8; }

/* Perf card */
.perf-card {
    background: #111827; border: 1px solid #1e293b;
    border-radius: 14px; padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
}
.perf-fund-name { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.6rem; }
.perf-nav { font-size: 1.4rem; font-weight: 700; color: #00d4aa; }
.perf-date { font-size: 0.72rem; color: #64748b; }
.change-pos { color: #22c55e; font-weight: 600; }
.change-neg { color: #ef4444; font-weight: 600; }
.change-neutral { color: #94a3b8; font-weight: 600; }

/* Divider */
.custom-divider { border: none; border-top: 1px solid #1e293b; margin: 1.5rem 0; }

/* Empty state */
.empty-state {
    text-align: center; padding: 2.5rem 1rem;
    color: #475569; font-size: 0.9rem;
}
.empty-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }

/* Analyse button override */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(90deg, #00d4aa, #3b82f6) !important;
    border: none !important; color: #fff !important;
    font-weight: 600 !important; border-radius: 10px !important;
    padding: 0.6rem 2rem !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Hero Header
# ──────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <h1>📈 MF Portfolio Analyzer</h1>
  <p>Search Indian Mutual Funds · Build your portfolio · Visualise performance</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Session State Init
# ──────────────────────────────────────────────────────────────

if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = []

if "search_results" not in st.session_state:
    st.session_state["search_results"] = []

if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""

if "pending_add" not in st.session_state:
    st.session_state["pending_add"] = None

if "perf_data" not in st.session_state:
    st.session_state["perf_data"] = []

if "show_dashboard" not in st.session_state:
    st.session_state["show_dashboard"] = False

if "benchmark_data" not in st.session_state:
    st.session_state["benchmark_data"] = []

# ──────────────────────────────────────────────────────────────
# API Helpers
# ──────────────────────────────────────────────────────────────

def search_funds(query: str) -> List[dict]:
    try:
        r = requests.get(f"{API_BASE}/search", params={"q": query}, timeout=20)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Search failed: {e}")
        return []


def get_fund_performance(scheme_code: int) -> Optional[dict]:
    try:
        r = requests.get(f"{API_BASE}/mf/{scheme_code}", timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Could not fetch data for scheme {scheme_code}: {e}")
        return None


def get_benchmarks() -> List[dict]:
    try:
        r = requests.get(f"{API_BASE}/benchmarks", timeout=60)
        r.raise_for_status()
        return r.json().get("benchmarks", [])
    except Exception as e:
        st.warning(f"⚠️ Benchmark data unavailable: {e}")
        return []

# ──────────────────────────────────────────────────────────────
# Portfolio Helpers
# ──────────────────────────────────────────────────────────────

def already_in_portfolio(scheme_code: int) -> bool:
    return any(f["scheme_code"] == scheme_code for f in st.session_state.portfolio)


def add_to_portfolio(fund: dict, amount: float):
    st.session_state.portfolio.append({
        "scheme_code": fund["scheme_code"],
        "scheme_name": fund["scheme_name"],
        "fund_house":  fund["fund_house"],
        "scheme_type": fund["scheme_type"],
        "invested":    amount,
    })
    st.session_state.pending_add = None
    st.session_state.show_dashboard = False
    st.session_state.perf_data = []


def remove_from_portfolio(scheme_code: int):
    st.session_state.portfolio = [
        f for f in st.session_state.portfolio if f["scheme_code"] != scheme_code
    ]
    st.session_state.show_dashboard = False
    st.session_state.perf_data = []

# ──────────────────────────────────────────────────────────────
# PHASE 1 — Two-column layout
# ──────────────────────────────────────────────────────────────

col_search, col_portfolio = st.columns([3, 2], gap="large")

# ── LEFT: Search ──────────────────────────────────────────────
with col_search:
    st.markdown('<div class="section-label">🔍 Search Mutual Funds</div>', unsafe_allow_html=True)

    search_col1, search_col2 = st.columns([5, 1])
    with search_col1:
        query = st.text_input(
            "Fund name",
            placeholder="e.g. Mirae Asset, HDFC, SBI, Axis",
            label_visibility="collapsed",
            key="search_input",
        )
    with search_col2:
        do_search = st.button("Search", use_container_width=True)

    if do_search and query.strip():
        with st.spinner("Searching..."):
            st.session_state.search_results = search_funds(query.strip())
            st.session_state.search_query = query.strip()
            st.session_state.pending_add = None

    results = st.session_state.search_results

    if results:
        st.markdown(
            f'<div class="section-label" style="margin-top:1rem">'
            f'Found {len(results)} result(s) for "{st.session_state.search_query}"</div>',
            unsafe_allow_html=True,
        )

        for fund in results:
            code = fund["scheme_code"]
            name = fund["scheme_name"]
            house = fund.get("fund_house", "—")
            ftype = fund.get("scheme_type", "")
            cat   = fund.get("scheme_category", "")

            with st.container():
                st.markdown(f"""
                <div class="fund-card">
                  <div class="fund-name">{name}</div>
                  <div class="fund-meta">{house} · {ftype} · {cat}</div>
                  <span class="fund-code-badge">Code: {code}</span>
                </div>
                """, unsafe_allow_html=True)

                if already_in_portfolio(code):
                    st.caption("✅ Already in portfolio")
                elif (
                    st.session_state.pending_add is not None
                    and st.session_state.pending_add["scheme_code"] == code
                ):
                    # Amount entry inline
                    amt_col, btn_col = st.columns([3, 1])
                    with amt_col:
                        amt = st.number_input(
                            "Amount Invested (₹)",
                            min_value=100.0,
                            step=1000.0,
                            format="%.0f",
                            key=f"amt_{code}",
                        )
                    with btn_col:
                        st.write("")
                        if st.button("Confirm ✓", key=f"confirm_{code}", type="primary"):
                            add_to_portfolio(fund, amt)
                            st.rerun()
                    if st.button("Cancel", key=f"cancel_{code}"):
                        st.session_state.pending_add = None
                        st.rerun()
                else:
                    if st.button(f"＋ Add to Portfolio", key=f"add_{code}"):
                        st.session_state.pending_add = fund
                        st.rerun()

    elif st.session_state.search_query:
        st.markdown(
            '<div class="empty-state"><div class="empty-icon">🔎</div>'
            'No matching funds found. Try a different keyword.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="empty-state"><div class="empty-icon">🏦</div>'
            'Search for a fund by name to get started.</div>',
            unsafe_allow_html=True,
        )

# ── RIGHT: Portfolio ──────────────────────────────────────────
with col_portfolio:
    portfolio = st.session_state.portfolio
    count = len(portfolio)
    st.markdown(
        f'<div class="section-label">📁 My Portfolio '
        f'<span style="color:#64748b">({count} fund{"s" if count != 1 else ""})</span></div>',
        unsafe_allow_html=True,
    )

    if not portfolio:
        st.markdown(
            '<div class="empty-state"><div class="empty-icon">📂</div>'
            'Your portfolio is empty.<br>Search and add funds to begin.</div>',
            unsafe_allow_html=True,
        )
    else:
        for fund in portfolio:
            code  = fund["scheme_code"]
            name  = fund["scheme_name"]
            house = fund["fund_house"]
            amt   = fund["invested"]

            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"""
                <div class="pf-item">
                  <div class="pf-item-name">{name[:55]}{'…' if len(name)>55 else ''}</div>
                  <div class="pf-item-meta">{house} · Code: {code}</div>
                  <div class="pf-amount">₹{amt:,.0f} invested</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.write("")
                st.write("")
                if st.button("🗑️", key=f"rm_{code}", help="Remove from portfolio"):
                    remove_from_portfolio(code)
                    st.rerun()

        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

        total_invested = sum(f["invested"] for f in portfolio)
        st.markdown(
            f'<div style="text-align:right; color:#94a3b8; font-size:0.85rem;">'
            f'Total Invested: <span style="color:#00d4aa; font-weight:700; font-size:1rem;">'
            f'₹{total_invested:,.0f}</span></div>',
            unsafe_allow_html=True,
        )
        st.write("")

        if st.button("🔍 Analyse Portfolio", type="primary", use_container_width=True):
            with st.spinner("Fetching live NAV data for all funds…"):
                results_data = []
                for fund in portfolio:
                    perf = get_fund_performance(fund["scheme_code"])
                    if perf:
                        perf["invested"] = fund["invested"]
                        results_data.append(perf)
            with st.spinner("Fetching benchmark data (Nifty 50, S&P 500, Gold, Silver)…"):
                bm_data = get_benchmarks()
            st.session_state.perf_data = results_data
            st.session_state.benchmark_data = bm_data
            st.session_state.show_dashboard = True
            st.rerun()

# ──────────────────────────────────────────────────────────────
# PHASE 2 — Performance Dashboard
# ──────────────────────────────────────────────────────────────

if st.session_state.show_dashboard and st.session_state.perf_data:
    perf_data = st.session_state.perf_data
    bm_data   = st.session_state.get("benchmark_data", [])

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-label" style="font-size:0.9rem; margin-bottom:1rem;">'
        '📊 Portfolio Performance Dashboard</div>',
        unsafe_allow_html=True,
    )

    # ── Helpers ──────────────────────────────────────────────
    import re as _re

    def rgb_to_rgba(color: str, alpha: float = 0.2) -> str:
        """Convert plotly's 'rgb(r,g,b)' or '#rrggbb' to 'rgba(r,g,b,a)'."""
        m = _re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color)
        if m:
            return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha})"
        h = color.lstrip('#')
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha})"
        return color  # fallback: return unchanged

    def get_pct(fund_data: dict, period: str) -> Optional[float]:
        key = f"change_{period}"
        ch = fund_data.get(key, {})
        return ch.get("change_pct") if ch else None

    def get_hist_nav(fund_data: dict, period: str) -> Optional[float]:
        """Historical NAV for a given period from the fund performance dict."""
        key = f"change_{period}"
        ch = fund_data.get(key, {})
        return ch.get("nav") if ch else None

    def fmt_pct(v: Optional[float]) -> str:
        if v is None:
            return "N/A"
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.2f}%"

    def color_pct(v: Optional[float]) -> str:
        if v is None:
            return "change-neutral"
        return "change-pos" if v >= 0 else "change-neg"

    # ── Portfolio NAV-sum % changes ──────────────────────────
    # Total portfolio value = sum of 1 unit NAV of each fund
    total_nav_current = sum(fd.get("current_nav", 0) for fd in perf_data)

    def portfolio_pct(period: str) -> Optional[float]:
        hist_navs = [get_hist_nav(fd, period) for fd in perf_data]
        if any(h is None for h in hist_navs):
            return None
        total_hist = sum(hist_navs)
        if total_hist == 0:
            return None
        return round(((total_nav_current - total_hist) / total_hist) * 100, 4)

    pf_changes = {pk: portfolio_pct(pk) for pk in PERIOD_KEYS}

    # ── Portfolio Overview Card ──────────────────────────────
    pf_changes_html = ""
    for pk, pl in zip(PERIOD_KEYS, PERIOD_LABELS):
        v   = pf_changes[pk]
        cls = color_pct(v)
        pf_changes_html += (
            f'<div style="text-align:center;padding:0.5rem 0.8rem;'
            f'background:#0b0f19;border-radius:8px;min-width:90px">'
            f'<div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.08em">{pl}</div>'
            f'<div class="{cls}" style="font-size:0.95rem;font-weight:700;margin-top:0.2rem">{fmt_pct(v)}</div>'
            f'</div>'
        )

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1f3c,#111827);border:1px solid #3b82f6;
         border-radius:16px;padding:1.4rem 1.6rem;margin-bottom:1.2rem">
      <div style="font-size:0.75rem;color:#3b82f6;text-transform:uppercase;
           letter-spacing:0.1em;font-weight:600;margin-bottom:0.6rem">🗂 Overall Portfolio (1 unit each)</div>
      <div style="display:flex;align-items:baseline;gap:0.8rem;margin-bottom:0.9rem">
        <span style="font-size:1.5rem;font-weight:700;color:#00d4aa">₹{total_nav_current:,.4f}</span>
        <span style="font-size:0.75rem;color:#64748b">combined NAV (1 unit per fund)</span>
      </div>
      <div style="display:flex;gap:0.6rem;flex-wrap:wrap">{pf_changes_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 2a: Summary KPI row ──────────────────────────────────
    total_inv = sum(f["invested"] for f in st.session_state.portfolio)
    pct_1m_vals = [(f["scheme_name"], get_pct(f, "1m")) for f in perf_data if get_pct(f, "1m") is not None]
    best_fund = max(pct_1m_vals, key=lambda x: x[1], default=("—", None))
    worst_fund = min(pct_1m_vals, key=lambda x: x[1], default=("—", None))

    # Portfolio 1M vs Nifty 50 1M delta
    pf_1m = pf_changes.get("1m")
    nifty_1m = next((b.get("change_1m") for b in bm_data if b.get("symbol") == "^NSEI"), None)
    vs_nifty_str = "N/A"
    if pf_1m is not None and nifty_1m is not None:
        delta = round(pf_1m - nifty_1m, 2)
        sign = "+" if delta >= 0 else ""
        vs_nifty_str = f"{sign}{delta:.2f}%"

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    kpis = [
        ("Total Invested",      f"₹{total_inv:,.0f}",            "across all funds"),
        ("Funds Tracked",       str(len(perf_data)),              "in portfolio"),
        ("Portfolio 1M Return", fmt_pct(pf_1m),                  "combined NAV basis"),
        ("vs Nifty 50 (1M)",   vs_nifty_str,                    "portfolio alpha"),
        ("Best 1M (Fund)",      fmt_pct(best_fund[1]),           best_fund[0][:25] if best_fund[0] != "—" else "—"),
        ("Worst 1M (Fund)",     fmt_pct(worst_fund[1]),          worst_fund[0][:25] if worst_fund[0] != "—" else "—"),
    ]
    for col, (label, value, sub) in zip([k1, k2, k3, k4, k5, k6], kpis):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{label}</div>
              <div class="metric-value" style="font-size:1.4rem">{value}</div>
              <div class="metric-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    # ── 2b: Individual fund performance cards ────────────────
    st.markdown('<div class="section-label">Fund Snapshots</div>', unsafe_allow_html=True)

    for fd in perf_data:
        short_name = fd["scheme_name"][:65] + ("…" if len(fd["scheme_name"]) > 65 else "")
        nav = fd.get("current_nav", 0)
        date = fd.get("current_date", "")

        changes_html = ""
        for pk, pl in zip(PERIOD_KEYS, PERIOD_LABELS):
            v = get_pct(fd, pk)
            cls = color_pct(v)
            changes_html += (
                f'<div style="text-align:center; padding: 0.5rem 0.8rem; '
                f'background:#0b0f19; border-radius:8px; min-width:90px">'
                f'<div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;'
                f'letter-spacing:0.08em">{pl}</div>'
                f'<div class="{cls}" style="font-size:0.9rem;margin-top:0.2rem">{fmt_pct(v)}</div>'
                f'</div>'
            )

        st.markdown(f"""
        <div class="perf-card">
          <div class="perf-fund-name">{short_name}</div>
          <div style="display:flex; align-items:baseline; gap:0.8rem; margin-bottom:0.8rem">
            <span class="perf-nav">₹{nav:,.4f}</span>
            <span class="perf-date">NAV as of {date}</span>
          </div>
          <div style="display:flex; gap:0.6rem; flex-wrap:wrap">{changes_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 2b-bm: Benchmark Performance Cards ───────────────────
    if bm_data:
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">🌐 Benchmark Performance</div>', unsafe_allow_html=True)
        bm_cols = st.columns(len(bm_data))
        BM_PERIOD_MAP = {
            "1d": ("1 Day",    "change_1d"),
            "1w": ("1 Week",   "change_1w"),
            "1m": ("1 Month",  "change_1m"),
            "3m": ("3 Months", "change_3m"),
            "6m": ("6 Months", "change_6m"),
        }
        BM_ICONS = {"^NSEI": "🇮🇳", "^GSPC": "🇺🇸", "GC=F": "🥇", "SI=F": "🥈"}
        for col, bm in zip(bm_cols, bm_data):
            with col:
                icon = BM_ICONS.get(bm["symbol"], "📊")
                price = bm.get("current_price")
                currency = bm.get("currency") or ""
                price_str = f"{price:,.4f} {currency}".strip() if price else "N/A"
                rows_html = ""
                for pk, (pl, bk) in BM_PERIOD_MAP.items():
                    v = bm.get(bk)
                    cls = color_pct(v)
                    rows_html += (
                        f'<div style="display:flex;justify-content:space-between;'
                        f'padding:0.25rem 0;border-bottom:1px solid #1e293b">'
                        f'<span style="font-size:0.72rem;color:#64748b">{pl}</span>'
                        f'<span class="{cls}" style="font-size:0.78rem">{fmt_pct(v)}</span></div>'
                    )
                st.markdown(f"""
                <div style="background:#111827;border:1px solid #1e293b;border-radius:14px;
                     padding:1rem 1.1rem;margin-bottom:0.5rem">
                  <div style="font-size:1.1rem;margin-bottom:0.2rem">{icon} <span style="font-weight:700;
                       color:#e2e8f0;font-size:0.95rem">{bm['name']}</span></div>
                  <div style="font-size:0.72rem;color:#64748b;margin-bottom:0.6rem">{bm['symbol']}</div>
                  <div style="font-size:1.2rem;font-weight:700;color:#00d4aa;margin-bottom:0.7rem">{price_str}</div>
                  {rows_html}
                </div>
                """, unsafe_allow_html=True)

    else:
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.info("🌐 Benchmark data could not be loaded. The backend may need a moment — try clicking Analyse Portfolio again.")

    # ── 2c: Comparative Bar Chart (funds) ─────────────────────
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Comparative % Change by Period</div>', unsafe_allow_html=True)

    bar_fig = go.Figure()
    colors = px.colors.qualitative.Set2

    # Portfolio aggregate trace
    pf_y = [pf_changes.get(pk) for pk in PERIOD_KEYS]
    bar_fig.add_trace(go.Bar(
        name="📁 Portfolio (total NAV)",
        x=PERIOD_LABELS,
        y=pf_y,
        marker_color="#00d4aa",
        text=[fmt_pct(v) for v in pf_y],
        textposition="outside",
        textfont=dict(size=10),
    ))

    for i, fd in enumerate(perf_data):
        name_short = fd["scheme_name"].split("(")[0].strip()[:40]
        y_vals = [get_pct(fd, pk) for pk in PERIOD_KEYS]
        bar_fig.add_trace(go.Bar(
            name=name_short,
            x=PERIOD_LABELS,
            y=y_vals,
            marker_color=colors[i % len(colors)],
            text=[fmt_pct(v) for v in y_vals],
            textposition="outside",
            textfont=dict(size=10),
        ))

    bar_fig.update_layout(
        barmode="group",
        plot_bgcolor="#111827",
        paper_bgcolor="#111827",
        font=dict(color="#94a3b8", family="Inter"),
        legend=dict(bgcolor="#0b0f19", bordercolor="#1e293b", borderwidth=1),
        xaxis=dict(gridcolor="#1e293b"),
        yaxis=dict(gridcolor="#1e293b", title="% Change", zeroline=True,
                   zerolinecolor="#334155", zerolinewidth=1),
        margin=dict(t=30, b=20),
        height=420,
    )
    st.plotly_chart(bar_fig, use_container_width=True)

    # ── 2c-bm: Benchmark vs Portfolio Bar Chart ────────────────
    if bm_data:
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">📊 Portfolio vs Benchmarks</div>', unsafe_allow_html=True)
        bm_bar = go.Figure()
        BM_COLORS = {"^NSEI": "#f59e0b", "^GSPC": "#3b82f6", "GC=F": "#fbbf24", "SI=F": "#94a3b8"}
        BM_KEY_MAP = {"1d": "change_1d", "1w": "change_1w", "1m": "change_1m", "3m": "change_3m", "6m": "change_6m"}

        # Portfolio aggregate
        bm_bar.add_trace(go.Bar(
            name="📁 Portfolio",
            x=PERIOD_LABELS,
            y=[pf_changes.get(pk) for pk in PERIOD_KEYS],
            marker_color="#00d4aa",
            text=[fmt_pct(pf_changes.get(pk)) for pk in PERIOD_KEYS],
            textposition="outside", textfont=dict(size=10),
        ))
        for bm in bm_data:
            y_bm = [bm.get(BM_KEY_MAP[pk]) for pk in PERIOD_KEYS]
            bm_bar.add_trace(go.Bar(
                name=bm["name"],
                x=PERIOD_LABELS,
                y=y_bm,
                marker_color=BM_COLORS.get(bm["symbol"], "#64748b"),
                text=[fmt_pct(v) for v in y_bm],
                textposition="outside", textfont=dict(size=10),
            ))
        bm_bar.update_layout(
            barmode="group",
            plot_bgcolor="#111827", paper_bgcolor="#111827",
            font=dict(color="#94a3b8", family="Inter"),
            legend=dict(bgcolor="#0b0f19", bordercolor="#1e293b", borderwidth=1),
            xaxis=dict(gridcolor="#1e293b"),
            yaxis=dict(gridcolor="#1e293b", title="% Change", zeroline=True,
                       zerolinecolor="#334155", zerolinewidth=1),
            margin=dict(t=30, b=20),
            height=400,
        )
        st.plotly_chart(bm_bar, use_container_width=True)

    # ── 2d: Radar Chart ───────────────────────────────────────
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Radar — Performance Shape Across Periods</div>', unsafe_allow_html=True)

    radar_fig = go.Figure()
    theta_labels = PERIOD_LABELS + [PERIOD_LABELS[0]]  # close the polygon

    for i, fd in enumerate(perf_data):
        name_short = fd["scheme_name"].split("(")[0].strip()[:40]
        raw = [get_pct(fd, pk) or 0 for pk in PERIOD_KEYS]
        r_vals = raw + [raw[0]]
        radar_fig.add_trace(go.Scatterpolar(
            r=r_vals,
            theta=theta_labels,
            fill="toself",
            fillcolor=rgb_to_rgba(colors[i % len(colors)], 0.2),
            line=dict(color=colors[i % len(colors)], width=2),
            name=name_short,
        ))

    radar_fig.update_layout(
        polar=dict(
            bgcolor="#0b0f19",
            radialaxis=dict(gridcolor="#1e293b", linecolor="#1e293b", tickfont=dict(color="#64748b")),
            angularaxis=dict(gridcolor="#1e293b", linecolor="#1e293b", tickfont=dict(color="#94a3b8")),
        ),
        paper_bgcolor="#111827",
        font=dict(color="#94a3b8", family="Inter"),
        legend=dict(bgcolor="#0b0f19", bordercolor="#1e293b", borderwidth=1),
        margin=dict(t=30, b=20),
        height=420,
    )
    st.plotly_chart(radar_fig, use_container_width=True)

    # ── 2e: Portfolio Allocation Pie ──────────────────────────
    col_pie, col_table = st.columns([1, 1], gap="large")

    with col_pie:
        st.markdown('<div class="section-label">Portfolio Allocation by Investment</div>', unsafe_allow_html=True)
        labels = [f["scheme_name"].split("(")[0].strip()[:35] for f in perf_data]
        amounts = [f["invested"] for f in perf_data]

        pie_fig = go.Figure(go.Pie(
            labels=labels,
            values=amounts,
            hole=0.45,
            marker=dict(colors=colors[:len(labels)], line=dict(color="#0b0f19", width=2)),
            textinfo="percent+label",
            textfont=dict(size=11, color="#e2e8f0"),
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        pie_fig.update_layout(
            paper_bgcolor="#111827",
            font=dict(color="#94a3b8", family="Inter"),
            showlegend=False,
            margin=dict(t=20, b=20),
            height=350,
            annotations=[dict(
                text=f"₹{sum(amounts):,.0f}",
                x=0.5, y=0.5, font_size=14, font_color="#00d4aa",
                showarrow=False, font_family="Inter",
            )],
        )
        st.plotly_chart(pie_fig, use_container_width=True)

    # ── 2f: Detailed Data Table ───────────────────────────────
    with col_table:
        st.markdown('<div class="section-label">Detailed Performance Table</div>', unsafe_allow_html=True)
        import pandas as pd

        rows = []
        # Portfolio aggregate row
        pf_row = {
            "Fund": "📁 Portfolio (total NAV)",
            "Code": "—",
            "NAV (₹)": round(total_nav_current, 4),
            "Invested (₹)": f"₹{total_inv:,.0f}",
        }
        for pk, pl in zip(PERIOD_KEYS, PERIOD_LABELS):
            pf_row[pl] = fmt_pct(pf_changes.get(pk))
        rows.append(pf_row)

        for fd in perf_data:
            row = {
                "Fund": fd["scheme_name"].split("(")[0].strip()[:40],
                "Code": fd["scheme_code"],
                "NAV (₹)": round(fd.get("current_nav", 0), 4),
                "Invested (₹)": f"₹{fd['invested']:,.0f}",
            }
            for pk, pl in zip(PERIOD_KEYS, PERIOD_LABELS):
                row[pl] = fmt_pct(get_pct(fd, pk))
            rows.append(row)

        # Benchmark rows
        BM_KEY_MAP2 = {"1d": "change_1d", "1w": "change_1w", "1m": "change_1m", "3m": "change_3m", "6m": "change_6m"}
        for bm in bm_data:
            bm_row = {
                "Fund": f"[BM] {bm['name']}",
                "Code": bm["symbol"],
                "NAV (₹)": bm.get("current_price") or "N/A",
                "Invested (₹)": "—",
            }
            for pk, pl in zip(PERIOD_KEYS, PERIOD_LABELS):
                bm_row[pl] = fmt_pct(bm.get(BM_KEY_MAP2[pk]))
            rows.append(bm_row)

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)

    # ── Footnote ──────────────────────────────────────────────
    st.markdown(
        '<div style="text-align:center; color:#475569; font-size:0.75rem; margin-top:1.5rem">'
        'Data sourced from mfapi.in via OrivisAlpha backend · NAV changes are point-to-point'
        '</div>',
        unsafe_allow_html=True,
    )
