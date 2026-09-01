import os
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
# LOAD CSS
# ============================================================

from pathlib import Path

def load_css():
    css_path = Path(__file__).parent / "style.css"

    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True
        )
    else:
        st.error(f"CSS file not found: {css_path}")


load_css()

# ============================================================
# STOCK LIST
# ============================================================

STOCKS = {
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "RELIANCE": "RELIANCE.NS",
    "WIPRO": "WIPRO.NS",

    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "AXISBANK": "AXISBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "INDUSINDBK": "INDUSINDBK.NS",

    "LT": "LT.NS",
    "ITC": "ITC.NS",
    "BHARTIARTL": "BHARTIARTL.NS",

    "MARUTI": "MARUTI.NS",

    "TATASTEEL": "TATASTEEL.NS",
    "TATACONSUM": "TATACONSUM.NS",

    "SUNPHARMA": "SUNPHARMA.NS",
    "DRREDDY": "DRREDDY.NS",
    "CIPLA": "CIPLA.NS",

    "HINDUNILVR": "HINDUNILVR.NS",
    "ASIANPAINT": "ASIANPAINT.NS",

    "BAJFINANCE": "BAJFINANCE.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS",

    "ADANIENT": "ADANIENT.NS",
    "ADANIPORTS": "ADANIPORTS.NS",

    "NTPC": "NTPC.NS",
    "POWERGRID": "POWERGRID.NS",
    "ONGC": "ONGC.NS",
    "COALINDIA": "COALINDIA.NS",
    "BPCL": "BPCL.NS",

    "JSWSTEEL": "JSWSTEEL.NS",
    "HINDALCO": "HINDALCO.NS",

    "HCLTECH": "HCLTECH.NS",
    "TECHM": "TECHM.NS",

    "APOLLOHOSP": "APOLLOHOSP.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",

    "TITAN": "TITAN.NS",
    "NESTLEIND": "NESTLEIND.NS",

    "BEL": "BEL.NS",
    "HAL": "HAL.NS",

    "IRFC": "IRFC.NS",
    "IREDA": "IREDA.NS",

    "ETERNAL": "ETERNAL.NS",

    "TRENT": "TRENT.NS",
    "EICHERMOT": "EICHERMOT.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS",

    "GRASIM": "GRASIM.NS",
}


# ============================================================
# HELPERS
# ============================================================

def money(value):
    try:
        return f"₹{float(value):,.2f}"
    except Exception:
        return "—"


def percentage(value):
    try:
        return f"{float(value):+.2f}%"
    except Exception:
        return "—"


def safe_float(value, default=0.0):
    try:
        value = float(value)
        if np.isnan(value) or np.isinf(value):
            return default
        return value
    except Exception:
        return default


