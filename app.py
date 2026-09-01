import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Real-Time Stock Market",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
    "LT": "LT.NS",
    "ITC": "ITC.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "MARUTI": "MARUTI.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "ADANIENT": "ADANIENT.NS",
    "ADANIPORTS": "ADANIPORTS.NS",
    "NTPC": "NTPC.NS",
    "POWERGRID": "POWERGRID.NS",
    "ONGC": "ONGC.NS",
    "COALINDIA": "COALINDIA.NS",
    "JSWSTEEL": "JSWSTEEL.NS",
    "HCLTECH": "HCLTECH.NS",
    "TECHM": "TECHM.NS",
    "DRREDDY": "DRREDDY.NS",
    "CIPLA": "CIPLA.NS",
    "APOLLOHOSP": "APOLLOHOSP.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "TITAN": "TITAN.NS",
    "NESTLEIND": "NESTLEIND.NS",
    "BEL": "BEL.NS",
    "HAL": "HAL.NS",
    "IRFC": "IRFC.NS",
    "IREDA": "IREDA.NS",
    "ZOMATO": "ZOMATO.NS",
    "TRENT": "TRENT.NS",
    "M&M": "M&M.NS",
    "EICHERMOT": "EICHERMOT.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS",
    "INDUSINDBK": "INDUSINDBK.NS",
    "GRASIM": "GRASIM.NS",
    "BPCL": "BPCL.NS",
    "HINDALCO": "HINDALCO.NS",
    "TATACONSUM": "TATACONSUM.NS",
}

INDEXES = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN"
}

# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

.main {
    padding-top: 1rem;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
}

.hero {
    padding: 25px;
    border-radius: 20px;
    background: linear-gradient(135deg, #111827, #1f2937);
    color: white;
    margin-bottom: 20px;
}

.hero h1 {
    margin-bottom: 5px;
    font-size: 38px;
}

.hero p {
    color: #cbd5e1;
}

.stock-card {
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 18px;
    background: white;
    margin-bottom: 14px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.05);
}

.top-card {
    border-radius: 18px;
    padding: 18px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    min-height: 190px;
}

.metric-title {
    font-size: 13px;
    color: #64748b;
}

.metric-value {
    font-size: 23px;
    font-weight: 700;
}

.buy {
    color: #16a34a;
    font-weight: 800;
}

.sell {
    color: #dc2626;
    font-weight: 800;
}

.hold {
    color: #d97706;
    font-weight: 800;
}

.small {
    color: #64748b;
    font-size: 13px;
}

.section-title {
    font-size: 27px;
    font-weight: 800;
    margin-top: 25px;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA FUNCTIONS
# ============================================================

@st.cache_data(ttl=60)
def get_stock_data(symbol):

    try:
        ticker = yf.Ticker(symbol)

        df = ticker.history(
            period="6mo",
            interval="1d",
            auto_adjust=False
        )

        if df.empty:
            return None

        df = df.dropna()

        close = df["Close"]

        current = float(close.iloc[-1])
        previous = float(close.iloc[-2])

        day_return = ((current - previous) / previous) * 100

        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])

        # RSI
        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)

        rsi = 100 - (100 / (1 + rs))
        rsi_value = float(rsi.iloc[-1])

        # Volatility
        returns = close.pct_change()

        volatility = float(
            returns.rolling(20).std().iloc[-1] * 100
        )

        # Momentum
        momentum_5d = (
            (current / float(close.iloc[-6])) - 1
        ) * 100

        momentum_20d = (
            (current / float(close.iloc[-21])) - 1
        ) * 100

        # ====================================================
        # SIMPLE ANALYTICAL ESTIMATE
        # ====================================================

        score = 50

        if current > sma20:
            score += 10
        else:
            score -= 10

        if current > sma50:
            score += 10
        else:
            score -= 10

        if rsi_value > 55:
            score += 8
        elif rsi_value < 45:
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

        # Expected return
        trend_component = momentum_20d * 0.35
        short_component = momentum_5d * 0.25

        expected_return = (
            trend_component +
            short_component
        )

        # Keep estimate reasonable
        expected_return = max(
            -12,
            min(15, expected_return)
        )

        estimated_price = current * (
            1 + expected_return / 100
        )

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
            "rsi": rsi_value,
            "volatility": volatility,
            "momentum_5d": momentum_5d,
            "momentum_20d": momentum_20d,
            "history": df
        }

    except Exception as e:
        return None


# ============================================================
# NEWS
# ============================================================

@st.cache_data(ttl=300)
def get_news(symbol):

    try:

        ticker = yf.Ticker(symbol)

        news = ticker.news

        results = []

        for item in news[:8]:

            content = item.get("content", {})

            title = content.get("title")

            if not title:
                title = item.get("title", "News")

            publisher = content.get(
                "provider",
                {}
            ).get(
                "displayName",
                "News"
            )

            results.append({
                "title": title,
                "publisher": publisher
            })

        return results

    except Exception:
        return []


