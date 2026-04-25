from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yfinance as yf
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="Financial Instrument Analyzer API",
    description="Fetches current prices, percentage changes, and latest news using yfinance.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PriceChanges(BaseModel):
    one_hour: float | None = Field(default=None, description="1-hour price change percentage")
    one_week: float | None = Field(default=None, description="1-week price change percentage")
    one_month: float | None = Field(default=None, description="1-month price change percentage")
    one_year: float | None = Field(default=None, description="1-year price change percentage")


class NewsItem(BaseModel):
    title: str
    publisher: str | None = None
    link: str | None = None
    published_at: str | None = None
    summary: str | None = None


class QuoteResponse(BaseModel):
    symbol: str
    short_name: str | None = None
    currency: str | None = None
    current_price: float
    changes: PriceChanges
    news: list[NewsItem]
    fetched_at: str


def _percentage_change(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or start == 0:
        return None
    return round(((end - start) / start) * 100, 2)


def _price_change_for_period(ticker: yf.Ticker, period: str, interval: str) -> float | None:
    history = ticker.history(period=period, interval=interval, auto_adjust=False)
    if history.empty or "Close" not in history:
        return None

    closes = history["Close"].dropna()
    if len(closes) < 2:
        return None

    return _percentage_change(float(closes.iloc[0]), float(closes.iloc[-1]))


def _extract_current_price(ticker: yf.Ticker) -> tuple[float | None, dict[str, Any]]:
    info = ticker.get_info()

    for key in ("regularMarketPrice", "currentPrice", "previousClose"):
        value = info.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value), info

    history = ticker.history(period="1d", interval="1m", auto_adjust=False)
    if history.empty or "Close" not in history:
        return None, info

    closes = history["Close"].dropna()
    if closes.empty:
        return None, info

    return float(closes.iloc[-1]), info


def _format_news_timestamp(timestamp: Any) -> str | None:
    if not isinstance(timestamp, (int, float)):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _extract_news(ticker: yf.Ticker, limit: int) -> list[NewsItem]:
    raw_news = ticker.news or []
    news_items: list[NewsItem] = []

    for item in raw_news[:limit]:
        content = item.get("content", item)
        title = content.get("title") or item.get("title")
        if not title:
            continue

        click_through_url = content.get("clickThroughUrl") or {}
        canonical_url = content.get("canonicalUrl") or {}
        provider = content.get("provider") or {}

        news_items.append(
            NewsItem(
                title=title,
                publisher=provider.get("displayName") or item.get("publisher"),
                link=click_through_url.get("url") or canonical_url.get("url") or item.get("link"),
                published_at=_format_news_timestamp(
                    content.get("pubDate")
                    if isinstance(content.get("pubDate"), (int, float))
                    else item.get("providerPublishTime")
                ),
                summary=content.get("summary"),
            )
        )

    return news_items


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/quote/{symbol}", response_model=QuoteResponse)
def get_quote(
    symbol: str,
    news_limit: int = Query(default=5, ge=0, le=20, description="Maximum news items to return"),
) -> QuoteResponse:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Symbol is required.")

    ticker = yf.Ticker(normalized_symbol)

    try:
        current_price, info = _extract_current_price(ticker)
        if current_price is None:
            raise HTTPException(status_code=404, detail=f"No market data found for {normalized_symbol}.")

        changes = PriceChanges(
            one_hour=_price_change_for_period(ticker, "1d", "1m"),
            one_week=_price_change_for_period(ticker, "5d", "30m"),
            one_month=_price_change_for_period(ticker, "1mo", "1d"),
            one_year=_price_change_for_period(ticker, "1y", "1d"),
        )

        return QuoteResponse(
            symbol=normalized_symbol,
            short_name=info.get("shortName") or info.get("longName"),
            currency=info.get("currency"),
            current_price=round(current_price, 4),
            changes=changes,
            news=_extract_news(ticker, news_limit),
            fetched_at=datetime.now(tz=timezone.utc).isoformat(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to fetch data from yfinance: {exc}") from exc