# ============================================================
# DOWNLOAD SINGLE STOCK
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def download_stock(symbol):
    """
    Download one stock from Yahoo Finance.

    Returns:
        pandas.DataFrame
    """

    try:
        df = yf.download(
            symbol,
            period="6mo",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # yfinance can return MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df.columns = df.columns.get_level_values(0)
            except Exception:
                df.columns = [
                    str(col[0]) if isinstance(col, tuple) else str(col)
                    for col in df.columns
                ]

        df = df.copy()

        if "Close" not in df.columns:
            return pd.DataFrame()

        df["Close"] = pd.to_numeric(
            df["Close"],
            errors="coerce"
        )

        df = df.dropna(subset=["Close"])

        return df

    except Exception:
        return pd.DataFrame()


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

def calculate_analysis(df):
    if df is None or df.empty:
        return None

    if "Close" not in df.columns:
        return None

    close = pd.to_numeric(
        df["Close"],
        errors="coerce"
    ).dropna()

    if len(close) < 30:
        return None

    try:
        current = safe_float(close.iloc[-1])
        previous = safe_float(close.iloc[-2])

        if previous == 0:
            return None

        # ----------------------------------------------------
        # DAILY RETURN
        # ----------------------------------------------------

        day_return = (
            (current - previous) / previous
        ) * 100

        # ----------------------------------------------------
        # SMA
        # ----------------------------------------------------

        sma20 = safe_float(
            close.rolling(20).mean().iloc[-1]
        )

        sma50 = safe_float(
            close.rolling(50).mean().iloc[-1]
        )

        # ----------------------------------------------------
        # RSI
        # ----------------------------------------------------

        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)

        rsi_series = 100 - (
            100 / (1 + rs)
        )

        rsi = safe_float(
            rsi_series.iloc[-1],
            50.0
        )

        if rsi == 0:
            rsi = 50.0

        rsi = max(0.0, min(100.0, rsi))

        # ----------------------------------------------------
        # MOMENTUM
        # ----------------------------------------------------

        momentum_5d = (
            current / safe_float(close.iloc[-6], current) - 1
        ) * 100

        momentum_20d = (
            current / safe_float(close.iloc[-21], current) - 1
        ) * 100

        # ----------------------------------------------------
        # VOLATILITY
        # ----------------------------------------------------

        returns = close.pct_change()

        volatility = safe_float(
            returns.rolling(20).std().iloc[-1] * 100,
            0.0
        )

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = 50.0

        if current > sma20:
            score += 10
        else:
            score -= 10

        if current > sma50:
            score += 10
        else:
            score -= 10

        if rsi > 55:
            score += 8
        elif rsi < 45:
            score -= 8

        if momentum_5d > 0:
            score += 7
        else:
            score -= 7

        if momentum_20d > 0:
            score += 8
        else:
            score -= 8

        score = max(10, min(90, score))

        # ----------------------------------------------------
        # EXPECTED RETURN
        # ----------------------------------------------------

        trend_component = momentum_20d * 0.35
        short_component = momentum_5d * 0.25

        expected_return = (
            trend_component +
            short_component
        )

        expected_return = max(
            -12,
            min(15, expected_return)
        )

        estimated_price = (
            current *
            (1 + expected_return / 100)
        )

        # ----------------------------------------------------
        # SIGNAL
        # ----------------------------------------------------

        if score >= 65:
            signal = "BUY"
        elif score <= 35:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "current": current,
            "previous": previous,
            "day_return": day_return,
            "estimated": estimated_price,
            "expected_return": expected_return,
            "confidence": score,
            "signal": signal,
            "sma20": sma20,
            "sma50": sma50,
            "rsi": rsi,
            "volatility": volatility,
            "momentum_5d": momentum_5d,
            "momentum_20d": momentum_20d,
            "history": df,
        }

    except Exception:
        return None


# ============================================================
# LOAD ALL STOCKS
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def load_all_stocks():
    rows = []

    for name, symbol in STOCKS.items():

        df = download_stock(symbol)

        analysis = calculate_analysis(df)

        if analysis is None:
            continue

        rows.append({
            "Stock": name,
            "Symbol": symbol,
            "Current Price": analysis["current"],
            "Estimated Price": analysis["estimated"],
            "Expected Return": analysis["expected_return"],
            "Signal": analysis["signal"],
            "Confidence": analysis["confidence"],
            "Live Return": analysis["day_return"],
            "RSI": analysis["rsi"],
            "SMA20": analysis["sma20"],
            "SMA50": analysis["sma50"],
            "Momentum 5D": analysis["momentum_5d"],
            "Momentum 20D": analysis["momentum_20d"],
            "Volatility": analysis["volatility"],
        })

    result = pd.DataFrame(rows)

    if not result.empty:
        result = result.sort_values(
            "Expected Return",
            ascending=False
        ).reset_index(drop=True)

    return result


# ============================================================
# NEWS
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_news(symbol):
    try:
        ticker = yf.Ticker(symbol)

        raw_news = ticker.news

        if not raw_news:
            return []

        results = []

        for item in raw_news[:8]:

            content = item.get("content", {})

            if not isinstance(content, dict):
                content = {}

            title = (
                content.get("title")
                or item.get("title")
                or "Market News"
            )

            publisher = "News"

            provider = content.get("provider", {})

            if isinstance(provider, dict):
                publisher = (
                    provider.get("displayName")
                    or provider.get("name")
                    or "News"
                )

            results.append({
                "title": str(title),
                "publisher": str(publisher),
            })

        return results

    except Exception:
        return []


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
# REFRESH
# ============================================================

