import gzip
import io
from datetime import datetime, time, date
from zoneinfo import ZoneInfo

import requests
import pandas as pd
import streamlit as st

IST = ZoneInfo("Asia/Kolkata")
INSTRUMENT_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
CANDLE_URL = "https://api.upstox.com/v3/historical-candle/intraday/{}/minutes/1"

st.set_page_config(
    page_title="NSE AI Stock Scanner",
    page_icon="📈",
    layout="wide"
)

st.title("📈 NSE Stock Scanner — V1")
st.caption(
    "Scan NSE equities for price increases during a selected intraday window."
)

with st.sidebar:
    token = st.text_input("Upstox access token", type="password")
    scan_date = st.date_input("Trading date", date.today())
    start_t = st.time_input("Start time", time(14, 0))
    end_t = st.time_input("End time", time(15, 0))
    min_pct = st.number_input(
        "Minimum increase (%)", 0.0, 50.0, 1.0, 0.1
    )
    top_n = st.number_input("Top N results", 5, 100, 20, 5)
    max_stocks = st.number_input(
        "Max stocks to scan", 10, 3000, 100, 10
    )


@st.cache_data(ttl=3600)
def load_instruments():
    r = requests.get(INSTRUMENT_URL, timeout=30)
    r.raise_for_status()

    raw = gzip.decompress(r.content)
    df = pd.read_json(io.BytesIO(raw))

    return df[
        (df["segment"] == "NSE_EQ")
        & (df["instrument_type"] == "EQ")
    ].drop_duplicates("instrument_key")


def candles(token, key):
    r = requests.get(
        CANDLE_URL.format(key),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        timeout=15,
    )

    if r.status_code != 200:
        return None

    rows = r.json().get("data", {}).get("candles", [])

    if not rows:
        return None

    return pd.DataFrame(
        rows,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "oi",
        ],
    )


def scan(token, universe):
    start = pd.Timestamp(
        datetime.combine(scan_date, start_t),
        tz=IST
    )

    end = pd.Timestamp(
        datetime.combine(scan_date, end_t),
        tz=IST
    )

    output = []

    bar = st.progress(0)

    total = len(universe)

    for position, (_, row) in enumerate(universe.iterrows(), start=1):
        df = candles(token, row["instrument_key"])

        if df is not None:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Handle timestamps returned with/without timezone.
            if df["timestamp"].dt.tz is None:
                df["timestamp"] = df["timestamp"].dt.tz_localize(IST)
            else:
                df["timestamp"] = df["timestamp"].dt.tz_convert(IST)

            df = df[
                (df["timestamp"] >= start)
                & (df["timestamp"] <= end)
            ].sort_values("timestamp")

            if not df.empty:
                p0 = float(df.iloc[0]["close"])
                p1 = float(df.iloc[-1]["close"])

                chg = ((p1 - p0) / p0 * 100) if p0 else 0

                if chg >= min_pct:
                    output.append(
                        {
                            "Symbol": row["trading_symbol"],
                            "Company": row.get("name", ""),
                            "Start Price": p0,
                            "End Price": p1,
                            "Change %": chg,
                            "Window High": float(df["high"].max()),
                            "Window Low": float(df["low"].min()),
                            "Volume": int(df["volume"].sum()),
                        }
                    )

        bar.progress(position / total)

    bar.empty()

    if not output:
        return pd.DataFrame()

    return (
        pd.DataFrame(output)
        .sort_values("Change %", ascending=False)
        .head(int(top_n))
    )


if st.button("Load NSE universe"):
    try:
        st.session_state.universe = load_instruments()
        st.success(
            f"Loaded {len(st.session_state.universe):,} NSE equities."
        )
    except Exception as e:
        st.error(f"Unable to load NSE universe: {e}")


universe = st.session_state.get("universe")

if universe is not None:
    st.dataframe(
        universe[
            ["trading_symbol", "name", "instrument_key"]
        ].head(10),
        use_container_width=True,
        hide_index=True,
    )


if st.button("🔎 Scan stocks", type="primary"):
    if not token:
        st.error("Enter your Upstox access token.")

    elif start_t >= end_t:
        st.error("End time must be later than start time.")

    elif universe is None:
        st.error("Load the NSE universe first.")

    else:
        u = universe.head(int(max_stocks))

        st.warning(
            f"Scanning {len(u)} instruments. "
            "V1 intentionally limits the scan to reduce API load."
        )

        try:
            result = scan(token, u)

            if result.empty:
                st.info(
                    "No stocks met the selected increase threshold."
                )

            else:
                st.success(
                    f"Found {len(result)} qualifying stocks."
                )

                st.dataframe(
                    result.style.format(
                        {
                            "Start Price": "₹{:,.2f}",
                            "End Price": "₹{:,.2f}",
                            "Change %": "{:.2f}%",
                            "Window High": "₹{:,.2f}",
                            "Window Low": "₹{:,.2f}",
                            "Volume": "{:,.0f}",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "⬇️ Download CSV",
                    result.to_csv(index=False),
                    f"nse_scan_{scan_date}.csv",
                    "text/csv",
                )

        except Exception as e:
            st.error(f"Scan failed: {e}")


st.divider()

st.write(
    "**V1 definition:** percentage change = "
    "(last 1-minute close in the selected window − first "
    "1-minute close) / first close × 100."
)

st.caption(
    "Analysis tool only; it does not place trades or guarantee returns."
)
