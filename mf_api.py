from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
from datetime import datetime, timedelta
import math
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

app = FastAPI(
    title="Indian Mutual Fund Price API",
    description=(
        "Fetch current NAV and price change (1D, 1W, 1M, 3M, 6M) "
        "for any Indian Mutual Fund using its AMFI scheme code."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MFAPI_BASE = "https://api.mfapi.in/mf"


# ──────────────────────────────────────────────
# Response Models
# ──────────────────────────────────────────────

class PriceChange(BaseModel):
    nav: Optional[float]
    change: Optional[float]
    change_pct: Optional[float]
    date: Optional[str]


class MutualFundResponse(BaseModel):
    scheme_code: int
    scheme_name: str
    fund_house: str
    scheme_type: str
    scheme_category: str
    current_nav: float
    current_date: str
    change_1d: PriceChange
    change_1w: PriceChange
    change_1m: PriceChange
    change_3m: PriceChange
    change_6m: PriceChange


class SearchResult(BaseModel):
    scheme_code: int
    scheme_name: str
    fund_house: str
    scheme_type: str
    scheme_category: str


class BenchmarkPeriod(BaseModel):
    symbol: str
    name: str
    current_price: Optional[float]
    currency: Optional[str]
    change_1d: Optional[float]   # % change
    change_1w: Optional[float]
    change_1m: Optional[float]
    change_3m: Optional[float]
    change_6m: Optional[float]


class BenchmarksResponse(BaseModel):
    benchmarks: list[BenchmarkPeriod]
    fetched_at: str


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def fetch_fund_data(scheme_code: int) -> dict:
    """Fetch NAV history from mfapi.in for a given scheme code."""
    url = f"{MFAPI_BASE}/{scheme_code}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Scheme code {scheme_code} not found.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Upstream mfapi.in returned an error.")
    data = resp.json()
    if data.get("status") != "SUCCESS" or not data.get("data"):
        raise HTTPException(status_code=404, detail=f"No NAV data available for scheme {scheme_code}.")
    return data


def parse_date(date_str: str) -> datetime:
    """Parse DD-MM-YYYY date string from mfapi.in."""
    return datetime.strptime(date_str, "%d-%m-%Y")


def find_nav_on_or_before(nav_list: list[dict], target_date: datetime) -> Optional[dict]:
    """
    NAV list is sorted newest-first.
    Find the closest NAV entry on or before target_date.
    """
    for entry in nav_list:
        entry_date = parse_date(entry["date"])
        if entry_date <= target_date:
            return entry
    return None


def build_price_change(current_nav: float, historical_entry: Optional[dict]) -> PriceChange:
    if not historical_entry:
        return PriceChange(nav=None, change=None, change_pct=None, date=None)
    hist_nav = float(historical_entry["nav"])
    change = round(current_nav - hist_nav, 4)
    change_pct = round((change / hist_nav) * 100, 4) if hist_nav else None
    return PriceChange(
        nav=hist_nav,
        change=change,
        change_pct=change_pct,
        date=historical_entry["date"],
    )


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Health check and API info."""
    return {
        "status": "ok",
        "api": "Indian Mutual Fund Price API",
        "version": "1.0.0",
        "docs": "/docs",
        "usage": "GET /mf/{scheme_code}  →  current NAV + price changes",
    }


@app.get(
    "/mf/{scheme_code}",
    response_model=MutualFundResponse,
    tags=["Mutual Fund"],
    summary="Get NAV & Price Changes",
    description=(
        "Returns the current NAV and absolute + percentage price changes "
        "over 1 day, 1 week, 1 month, 3 months, and 6 months for the given "
        "AMFI mutual fund scheme code."
    ),
)
async def get_mf_data(
    scheme_code: int = Path(..., description="AMFI scheme code (e.g. 120503 for Mirae Asset Large Cap)", example=120503)
):
    data = await fetch_fund_data(scheme_code)
    meta = data["meta"]
    nav_list = data["data"]  # newest first

    # Current NAV
    latest = nav_list[0]
    current_nav = float(latest["nav"])
    current_date = latest["date"]
    current_dt = parse_date(current_date)

    # Reference dates
    ref_dates = {
        "1d":  current_dt - timedelta(days=1),
        "1w":  current_dt - timedelta(weeks=1),
        "1m":  current_dt - timedelta(days=30),
        "3m":  current_dt - timedelta(days=91),
        "6m":  current_dt - timedelta(days=182),
    }

    return MutualFundResponse(
        scheme_code=scheme_code,
        scheme_name=meta.get("scheme_name", ""),
        fund_house=meta.get("fund_house", ""),
        scheme_type=meta.get("scheme_type", ""),
        scheme_category=meta.get("scheme_category", ""),
        current_nav=current_nav,
        current_date=current_date,
        change_1d=build_price_change(current_nav, find_nav_on_or_before(nav_list[1:], ref_dates["1d"])),
        change_1w=build_price_change(current_nav, find_nav_on_or_before(nav_list[1:], ref_dates["1w"])),
        change_1m=build_price_change(current_nav, find_nav_on_or_before(nav_list[1:], ref_dates["1m"])),
        change_3m=build_price_change(current_nav, find_nav_on_or_before(nav_list[1:], ref_dates["3m"])),
        change_6m=build_price_change(current_nav, find_nav_on_or_before(nav_list[1:], ref_dates["6m"])),
    )


@app.get(
    "/mf/{scheme_code}/current",
    tags=["Mutual Fund"],
    summary="Get Current NAV Only",
    description="Returns only the latest NAV for a mutual fund scheme.",
)
async def get_current_nav(
    scheme_code: int = Path(..., description="AMFI scheme code", example=120503)
):
    data = await fetch_fund_data(scheme_code)
    latest = data["data"][0]
    return {
        "scheme_code": scheme_code,
        "scheme_name": data["meta"].get("scheme_name"),
        "current_nav": float(latest["nav"]),
        "date": latest["date"],
    }


@app.get(
    "/search",
    response_model=list[SearchResult],
    tags=["Search"],
    summary="Search Mutual Funds by Name",
    description="Search for mutual funds by name keyword. Returns a list of matching scheme codes and names.",
)
async def search_funds(
    q: str = Query(..., description="Fund name keyword to search", example="Mirae Asset")
):
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{MFAPI_BASE}/")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not fetch fund list from mfapi.in")

    all_funds = resp.json()
    keyword = q.lower()
    matches = [
        SearchResult(
            scheme_code=f["schemeCode"],
            scheme_name=f["schemeName"],
            fund_house=f.get("fundHouse", ""),
            scheme_type=f.get("schemeType", ""),
            scheme_category=f.get("schemeCategory", ""),
        )
        for f in all_funds
        if keyword in f.get("schemeName", "").lower()
    ]

    if not matches:
        raise HTTPException(status_code=404, detail=f"No funds found matching '{q}'")

    return matches[:50]  # cap at 50 results


# ──────────────────────────────────────────────
# Benchmark Symbols
# ──────────────────────────────────────────────

BENCHMARK_SYMBOLS = [
    {"symbol": "^NSEI",    "name": "Nifty 50"},
    {"symbol": "^GSPC",    "name": "S&P 500"},
    {"symbol": "XAUUSD=X", "name": "Gold Spot"},
    {"symbol": "XAGUSD=X", "name": "Silver Spot"},
]

# Trading sessions to look back per period
PERIOD_SESSIONS = {"1d": 1, "1w": 5, "1m": 21, "3m": 63, "6m": 126}


def _fetch_one_benchmark(bm: dict) -> BenchmarkPeriod:
    """
    Fetch 1 year of daily history for a symbol in a single yf.download() call,
    then derive all period % changes from that one dataset.
    """
    sym = bm["symbol"]
    try:
        df = yf.download(
            sym,
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if df.empty or "Close" not in df.columns:
            raise ValueError("No data")

        # Flatten MultiIndex columns — yf.download() always returns MultiIndex
        # in newer versions even for a single ticker
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)

        closes = df["Close"].dropna()
        cur_price = float(closes.iloc[-1])
        n = len(closes)

        def pct(sessions: int) -> Optional[float]:
            ref_idx = max(0, n - 1 - sessions)
            ref = float(closes.iloc[ref_idx])
            if ref == 0:
                return None
            return round(((cur_price - ref) / ref) * 100, 4)

        # Currency: derive from ticker info (fast call, cached by yf)
        try:
            info = yf.Ticker(sym).fast_info
            currency = getattr(info, "currency", None)
        except Exception:
            currency = None

        return BenchmarkPeriod(
            symbol=sym,
            name=bm["name"],
            current_price=round(cur_price, 6),
            currency=currency,
            change_1d=pct(PERIOD_SESSIONS["1d"]),
            change_1w=pct(PERIOD_SESSIONS["1w"]),
            change_1m=pct(PERIOD_SESSIONS["1m"]),
            change_3m=pct(PERIOD_SESSIONS["3m"]),
            change_6m=pct(PERIOD_SESSIONS["6m"]),
        )

    except Exception as exc:
        # Return a stub with nulls so the endpoint never crashes
        return BenchmarkPeriod(
            symbol=sym, name=bm["name"],
            current_price=None, currency=None,
            change_1d=None, change_1w=None,
            change_1m=None, change_3m=None, change_6m=None,
        )


@app.get(
    "/benchmarks",
    response_model=BenchmarksResponse,
    tags=["Benchmarks"],
    summary="Get Benchmark Performance",
    description=(
        "Returns price % changes over 1 day, 1 week, 1 month, 3 months, and 6 months "
        "for Nifty 50 (^NSEI), S&P 500 (^GSPC), Gold Spot (XAUUSD=X), and Silver Spot (XAGUSD=X)."
    ),
)
def get_benchmarks():
    """Fetch all 4 benchmarks in parallel — one yf.download() per symbol."""
    results_map: dict[str, BenchmarkPeriod] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_one_benchmark, bm): bm["symbol"] for bm in BENCHMARK_SYMBOLS}
        for future in as_completed(futures):
            sym = futures[future]
            results_map[sym] = future.result()

    # Preserve the original order
    ordered = [results_map[bm["symbol"]] for bm in BENCHMARK_SYMBOLS]
    return BenchmarksResponse(
        benchmarks=ordered,
        fetched_at=datetime.utcnow().isoformat() + "Z",
    )