refresh_col, update_col = st.columns([1, 5])

with refresh_col:

    if st.button(
        "🔄 Refresh Data",
        use_container_width=True
    ):
        st.cache_data.clear()
        st.rerun()


with update_col:

    st.markdown(
        f"""
        <div class="updated-text">
            Last checked:
            <b>{datetime.now().strftime("%d-%m-%Y %H:%M:%S")}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MARKET STOCK CHIPS
# ============================================================

st.markdown(
    '<div class="section-title">📌 Market Stocks</div>',
    unsafe_allow_html=True,
)

chip_html = '<div class="stock-scroll">' 

for stock in list(STOCKS.keys())[:14]:

    chip_html += f"""
        <div class="stock-chip">
            {stock}
        </div>
    """

chip_html += "</div>"

st.markdown(
    chip_html,
    unsafe_allow_html=True,
)

# ============================================================
# STOCK SELECTOR
# ============================================================

selected_stock = st.selectbox(
    "Select stock",
    list(STOCKS.keys()),
)


# ============================================================
# NAVIGATION
# ============================================================

page = st.radio(
    "Navigation",
    [
        "🏠 Home",
        "📊 All Listed Stocks",
        "🔍 Stock Analysis",
    ],
    horizontal=True,
    label_visibility="collapsed",
)


st.divider()


# ============================================================
# LOAD DATA
# ============================================================

with st.spinner("Loading market data..."):
    all_df = load_all_stocks()


# ============================================================
# DATA ERROR
# ============================================================

if all_df.empty:

    st.error(
        "Market data load avvatledu."
    )

    st.info(
        "Yahoo Finance connection check cheyyandi. "
        "CMD lo TCS.NS test successful ayithe "
        "Refresh Data click cheyyandi."
    )

    st.stop()


# ============================================================
# HOME PAGE
# ============================================================

if page == "🏠 Home":

    st.markdown(
        '<div class="section-title">🔥 Top Stocks For Today</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Highest analytical expected return → lowest expected return"
    )

    top_df = all_df.head(9)

    for start in range(0, len(top_df), 3):

        cols = st.columns(3)

        batch = top_df.iloc[
            start:start + 3
        ]

        for col, (_, row) in zip(
            cols,
            batch.iterrows()
        ):

            signal = str(row["Signal"])

            signal_class = signal.lower()

            expected_class = (
                "return-positive"
                if row["Expected Return"] >= 0
                else "return-negative"
            )

            live_class = (
                "return-positive"
                if row["Live Return"] >= 0
                else "return-negative"
            )

            with col:

                st.markdown(
                    f"""
                    <div class="top-card">

                        <div class="card-top-row">

                            <h3>
                                {row["Stock"]}
                            </h3>

                            <span class="signal {signal_class}">
                                {signal}
                            </span>

                        </div>

                        <div class="small">
                            Live Market Return
                        </div>

                        <div class="metric-value {live_class}">
                            {row["Live Return"]:+.2f}%
                        </div>

                        <div class="price-grid">

                            <div>
                                <span class="metric-title">
                                    Current Price
                                </span>

                                <strong>
                                    ₹{row["Current Price"]:,.2f}
                                </strong>
                            </div>

                            <div>
                                <span class="metric-title">
                                    Estimated Price
                                </span>

                                <strong>
                                    ₹{row["Estimated Price"]:,.2f}
                                </strong>
                            </div>

                        </div>

                        <div class="expected-box">

                            <span>
                                Expected Return
                            </span>

                            <b class="{expected_class}">
                                {row["Expected Return"]:+.2f}%
                            </b>

                        </div>

                        <div class="confidence-row">

                            <span>
                                Confidence
                            </span>

                            <b>
                                {row["Confidence"]:.0f}%
                            </b>

                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )


    # ========================================================
    # RANKING
    # ========================================================

    st.markdown(
        '<div class="section-title">📊 Today\'s Ranking</div>',
        unsafe_allow_html=True,
    )

    ranking_df = all_df[
        [
            "Stock",
            "Current Price",
            "Estimated Price",
            "Expected Return",
            "Signal",
            "Confidence",
            "Live Return",
        ]
    ].copy()

    ranking_df.columns = [
        "Stock",
        "Current Price",
        "Estimated Price",
        "Expected Return",
        "Signal",
        "Confidence",
        "Live Return",
    ]

    st.dataframe(
        ranking_df.style.format({
            "Current Price": "₹{:,.2f}",
            "Estimated Price": "₹{:,.2f}",
            "Expected Return": "{:+.2f}%",
            "Confidence": "{:.0f}%",
            "Live Return": "{:+.2f}%",
        }),
        use_container_width=True,
        hide_index=True,
        height=500,
    )


