# ============================================================
# SMA — STOCK MARKET ANALYSIS
# app.py
# ============================================================

import time
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SMA — Stock Market Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- GLOBAL ---------- */

    .stApp {
        background: #f7f8fa;
        color: #171717;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* ---------- BRAND ---------- */

    .brand {
        font-size: 34px;
        font-weight: 800;
        letter-spacing: 3px;
        color: #f2c76e;
        margin-bottom: 0;
    }

    .brand-subtitle {
        color: #6b7280;
        font-size: 13px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    /* ---------- HERO ---------- */

    .hero {
        padding: 35px;
        border: 1px solid rgba(242,199,110,0.20);
        border-radius: 24px;
        background: #ffffff;
        box-shadow: 0 12px 40px rgba(0,0,0,0.08);
        margin: 25px 0;
    }

    .hero-title {
        font-size: 48px;
        font-weight: 800;
        line-height: 1.05;
        margin-bottom: 12px;
    }

    .hero-text {
        color: #6b7280;
        font-size: 16px;
        max-width: 650px;
    }

    /* ---------- CARDS ---------- */

    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 22px;
        min-height: 125px;
    }

    .metric-label {
        color: #6b7280;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }

    .metric-value {
        font-size: 27px;
        font-weight: 750;
        margin-top: 8px;
    }

    .metric-positive {
        color: #55d68a;
    }

    .metric-negative {
        color: #ff6675;
    }

    .metric-neutral {
        color: #f2c76e;
    }

    /* ---------- SIGNAL ---------- */

    .signal-buy {
        display: inline-block;
        padding: 8px 18px;
        border-radius: 30px;
        background: rgba(70,210,130,0.12);
        border: 1px solid rgba(70,210,130,0.3);
        color: #55d68a;
        font-weight: 700;
    }

    .signal-hold {
        display: inline-block;
        padding: 8px 18px;
        border-radius: 30px;
        background: rgba(242,199,110,0.12);
        border: 1px solid rgba(242,199,110,0.3);
        color: #f2c76e;
        font-weight: 700;
    }

    .signal-sell {
        display: inline-block;
        padding: 8px 18px;
        border-radius: 30px;
        background: rgba(255,80,95,0.12);
        border: 1px solid rgba(255,80,95,0.3);
        color: #ff6675;
        font-weight: 700;
    }

    /* ---------- SECTION ---------- */

    .section-title {
        font-size: 24px;
        font-weight: 750;
        margin-top: 35px;
        margin-bottom: 15px;
    }

    .muted {
        color: #858585;
    }

    /* ---------- FOOTER ---------- */

    .footer {
        text-align: center;
        color: #6b7280;
        margin-top: 60px;
        font-size: 12px;
    }



    /* ---------- LIGHT THEME ---------- */

    [data-testid="stRadio"] label,
    [data-testid="stTextInput"] label,
    [data-testid="stSelectbox"] label {
        color: #374151 !important;
    }

    [data-baseweb="input"],
    [data-baseweb="select"] > div {
        background: #ffffff !important;
        color: #111827 !important;
        border-color: #d1d5db !important;
    }

    [data-baseweb="select"] * {
        color: #111827 !important;
    }

    [data-testid="stDataFrame"] {
        background: #ffffff;
    }

        </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# STOCK UNIVERSE
# ============================================================

STOCKS = {

    # ---------------- NSE ----------------

    "RELIANCE.NS": {
        "symbol": "RELIANCE",
        "name": "Reliance Industries",
        "exchange": "NSE",
    },

    "TCS.NS": {
        "symbol": "TCS",
        "name": "Tata Consultancy Services",
        "exchange": "NSE",
    },

    "INFY.NS": {
        "symbol": "INFY",
        "name": "Infosys",
        "exchange": "NSE",
    },

    "HDFCBANK.NS": {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank",
        "exchange": "NSE",
    },

    "ICICIBANK.NS": {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank",
        "exchange": "NSE",
    },

    "SBIN.NS": {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "exchange": "NSE",
    },

    "ITC.NS": {
        "symbol": "ITC",
        "name": "ITC Limited",
        "exchange": "NSE",
    },

    "BHARTIARTL.NS": {
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel",
        "exchange": "NSE",
    },

    "LT.NS": {
        "symbol": "LT",
        "name": "Larsen & Toubro",
        "exchange": "NSE",
    },

    "WIPRO.NS": {
        "symbol": "WIPRO",
        "name": "Wipro",
        "exchange": "NSE",
    },

    "HCLTECH.NS": {
        "symbol": "HCLTECH",
        "name": "HCL Technologies",
        "exchange": "NSE",
    },

    "MARUTI.NS": {
        "symbol": "MARUTI",
        "name": "Maruti Suzuki India",
        "exchange": "NSE",
    },

    "SUNPHARMA.NS": {
        "symbol": "SUNPHARMA",
        "name": "Sun Pharmaceutical",
        "exchange": "NSE",
    },

    "TATASTEEL.NS": {
        "symbol": "TATASTEEL",
        "name": "Tata Steel",
        "exchange": "NSE",
    },

    "TATAMOTORS.NS": {
        "symbol": "TATAMOTORS",
        "name": "Tata Motors",
        "exchange": "NSE",
    },

    "BAJFINANCE.NS": {
        "symbol": "BAJFINANCE",
        "name": "Bajaj Finance",
        "exchange": "NSE",
    },

    "AXISBANK.NS": {
        "symbol": "AXISBANK",
        "name": "Axis Bank",
        "exchange": "NSE",
    },

    "KOTAKBANK.NS": {
        "symbol": "KOTAKBANK",
        "name": "Kotak Mahindra Bank",
        "exchange": "NSE",
    },

    "ASIANPAINT.NS": {
        "symbol": "ASIANPAINT",
        "name": "Asian Paints",
        "exchange": "NSE",
    },

    "TITAN.NS": {
        "symbol": "TITAN",
        "name": "Titan Company",
        "exchange": "NSE",
    },

    "ADANIENT.NS": {
        "symbol": "ADANIENT",
        "name": "Adani Enterprises",
        "exchange": "NSE",
    },

    "ADANIPORTS.NS": {
        "symbol": "ADANIPORTS",
        "name": "Adani Ports",
        "exchange": "NSE",
    },

    "NTPC.NS": {
        "symbol": "NTPC",
        "name": "NTPC Limited",
        "exchange": "NSE",
    },

    "POWERGRID.NS": {
        "symbol": "POWERGRID",
        "name": "Power Grid Corporation",
        "exchange": "NSE",
    },

    "ONGC.NS": {
        "symbol": "ONGC",
        "name": "Oil & Natural Gas Corporation",
        "exchange": "NSE",
    },

    "COALINDIA.NS": {
        "symbol": "COALINDIA",
        "name": "Coal India",
        "exchange": "NSE",
    },

    "BEL.NS": {
        "symbol": "BEL",
        "name": "Bharat Electronics",
        "exchange": "NSE",
    },

    "HAL.NS": {
        "symbol": "HAL",
        "name": "Hindustan Aeronautics",
        "exchange": "NSE",
    },

    "IRFC.NS": {
        "symbol": "IRFC",
        "name": "Indian Railway Finance Corporation",
        "exchange": "NSE",
    },

    "IREDA.NS": {
        "symbol": "IREDA",
        "name": "Indian Renewable Energy Development Agency",
        "exchange": "NSE",
    },


    # ---------------- US ----------------

    "AAPL": {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "exchange": "NASDAQ",
    },

    "MSFT": {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
    },

    "GOOGL": {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "exchange": "NASDAQ",
    },

    "AMZN": {
        "symbol": "AMZN",
        "name": "Amazon.com Inc.",
        "exchange": "NASDAQ",
    },

    "NVDA": {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "exchange": "NASDAQ",
    },

    "META": {
        "symbol": "META",
        "name": "Meta Platforms",
        "exchange": "NASDAQ",
    },

    "TSLA": {
        "symbol": "TSLA",
        "name": "Tesla Inc.",
        "exchange": "NASDAQ",
    },
}


# ============================================================
# INDICES
# ============================================================

INDICES = {

    "^NSEI": {
        "symbol": "NIFTY 50",
        "name": "NIFTY 50",
        "exchange": "NSE",
    },

    "^NSEBANK": {
        "symbol": "BANK NIFTY",
        "name": "NIFTY Bank",
        "exchange": "NSE",
    },

    "^BSESN": {
        "symbol": "SENSEX",
        "name": "BSE SENSEX",
        "exchange": "BSE",
    },
}


# ============================================================
# DATA DOWNLOAD
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def get_stock_data(ticker, period="1y"):

    try:

        df = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df is None or df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [str(c).lower() for c in df.columns]

        required = [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for col in required:
            if col not in df.columns:
                df[col] = np.nan

        df = df[required].copy()

        df = df.dropna(subset=["close"])

        return df

    except Exception:
        return pd.DataFrame()


# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(series):

    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    return macd, signal


def calculate_indicators(df):

    if df.empty:
        return df

    df = df.copy()

    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()
    df["sma_200"] = df["close"].rolling(200).mean()

    df["ema_20"] = df["close"].ewm(
        span=20,
        adjust=False
    ).mean()

    df["ema_50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    df["rsi"] = calculate_rsi(df["close"])

    df["macd"], df["macd_signal"] = calculate_macd(
        df["close"]
    )

    df["bb_middle"] = df["close"].rolling(20).mean()

    bb_std = df["close"].rolling(20).std()

    df["bb_upper"] = (
        df["bb_middle"] + 2 * bb_std
    )

    df["bb_lower"] = (
        df["bb_middle"] - 2 * bb_std
    )

    df["returns"] = df["close"].pct_change()

    df["volatility"] = (
        df["returns"].rolling(20).std() * np.sqrt(252) * 100
    )

    df["momentum_5"] = (
        df["close"].pct_change(5) * 100
    )

    df["momentum_20"] = (
        df["close"].pct_change(20) * 100
    )

    return df


# ============================================================
# SIGNAL
# ============================================================

def calculate_signal(df):

    if df.empty:
        return "HOLD", 0

    row = df.iloc[-1]

    score = 0

    close = row["close"]

    sma20 = row["sma_20"]
    sma50 = row["sma_50"]
    rsi = row["rsi"]

    if pd.notna(sma20):

        if close > sma20:
            score += 1
        else:
            score -= 1

    if pd.notna(sma50):

        if close > sma50:
            score += 1
        else:
            score -= 1

    if pd.notna(rsi):

        if rsi < 35:
            score += 2

        elif rsi > 70:
            score -= 2

    if score >= 2:
        return "BUY", score

    if score <= -2:
        return "SELL", score

    return "HOLD", score


# ============================================================
# ESTIMATED PRICE
# ============================================================

def calculate_estimated_price(df):

    if df.empty:
        return None

    close = float(df["close"].iloc[-1])

    momentum = df["momentum_20"].iloc[-1]

    if pd.isna(momentum):
        momentum = 0

    estimated_return = momentum * 0.25

    estimated_price = close * (
        1 + estimated_return / 100
    )

    return estimated_price


# ============================================================
# FORMAT
# ============================================================

def money(value):

    if value is None or pd.isna(value):
        return "—"

    return f"₹{value:,.2f}"


def percent(value):

    if value is None or pd.isna(value):
        return "—"

    return f"{value:+.2f}%"


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>📈 SMA — Stock Market Analysis</h1>
        <p>
            Real-Time Stock Data • Expected Price • Returns •
            Signals • Confidence • Technical Analysis • News
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# NAVIGATION
# ============================================================

page = st.radio(
    "Navigation",
    [
        "Home",
        "Stock Analysis",
        "All Stocks",
    ],
    horizontal=True,
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "Home":

    st.markdown(
        """
        <div class="hero">

            <div class="hero-title">
                Smarter Market Intelligence.
            </div>

            <div class="hero-text">
                Analyze stocks using price action,
                technical indicators, momentum and
                algorithmic signals.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">Market Overview</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3)

    for col, (ticker, info) in zip(
        cols,
        INDICES.items()
    ):

        df = get_stock_data(
            ticker,
            period="5d"
        )

        with col:

            if df.empty:

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">
                            {info["symbol"]}
                        </div>

                        <div class="metric-value">
                            Data unavailable
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                continue

            current = float(df["close"].iloc[-1])

            if len(df) > 1:

                previous = float(
                    df["close"].iloc[-2]
                )

                change = (
                    (current - previous)
                    / previous
                    * 100
                )

            else:
                change = 0

            css_class = (
                "metric-positive"
                if change >= 0
                else "metric-negative"
            )

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-label">
                        {info["symbol"]}
                    </div>

                    <div class="metric-value">
                        {current:,.2f}
                    </div>

                    <div class="{css_class}">
                        {change:+.2f}%
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# STOCK ANALYSIS
# ============================================================

elif page == "Stock Analysis":

    st.markdown(
        '<div class="section-title">Stock Analysis</div>',
        unsafe_allow_html=True,
    )

    search = st.text_input(
        "Search stock",
        placeholder="Example: TCS, INFY, RELIANCE, AAPL"
    )

    search = search.strip().upper()

    matches = []

    for ticker, info in STOCKS.items():

        if (
            not search
            or search in info["symbol"].upper()
            or search in info["name"].upper()
        ):
            matches.append(ticker)

    if not matches:

        st.warning("Stock not found.")

    else:

        selected = st.selectbox(
            "Select stock",
            matches,
            format_func=lambda x:
                f'{STOCKS[x]["symbol"]} — {STOCKS[x]["name"]}'
        )

        info = STOCKS[selected]

        df = get_stock_data(
            selected,
            period="1y"
        )

        if df.empty:

            st.error(
                "Market data is currently unavailable."
            )

        else:

            df = calculate_indicators(df)

            latest = df.iloc[-1]

            current = float(
                latest["close"]
            )

            previous = (
                float(df["close"].iloc[-2])
                if len(df) > 1
                else current
            )

            daily_change = (
                (current - previous)
                / previous
                * 100
            )

            signal, score = calculate_signal(df)

            estimated = calculate_estimated_price(df)

            # --------------------------------------------
            # TITLE
            # --------------------------------------------

            st.markdown(
                f"""
                <div class="hero">

                    <div class="brand">
                        {info["symbol"]}
                    </div>

                    <div class="hero-text">
                        {info["name"]}
                        · {info["exchange"]}
                    </div>

                    <div style="
                        font-size:42px;
                        font-weight:800;
                        margin-top:20px;
                    ">
                        {money(current)}
                    </div>

                    <div class="
                        {"metric-positive"
                        if daily_change >= 0
                        else "metric-negative"}
                    ">
                        {percent(daily_change)}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            # --------------------------------------------
            # METRICS
            # --------------------------------------------

            cols = st.columns(5)

            metrics = [
                (
                    "SMA 20",
                    money(latest["sma_20"])
                ),
                (
                    "SMA 50",
                    money(latest["sma_50"])
                ),
                (
                    "RSI",
                    (
                        f'{latest["rsi"]:.2f}'
                        if pd.notna(latest["rsi"])
                        else "—"
                    )
                ),
                (
                    "Momentum",
                    percent(latest["momentum_20"])
                ),
                (
                    "Volatility",
                    (
                        f'{latest["volatility"]:.2f}%'
                        if pd.notna(latest["volatility"])
                        else "—"
                    )
                ),
            ]

            for col, (label, value) in zip(
                cols,
                metrics
            ):

                with col:

                    st.markdown(
                        f"""
                        <div class="metric-card">

                            <div class="metric-label">
                                {label}
                            </div>

                            <div class="metric-value">
                                {value}
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # --------------------------------------------
            # CHART
            # --------------------------------------------

            st.markdown(
                '<div class="section-title">Price Chart</div>',
                unsafe_allow_html=True,
            )

            chart_df = df[
                ["close", "sma_20", "sma_50"]
            ].copy()

            chart_df.columns = [
                "Price",
                "SMA 20",
                "SMA 50",
            ]

            st.line_chart(
                chart_df,
                height=430,
            )

            # --------------------------------------------
            # SIGNAL
            # --------------------------------------------

            st.markdown(
                '<div class="section-title">Analysis Signal</div>',
                unsafe_allow_html=True,
            )

            signal_class = {
                "BUY": "signal-buy",
                "HOLD": "signal-hold",
                "SELL": "signal-sell",
            }[signal]

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    f"""
                    <div class="metric-card">

                        <div class="metric-label">
                            Current Signal
                        </div>

                        <div style="margin-top:15px;">
                            <span class="{signal_class}">
                                {signal}
                            </span>
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col2:

                st.markdown(
                    f"""
                    <div class="metric-card">

                        <div class="metric-label">
                            Estimated Price
                        </div>

                        <div class="metric-value">
                            {money(estimated)}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # --------------------------------------------
            # RAW DATA
            # --------------------------------------------

            with st.expander("View market data"):

                display_df = df.tail(30).copy()

                st.dataframe(
                    display_df,
                    width="stretch",
                )


# ============================================================
# ALL STOCKS
# ============================================================

elif page == "All Stocks":

    st.markdown(
        '<div class="section-title">All Supported Stocks</div>',
        unsafe_allow_html=True,
    )

    search = st.text_input(
        "Search",
        placeholder="Search symbol or company name..."
    ).strip().upper()

    rows = []

    for ticker, info in STOCKS.items():

        if search and not (
            search in info["symbol"].upper()
            or search in info["name"].upper()
        ):
            continue

        df = get_stock_data(
            ticker,
            period="5d"
        )

        if df.empty:
            continue

        current = float(
            df["close"].iloc[-1]
        )

        if len(df) > 1:

            previous = float(
                df["close"].iloc[-2]
            )

            change = (
                (current - previous)
                / previous
                * 100
            )

        else:
            change = 0

        rows.append(
            {
                "Symbol": info["symbol"],
                "Company": info["name"],
                "Exchange": info["exchange"],
                "Price": current,
                "Change %": change,
            }
        )

        # Small delay to reduce aggressive requests
        time.sleep(0.05)

    if rows:

        table = pd.DataFrame(rows)

        table = table.sort_values(
            "Change %",
            ascending=False
        )

        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
        )

    else:

        st.warning(
            "No market data available."
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        SMA — Stock Market Analysis
        <br>
        Market data provided by external market-data services.
        This application is for informational purposes only.
    </div>
    """,
    unsafe_allow_html=True,
)
