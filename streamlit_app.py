from __future__ import annotations

from datetime import datetime

import requests
import streamlit as st


API_BASE_URL = "http://localhost:8000"


st.set_page_config(page_title="Financial Instrument Analyzer", layout="wide")

st.title("Financial Instrument Analyzer")

with st.sidebar:
    st.header("Backend")
    api_base_url = st.text_input("FastAPI base URL", value=API_BASE_URL)
    news_limit = st.slider("News items", min_value=0, max_value=20, value=5)

symbol = st.text_input("Stock or financial instrument symbol", placeholder="AAPL, MSFT, TSLA, BTC-USD")
submitted = st.button("Fetch data", type="primary")


def format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def format_datetime(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return value


if submitted:
    normalized_symbol = symbol.strip()

    if not normalized_symbol:
        st.warning("Enter a symbol to continue.")
        st.stop()

    with st.spinner(f"Fetching market data for {normalized_symbol.upper()}..."):
        try:
            response = requests.get(
                f"{api_base_url.rstrip('/')}/quote/{normalized_symbol}",
                params={"news_limit": news_limit},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError as exc:
            detail = exc.response.json().get("detail", exc.response.text)
            st.error(f"Backend error: {detail}")
            st.stop()
        except requests.exceptions.RequestException as exc:
            st.error(f"Could not reach the FastAPI backend: {exc}")
            st.stop()

    heading = data.get("short_name") or data["symbol"]
    currency = data.get("currency") or ""
    st.subheader(f"{heading} ({data['symbol']})")

    price_label = f"{data['current_price']:,.4f} {currency}".strip()
    st.metric("Current price", price_label)

    changes = data.get("changes", {})
    cols = st.columns(4)
    cols[0].metric("1 hour", format_percent(changes.get("one_hour")))
    cols[1].metric("1 week", format_percent(changes.get("one_week")))
    cols[2].metric("1 month", format_percent(changes.get("one_month")))
    cols[3].metric("1 year", format_percent(changes.get("one_year")))

    st.caption(f"Fetched at {format_datetime(data.get('fetched_at'))}")

    st.divider()
    st.subheader("Latest news")

    news_items = data.get("news", [])
    if not news_items:
        st.info("No recent yfinance news was returned for this symbol.")
    else:
        for item in news_items:
            title = item.get("title", "Untitled")
            link = item.get("link")
            publisher = item.get("publisher") or "Unknown publisher"
            published_at = format_datetime(item.get("published_at"))

            if link:
                st.markdown(f"### [{title}]({link})")
            else:
                st.markdown(f"### {title}")

            meta = " | ".join(part for part in (publisher, published_at) if part)
            if meta:
                st.caption(meta)

            if item.get("summary"):
                st.write(item["summary"])
else:
    st.info("Start the FastAPI backend, enter a symbol, and fetch the latest market snapshot.")