# ============================================================
# ALL LISTED STOCKS
# ============================================================

elif page == "📊 All Listed Stocks":

    st.markdown(
        '<div class="section-title">📋 All Listed Stocks</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Stocks successfully received from Yahoo Finance"
    )

    search = st.text_input(
        "Search stock",
        placeholder="Search TCS, INFY, RELIANCE..."
    )

    display_df = all_df.copy()

    if search.strip():

        search_upper = search.strip().upper()

        display_df = display_df[
            display_df["Stock"]
            .str.upper()
            .str.contains(
                search_upper,
                na=False
            )
        ]

    display_df = display_df[
        [
            "Stock",
            "Current Price",
            "Estimated Price",
            "Expected Return",
            "Signal",
            "Confidence",
            "Live Return",
            "RSI",
            "SMA20",
            "SMA50",
        ]
    ]

    st.dataframe(
        display_df.style.format({
            "Current Price": "₹{:,.2f}",
            "Estimated Price": "₹{:,.2f}",
            "Expected Return": "{:+.2f}%",
            "Confidence": "{:.0f}%",
            "Live Return": "{:+.2f}%",
            "RSI": "{:.1f}",
            "SMA20": "₹{:,.2f}",
            "SMA50": "₹{:,.2f}",
        }),
        use_container_width=True,
        hide_index=True,
        height=600,
    )


# ============================================================
# STOCK ANALYSIS
# ============================================================

