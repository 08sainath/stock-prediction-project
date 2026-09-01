import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# -----------------------------
# Stock configuration
# -----------------------------
STOCK_OPTIONS = {
    "AAPL": ("Apple Inc. (NASDAQ)", "AAPL"),
    "TCS": ("Tata Consultancy Services (NSE)", "TCS.NS"),
    "NIFTY50": ("NIFTY 50 Index (NSE)", "^NSEI"),
}

st.set_page_config(
    page_title="Real-Time Stock Market Analysis & Prediction",
    page_icon="📈",
    layout="wide",
)

# -----------------------------
# CSS
# -----------------------------
def load_css():
    css = """
    <style>
    .metric-card {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,.25);
        margin-bottom: 10px;
    }
    .signal {
        font-size: 28px;
        font-weight: 800;
        padding: 12px 18px;
        border-radius: 12px;
        text-align: center;
    }
    .small { color: #777; font-size: 13px; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_css()

# -----------------------------
# Yahoo Finance chart API
# -----------------------------
@st.cache_data(ttl=60)
def get_market_data(symbol, period="6mo", interval="1d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "range": period,
        "interval": interval,
        "includePrePost": "false",
        "events": "div,splits",
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()

    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]

    df = pd.DataFrame({
        "Date": pd.to_datetime(timestamps, unit="s"),
        "Open": quote.get("open", []),
        "High": quote.get("high", []),
        "Low": quote.get("low", []),
        "Close": quote.get("close", []),
        "Volume": quote.get("volume", []),
    })

    df = df.dropna(subset=["Close"]).set_index("Date")
    return df

# -----------------------------
# Indicators
# -----------------------------
def add_indicators(df):
    df = df.copy()

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACDSignal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["Return1D"] = df["Close"].pct_change()
    df["Momentum5D"] = df["Close"].pct_change(5)

    return df.dropna()

# -----------------------------
# Simple explainable prediction
# NOTE: This is a technical-signal model, not a guaranteed ML forecast.
# -----------------------------
def make_prediction(df):
    last = df.iloc[-1]
    score = 0.0
    reasons = []

    if last["Close"] > last["EMA20"]:
        score += 1.0
        reasons.append("Price above EMA20")
    else:
        score -= 1.0
        reasons.append("Price below EMA20")

    if last["EMA20"] > last["EMA50"]:
        score += 1.0
        reasons.append("EMA20 above EMA50")
    else:
        score -= 1.0
        reasons.append("EMA20 below EMA50")

    if last["MACD"] > last["MACDSignal"]:
        score += 1.0
        reasons.append("MACD bullish")
    else:
        score -= 1.0
        reasons.append("MACD bearish")

    if last["RSI"] < 30:
        score += 0.5
        reasons.append("RSI oversold")
    elif last["RSI"] > 70:
        score -= 0.5
        reasons.append("RSI overbought")
    elif last["RSI"] >= 50:
        score += 0.5
        reasons.append("RSI above 50")
    else:
        score -= 0.5
        reasons.append("RSI below 50")

    if last["Momentum5D"] > 0:
        score += 0.5
        reasons.append("5-day momentum positive")
    else:
        score -= 0.5
        reasons.append("5-day momentum negative")

    if score >= 2:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Heuristic confidence, intentionally capped.
    confidence = min(95, max(50, 50 + abs(score) / 4.5 * 45))

    # Small next-session estimate based on recent momentum + signal.
    recent_vol = float(df["Return1D"].tail(20).std() or 0.01)
    expected_move = np.clip(
        (score / 5.0) * max(recent_vol, 0.003),
        -0.08,
        0.08,
    )
    predicted_price = float(last["Close"] * (1 + expected_move))

    return signal, confidence, predicted_price, reasons

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## 📌 Select Stock")
    selected_stock = st.selectbox(
        "Stock Symbol",
        list(STOCK_OPTIONS.keys()),
        format_func=lambda x: f"{x} — {STOCK_OPTIONS[x][0]}",
    )

    period = st.selectbox(
        "Historical Data",
        ["1mo", "3mo", "6mo", "1y", "2y"],
        index=2,
    )

    refresh = st.button("🔄 Refresh Data", use_container_width=True)

    if refresh:
        st.cache_data.clear()
        st.rerun()

# -----------------------------
# Main
# -----------------------------
display_name, yahoo_symbol = STOCK_OPTIONS[selected_stock]

st.title("📈 Real-Time Stock Market Analysis & Prediction System")
st.caption(
    "Live market data + explainable technical analysis. "
    "Prediction is an analytical estimate, not a guaranteed future price."
)

try:
    raw = get_market_data(yahoo_symbol, period=period, interval="1d")
    df = add_indicators(raw)

    if len(df) < 60:
        st.warning("Not enough historical data was returned for reliable indicators.")
        st.stop()

    signal, confidence, predicted_price, reasons = make_prediction(df)

    last = df.iloc[-1]
    previous_close = float(df["Close"].iloc[-2])
    current_price = float(last["Close"])
    change = current_price - previous_close
    change_pct = change / previous_close * 100

    # Header
    st.subheader(f"{selected_stock} — {display_name}")
    st.caption(
        f"Last available market candle: "
        f"{df.index[-1].strftime('%Y-%m-%d %H:%M')} | Symbol: {yahoo_symbol}"
    )

    # Metrics
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Current Price",
        f"{current_price:,.2f}",
        f"{change:+,.2f} ({change_pct:+.2f}%)",
    )

    c2.metric(
        "Estimated Next Price",
        f"{predicted_price:,.2f}",
        f"{(predicted_price/current_price-1)*100:+.2f}%",
    )

    c3.metric("Signal", signal)
    c4.metric("Confidence", f"{confidence:.0f}%")

    st.divider()

    # Signal banner
    st.markdown(
        f'<div class="signal">Signal: {signal} &nbsp; | &nbsp; '
        f'Confidence: {confidence:.0f}%</div>',
        unsafe_allow_html=True,
    )

    st.write("")

    left, right = st.columns([2, 1])

    with left:
        st.subheader("📊 Price & Trend")

        chart_df = df[["Close", "EMA20", "EMA50"]].tail(120)
        st.line_chart(chart_df, use_container_width=True)

    with right:
        st.subheader("🧠 Analysis")

        st.write("**Indicators**")
        st.write(f"RSI: **{last['RSI']:.2f}**")
        st.write(f"EMA20: **{last['EMA20']:.2f}**")
        st.write(f"EMA50: **{last['EMA50']:.2f}**")
        st.write(f"MACD: **{last['MACD']:.4f}**")
        st.write(f"5D Momentum: **{last['Momentum5D']*100:.2f}%**")

        st.write("**Why this signal?**")
        for reason in reasons:
            st.write(f"• {reason}")

    st.divider()

    a, b = st.columns(2)

    with a:
        st.subheader("📈 Recent Market Data")
        view = df[["Open", "High", "Low", "Close", "Volume"]].tail(10).copy()
        st.dataframe(view, use_container_width=True)

    with b:
        st.subheader("⚠️ Risk Notes")
        st.info(
            "This dashboard provides an analytical signal based on recent "
            "price/technical data. It is not a guaranteed prediction and "
            "should not be treated as financial advice."
        )
        st.write(
            "For live intraday trading, use an authorised broker/data feed. "
            "Yahoo Finance data can be delayed and may not represent tick-by-tick prices."
        )

except requests.exceptions.RequestException as e:
    st.error("Unable to fetch market data.")
    st.code(str(e))
    st.info(
        "Check your internet connection and try the 🔄 Refresh Data button."
    )

except Exception as e:
    st.error("Dashboard could not process the selected stock.")
    st.code(f"{type(e).__name__}: {e}")
    st.info(
        "The error is shown above so it can be fixed without hiding the real cause."
    )