# ============================================================
# LOAD ALL DATA
# ============================================================

@st.cache_data(ttl=60)
def load_all_stocks():

    rows = []

    for name, symbol in STOCKS.items():

        data = get_stock_data(symbol)

        if data:

            rows.append({
                "Stock": name,
                "Symbol": symbol,
                "Current Price": data["current"],
                "Estimated Price": data["estimated"],
                "Expected Return": data["expected_return"],
                "Signal": data["signal"],
                "Confidence": data["confidence"],
                "Live Return": data["day_return"],
                "RSI": data["rsi"],
                "SMA20": data["sma20"],
                "SMA50": data["sma50"],
                "Momentum 5D": data["momentum_5d"],
                "Momentum 20D": data["momentum_20d"],
                "Volatility": data["volatility"]
            })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(
            "Expected Return",
            ascending=False
        )

    return df


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="hero">

<h1>📈 Real-Time Stock Market</h1>

<p>
Analysis • Prediction • Market Returns • News • Technical Behaviour
</p>

</div>
""", unsafe_allow_html=True)


# ============================================================
# REFRESH
# ============================================================

col1, col2, col3 = st.columns([1, 1, 5])

with col1:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

with col2:
    st.caption(
        "Updated: " +
        datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )


# ============================================================
# TOP STOCK HORIZONTAL SCROLL
# ============================================================

st.markdown(
    '<div class="section-title">📌 Stocks</div>',
    unsafe_allow_html=True
)

stock_names = list(STOCKS.keys())

selected_stock = st.selectbox(
    "Select stock",
    stock_names,
    label_visibility="collapsed"
)


# ============================================================
# NAVIGATION
# ============================================================

page = st.radio(
    "Navigation",
    [
        "🏠 Home",
        "📊 All Stocks",
        "🔍 Stock Analysis"
    ],
    horizontal=True
)

st.divider()


# ============================================================
# GET ALL DATA
# ============================================================

all_df = load_all_stocks()


if all_df.empty:

    st.error(
        "Market data load avvatledu. "
        "Internet connection / Yahoo Finance availability check cheyyandi."
    )

    st.stop()


# ============================================================
# PAGE 1
# ============================================================

if page == "🏠 Home":

    st.markdown(
        '<div class="section-title">🔥 Top Stocks For Today</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Highest analytical expected return → lowest expected return"
    )

    top_df = all_df.head(10)

    for start in range(0, len(top_df), 3):

        cols = st.columns(3)

        batch = top_df.iloc[start:start + 3]

        for col, (_, row) in zip(cols, batch.iterrows()):

            signal_class = row["Signal"].lower()

            with col:

                st.markdown(
                    f"""
                    <div class="top-card">

                    <h3>{row['Stock']}</h3>

                    <div class="small">
                    Live market return
                    </div>

                    <div class="metric-value">
                    {row['Live Return']:+.2f}%
                    </div>

                    <hr>

                    <div>
                    Current:
                    <b>₹{row['Current Price']:,.2f}</b>
                    </div>

                    <div>
                    Estimated:
                    <b>₹{row['Estimated Price']:,.2f}</b>
                    </div>

                    <div>
                    Expected:
                    <b>{row['Expected Return']:+.2f}%</b>
                    </div>

                    <br>

                    <span class="{signal_class}">
                    {row['Signal']}
                    </span>

                    &nbsp;&nbsp;

                    Confidence:
                    <b>{row['Confidence']:.0f}%</b>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

    st.markdown(
        '<div class="section-title">📈 Today's Ranking</div>',
        unsafe_allow_html=True
    )

    display_df = all_df[
        [
            "Stock",
            "Current Price",
            "Estimated Price",
            "Signal",
            "Confidence",
            "Live Return"
        ]
    ].copy()

    display_df.columns = [
        "Stock",
        "Current Price",
        "Estimated Price",
        "Signal",
        "Confidence",
        "Live Market Return"
    ]

    st.dataframe(
        display_df.style.format({
            "Current Price": "₹{:,.2f}",
            "Estimated Price": "₹{:,.2f}",
            "Confidence": "{:.0f}%",
            "Live Market Return": "{:+.2f}%"
        }),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PAGE 2
# ============================================================

elif page == "📊 All Stocks":

    st.markdown(
        '<div class="section-title">📊 All Listed Stocks</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Sorted from highest expected return to lowest expected return"
    )

    display_df = all_df[
        [
            "Stock",
            "Current Price",
            "Estimated Price",
            "Confidence"
        ]
    ].copy()

    display_df.columns = [
        "Stock",
        "Current Price",
        "Estimated Price",
        "Confidence"
    ]

    st.dataframe(
        display_df.style.format({
            "Current Price": "₹{:,.2f}",
            "Estimated Price": "₹{:,.2f}",
            "Confidence": "{:.0f}%"
        }),
        use_container_width=True,
        height=650,
        hide_index=True
    )


# ============================================================
# PAGE 3
# ============================================================

elif page == "🔍 Stock Analysis":

    st.markdown(
        '<div class="section-title">🔍 Detailed Stock Analysis</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:

        stock1 = st.selectbox(
            "Select Stock 1",
            stock_names,
            index=stock_names.index(selected_stock)
        )

    with c2:

        stock2_options = [
            "None"
        ] + stock_names

        stock2 = st.selectbox(
            "Select Stock 2 (optional)",
            stock2_options
        )


    selected = [stock1]

    if stock2 != "None" and stock2 != stock1:
        selected.append(stock2)


    for stock_name in selected:

        symbol = STOCKS[stock_name]

        data = get_stock_data(symbol)

        if not data:
            st.warning(
                f"{stock_name} data unavailable."
            )
            continue

        st.divider()

        # ====================================================
        # BASIC SUMMARY
        # ====================================================

        st.markdown(
            f"## 📌 {stock_name}"
        )

        a, b, c, d = st.columns(4)

        with a:
            st.metric(
                "Current Price",
                f"₹{data['current']:,.2f}"
            )

        with b:
            st.metric(
                "Estimated Price",
                f"₹{data['estimated']:,.2f}"
            )

        with c:
            st.metric(
                "Signal",
                data["signal"]
            )

        with d:
            st.metric(
                "Confidence",
                f"{data['confidence']:.0f}%"
            )


        # ====================================================
        # EXPECTED RETURN
        # ====================================================

        st.markdown("### 📈 Expected Return")

        st.progress(
            int(min(100, max(0,
                data["confidence"]
            )))
        )

        st.write(
            f"Analytical expected return: "
            f"**{data['expected_return']:+.2f}%**"
        )

        st.write(
            f"Live market return today: "
            f"**{data['day_return']:+.2f}%**"
        )


        # ====================================================
        # PRICE CHART
        # ====================================================

        st.markdown("### 📊 Price Trend")

        history = data["history"]

        chart_df = history[
            ["Close"]
        ].rename(
            columns={"Close": stock_name}
        )

        st.line_chart(
            chart_df,
            height=350
        )


        # ====================================================
        # TECHNICAL DATA
        # ====================================================

        st.markdown("### ⚙️ Technical Behaviour")

        t1, t2, t3, t4 = st.columns(4)

        with t1:
            st.metric(
                "RSI",
                f"{data['rsi']:.1f}"
            )

        with t2:
            st.metric(
                "SMA 20",
                f"₹{data['sma20']:,.2f}"
            )

        with t3:
            st.metric(
                "SMA 50",
                f"₹{data['sma50']:,.2f}"
            )

        with t4:
            st.metric(
                "Volatility",
                f"{data['volatility']:.2f}%"
            )


        # ====================================================
        # WHY HIGH / LOW?
        # ====================================================

        st.markdown(
            "### 🧠 Why is this stock behaving this way?"
        )

        reasons = []

        if data["current"] > data["sma20"]:
            reasons.append(
                "Price is above the 20-day moving average, "
                "which indicates positive short-term momentum."
            )
        else:
            reasons.append(
                "Price is below the 20-day moving average, "
                "showing weaker short-term momentum."
            )

        if data["current"] > data["sma50"]:
            reasons.append(
                "Price is above the 50-day moving average, "
                "supporting the medium-term trend."
            )
        else:
            reasons.append(
                "Price is below the 50-day moving average, "
                "indicating medium-term weakness."
            )

        if data["rsi"] > 70:
            reasons.append(
                "RSI is above 70, so the stock may be "
                "technically overbought."
            )

        elif data["rsi"] < 30:
            reasons.append(
                "RSI is below 30, so the stock may be "
                "technically oversold."
            )

        elif data["rsi"] >= 55:
            reasons.append(
                "RSI indicates relatively positive momentum."
            )

        else:
            reasons.append(
                "RSI indicates relatively weak/neutral momentum."
            )

        if data["momentum_5d"] > 0:
            reasons.append(
                f"5-day momentum is positive "
                f"({data['momentum_5d']:+.2f}%)."
            )
        else:
            reasons.append(
                f"5-day momentum is negative "
                f"({data['momentum_5d']:+.2f}%)."
            )

        if data["momentum_20d"] > 0:
            reasons.append(
                f"20-day momentum is positive "
                f"({data['momentum_20d']:+.2f}%)."
            )
        else:
            reasons.append(
                f"20-day momentum is negative "
                f"({data['momentum_20d']:+.2f}%)."
            )

        for i, reason in enumerate(reasons, 1):

            st.write(
                f"**{i}.** {reason}"
            )


        # ====================================================
        # NEWS
        # ====================================================

        st.markdow    )