elif page == "🔍 Stock Analysis":

    symbol = STOCKS[selected_stock]

    st.markdown(
        f"""
        <div class="section-title">
            🔍 {selected_stock} — Stock Analysis
        </div>
        """,
        unsafe_allow_html=True,
    )

    df = download_stock(symbol)

    analysis = calculate_analysis(df)

    if analysis is None:

        st.error(
            f"Data available kaaledu for {selected_stock}."
        )

        st.stop()


    current = analysis["current"]
    estimated = analysis["estimated"]
    expected_return = analysis["expected_return"]
    signal = analysis["signal"]
    confidence = analysis["confidence"]
    live_return = analysis["day_return"]
    rsi = analysis["rsi"]
    sma20 = analysis["sma20"]
    sma50 = analysis["sma50"]
    momentum5 = analysis["momentum_5d"]
    momentum20 = analysis["momentum_20d"]
    volatility = analysis["volatility"]


    # ========================================================
    # MAIN METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(
            f"""
            <div class="analysis-box">

                <div class="metric-title">
                    Current Price
                </div>

                <div class="big-number">
                    ₹{current:,.2f}
                </div>

                <div class="small">
                    Live / latest available
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with c2:

        st.markdown(
            f"""
            <div class="analysis-box">

                <div class="metric-title">
                    Estimated Price
                </div>

                <div class="big-number">
                    ₹{estimated:,.2f}
                </div>

                <div class="small">
                    Analytical estimate
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with c3:

        signal_class = signal.lower()

        st.markdown(
            f"""
            <div class="analysis-box">

                <div class="metric-title">
                    Signal
                </div>

                <div class="big-number signal {signal_class}">
                    {signal}
                </div>

                <div class="small">
                    Technical score based
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with c4:

        confidence_class = (
            "return-positive"
            if confidence >= 60
            else "return-negative"
        )

        st.markdown(
            f"""
            <div class="analysis-box">

                <div class="metric-title">
                    Confidence
                </div>

                <div class="big-number {confidence_class}">
                    {confidence:.0f}%
                </div>

                <div class="small">
                    Analytical confidence
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # RETURNS
    # ========================================================

    st.markdown(
        '<div class="section-title">📈 Returns & Forecast</div>',
        unsafe_allow_html=True,
    )

    r1, r2, r3 = st.columns(3)

    live_class = (
        "return-positive"
        if live_return >= 0
        else "return-negative"
    )

    expected_class = (
        "return-positive"
        if expected_return >= 0
        else "return-negative"
    )

    with r1:

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    Today's Return
                </div>

                <div class="metric-value {live_class}">
                    {live_return:+.2f}%
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with r2:

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    Expected Return
                </div>

                <div class="metric-value {expected_class}">
                    {expected_return:+.2f}%
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with r3:

        price_difference = estimated - current

        price_class = (
            "return-positive"
            if price_difference >= 0
            else "return-negative"
        )

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    Expected Price Change
                </div>

                <div class="metric-value {price_class}">
                    ₹{price_difference:+,.2f}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # CHART
    # ========================================================

    st.markdown(
        '<div class="section-title">📊 Price Chart</div>',
        unsafe_allow_html=True,
    )

    history = analysis["history"].copy()

    chart_df = history[["Close"]].copy()

    chart_df["SMA20"] = (
        chart_df["Close"]
        .rolling(20)
        .mean()
    )

    chart_df["SMA50"] = (
        chart_df["Close"]
        .rolling(50)
        .mean()
    )

    chart_df = chart_df.dropna(
        subset=["Close"]
    )

    st.line_chart(
        chart_df[
            ["Close", "SMA20", "SMA50"]
        ],
        use_container_width=True,
    )


    # ========================================================
    # TECHNICAL INDICATORS
    # ========================================================

    st.markdown(
        '<div class="section-title">⚙️ Technical Indicators</div>',
        unsafe_allow_html=True,
    )

    t1, t2, t3, t4 = st.columns(4)

    with t1:

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    RSI (14)
                </div>

                <div class="metric-value">
                    {rsi:.1f}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with t2:

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    SMA 20
                </div>

                <div class="metric-value">
                    ₹{sma20:,.2f}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with t3:

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    SMA 50
                </div>

                <div class="metric-value">
                    ₹{sma50:,.2f}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with t4:

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    Volatility
                </div>

                <div class="metric-value">
                    {volatility:.2f}%
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # MOMENTUM
    # ========================================================

    st.markdown(
        '<div class="section-title">🚀 Momentum</div>',
        unsafe_allow_html=True,
    )

    m1, m2 = st.columns(2)

    momentum5_class = (
        "return-positive"
        if momentum5 >= 0
        else "return-negative"
    )

    momentum20_class = (
        "return-positive"
        if momentum20 >= 0
        else "return-negative"
    )

    with m1:

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    5 Day Momentum
                </div>

                <div class="metric-value {momentum5_class}">
                    {momentum5:+.2f}%
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with m2:

        st.markdown(
            f"""
            <div class="info-box">

                <div class="metric-title">
                    20 Day Momentum
                </div>

                <div class="metric-value {momentum20_class}">
                    {momentum20:+.2f}%
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # NEWS
    # ========================================================

    st.markdown(
        '<div class="section-title">📰 Latest News</div>',
        unsafe_allow_html=True,
    )

    news = get_news(symbol)

    if news:

        for item in news:

            title = item["title"]
            publisher = item["publisher"]

            st.markdown(
                f"""
                <div class="news-card">

                    <div class="news-title">
                        {title}
                    </div>

                    <div class="muted">
                        {publisher}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    else:

        st.info(
            "News currently available kaaledu."
        )


# ============================================================
# DISCLAIMER
# ============================================================

st.markdown(
    """
    <div class="disclaimer">

        <b>Disclaimer:</b>
        SMA analytical estimates are generated from historical
        market data and technical indicators. They are not guaranteed
        predictions and should not be treated as financial advice.
        Always perform your own research before making investment
        decisions.

    </div>
    """,
    unsafe_allow_html=True,
)