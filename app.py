import time
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="SMA — Stock Market Analysis", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp{background:#f7f8fa;color:#171717}.block-container{max-width:1450px;padding-top:2rem;padding-bottom:4rem}
.hero{padding:30px;border:1px solid rgba(242,199,110,.25);border-radius:24px;background:#fff;box-shadow:0 12px 40px rgba(0,0,0,.06);margin:20px 0}
.brand{font-size:34px;font-weight:800;letter-spacing:3px;color:#c99a2e}.muted{color:#6b7280}.card{background:#fff;border:1px solid #e5e7eb;border-radius:18px;padding:20px}
.buy{color:#16834b;font-weight:800}.sell{color:#c62838;font-weight:800}.hold{color:#a56a00;font-weight:800}
</style>
""", unsafe_allow_html=True)

STOCKS = {
    "RELIANCE.NS":("RELIANCE","Reliance Industries"), "TCS.NS":("TCS","Tata Consultancy Services"), "INFY.NS":("INFY","Infosys"), "HDFCBANK.NS":("HDFCBANK","HDFC Bank"), "ICICIBANK.NS":("ICICIBANK","ICICI Bank"), "SBIN.NS":("SBIN","State Bank of India"), "ITC.NS":("ITC","ITC Limited"), "BHARTIARTL.NS":("BHARTIARTL","Bharti Airtel"), "LT.NS":("LT","Larsen & Toubro"), "WIPRO.NS":("WIPRO","Wipro"), "HCLTECH.NS":("HCLTECH","HCL Technologies"), "MARUTI.NS":("MARUTI","Maruti Suzuki India"), "SUNPHARMA.NS":("SUNPHARMA","Sun Pharmaceutical"), "TATASTEEL.NS":("TATASTEEL","Tata Steel"), "TATAMOTORS.NS":("TATAMOTORS","Tata Motors"), "BAJFINANCE.NS":("BAJFINANCE","Bajaj Finance"), "AXISBANK.NS":("AXISBANK","Axis Bank"), "KOTAKBANK.NS":("KOTAKBANK","Kotak Mahindra Bank"), "ASIANPAINT.NS":("ASIANPAINT","Asian Paints"), "TITAN.NS":("TITAN","Titan Company"), "ADANIENT.NS":("ADANIENT","Adani Enterprises"), "ADANIPORTS.NS":("ADANIPORTS","Adani Ports"), "NTPC.NS":("NTPC","NTPC Limited"), "POWERGRID.NS":("POWERGRID","Power Grid Corporation"), "ONGC.NS":("ONGC","Oil & Natural Gas Corporation"), "COALINDIA.NS":("COALINDIA","Coal India"), "BEL.NS":("BEL","Bharat Electronics"), "HAL.NS":("HAL","Hindustan Aeronautics"), "IRFC.NS":("IRFC","Indian Railway Finance Corporation"), "IREDA.NS":("IREDA","Indian Renewable Energy Development Agency")
}

INDICES = {"^NSEI":("NIFTY 50","NIFTY 50"), "^NSEBANK":("BANK NIFTY","NIFTY Bank"), "^BSESN":("SENSEX","BSE SENSEX")}


def _number(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except Exception:
        return None


@st.cache_data(ttl=15, show_spinner=False)
def yahoo_chart_quote(ticker):
    """Fallback quote reader using Yahoo's chart endpoint; avoids yfinance ticker/crumb parsing errors."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        response = requests.get(url, params={"range":"1d", "interval":"1m", "includePrePost":"false"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("chart", {}).get("result") or []
        if not result:
            return None
        meta = result[0].get("meta", {})
        price = _number(meta.get("regularMarketPrice"))
        previous = _number(meta.get("previousClose")) or _number(meta.get("chartPreviousClose"))
        high = _number(meta.get("regularMarketDayHigh"))
        low = _number(meta.get("regularMarketDayLow"))
        if price is None:
            quote = (result[0].get("indicators", {}).get("quote") or [{}])[0]
            closes = [x for x in quote.get("close", []) if x is not None]
            if closes:
                price = _number(closes[-1])
        change = price - previous if price is not None and previous else None
        change_pct = change / previous * 100 if change is not None and previous else None
        return {"price":price,"previous":previous,"change":change,"change_pct":change_pct,"high":high,"low":low}
    except Exception:
        return None


@st.cache_data(ttl=15, show_spinner=False)
def get_live_quote(ticker):
    """Use yfinance first, then Yahoo chart API as a reliable fallback."""
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = _number(info.get("last_price"))
        previous = _number(info.get("previous_close"))
        high = _number(info.get("day_high"))
        low = _number(info.get("day_low"))
        if price is not None:
            change = price - previous if previous else None
            change_pct = change / previous * 100 if change is not None and previous else None
            return {"price":price,"previous":previous,"change":change,"change_pct":change_pct,"high":high,"low":low}
    except Exception:
        pass
    return yahoo_chart_quote(ticker)


@st.cache_data(ttl=120, show_spinner=False)
def get_history(ticker, period="1y"):
    try:
        df = yf.download(ticker, period=period, interval="1d", auto_adjust=False, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]
        cols = [c for c in ["open","high","low","close","volume"] if c in df.columns]
        return df[cols].dropna(subset=["close"])
    except Exception:
        return pd.DataFrame()


def rsi(series, period=14):
    delta = series.diff(); gain = delta.clip(lower=0).rolling(period).mean(); loss = (-delta.clip(upper=0)).rolling(period).mean(); rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def indicators(df):
    df = df.copy(); df["sma20"] = df.close.rolling(20).mean(); df["sma50"] = df.close.rolling(50).mean(); df["rsi"] = rsi(df.close); df["momentum20"] = df.close.pct_change(20) * 100; df["volatility"] = df.close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    return df


def signal(df):
    if df.empty: return "HOLD"
    last = df.iloc[-1]; score = 0
    if pd.notna(last.sma20): score += 1 if last.close > last.sma20 else -1
    if pd.notna(last.sma50): score += 1 if last.close > last.sma50 else -1
    if pd.notna(last.rsi):
        if last.rsi < 35: score += 2
        elif last.rsi > 70: score -= 2
    return "BUY" if score >= 2 else "SELL" if score <= -2 else "HOLD"


def money(v): return "₹—" if v is None else f"₹{v:,.2f}"

st.markdown('<div class="brand">SMA</div><div class="muted">STOCK MARKET ANALYSIS · INDIAN MARKETS</div>', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>Indian Stock Market Analysis</h1><p class="muted">Live NSE prices from Yahoo Finance, technical indicators and estimated price analysis.</p></div>', unsafe_allow_html=True)
page = st.radio("Navigation", ["Market Overview", "Stock Analysis", "All Stocks"], horizontal=True, label_visibility="collapsed")

st.subheader("Live Market")
cols = st.columns(3)
for col, (ticker, (symbol, name)) in zip(cols, INDICES.items()):
    q = get_live_quote(ticker)
    with col:
        if q and q.get("price") is not None:
            cls = "buy" if (q.get("change_pct") or 0) >= 0 else "sell"
            change_text = f'{q["change_pct"]:+.2f}%' if q.get("change_pct") is not None else "—"
            st.markdown(f'<div class="card"><b>{symbol}</b><br><span style="font-size:28px;font-weight:800">{money(q["price"])}</span><br><span class="{cls}">{change_text}</span> today</div>', unsafe_allow_html=True)
        else:
            st.warning(f"{symbol}: Yahoo Finance data temporarily unavailable")

st.caption("Yahoo Finance data is refreshed every 15 seconds. Yahoo may occasionally return temporary empty responses; SMA retries through Yahoo's chart endpoint.")

if page == "Market Overview":
    st.subheader("Market Status")
    st.info("Live quotes are fetched from Yahoo Finance. If Yahoo temporarily blocks a request, the page will retry automatically.")

elif page == "Stock Analysis":
    labels = {f"{v[0]} — {v[1]}": k for k,v in STOCKS.items()}
    selected_label = st.selectbox("Select NSE stock", list(labels.keys()))
    ticker = labels[selected_label]
    q = get_live_quote(ticker); hist = indicators(get_history(ticker))
    if q and q.get("price") is not None:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Live Price", money(q["price"]))
        c2.metric("Day Change", money(q.get("change")), f'{q["change_pct"]:+.2f}%' if q.get("change_pct") is not None else None)
        c3.metric("Day High", money(q.get("high"))); c4.metric("Day Low", money(q.get("low")))
    if not hist.empty:
        sig = signal(hist); last = hist.iloc[-1]; momentum = 0 if pd.isna(last.momentum20) else float(last.momentum20); estimated = q["price"] * (1 + momentum * .25 / 100) if q and q.get("price") else None
        st.subheader("Technical Analysis")
        a,b,c,d = st.columns(4); a.metric("SMA 20", money(last.sma20)); b.metric("SMA 50", money(last.sma50)); c.metric("RSI", f'{last.rsi:.2f}' if pd.notna(last.rsi) else "—"); d.metric("20D Momentum", f'{momentum:+.2f}%')
        st.line_chart(hist[["close","sma20","sma50"]].dropna(), height=420)
        cls = "buy" if sig == "BUY" else "sell" if sig == "SELL" else "hold"
        st.markdown(f'<div class="card"><h3>Signal: <span class="{cls}">{sig}</span></h3><p>Estimated price: <b>{money(estimated)}</b></p><p class="muted">Estimated price is a simple momentum-based indicator, not a guaranteed forecast.</p></div>', unsafe_allow_html=True)
    elif not q:
        st.error("Yahoo Finance could not return data for this stock right now. Please retry in a few seconds.")

else:
    search = st.text_input("Search NSE stocks", placeholder="Search symbol or company name...").strip().lower(); rows = []
    for ticker, (symbol, name) in STOCKS.items():
        if search and search not in symbol.lower() and search not in name.lower(): continue
        q = get_live_quote(ticker)
        if q and q.get("price") is not None: rows.append({"Symbol":symbol,"Company":name,"Exchange":"NSE","Live Price":q["price"],"Change %":q.get("change_pct")})
    if rows: st.dataframe(pd.DataFrame(rows).sort_values("Change %", ascending=False), use_container_width=True, hide_index=True)
    else: st.warning("No live stock data available right now.")

st.markdown('<div class="footer">SMA · Data provided by Yahoo Finance · For informational purposes only.</div>', unsafe_allow_html=True)
time.sleep(15)
st.rerun()
