import time
import numpy as np
import pandas as pd
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

# Indian NSE stocks only. Yahoo Finance uses .NS for NSE symbols.
STOCKS = {
    "RELIANCE.NS":("RELIANCE","Reliance Industries"), "TCS.NS":("TCS","Tata Consultancy Services"),
    "INFY.NS":("INFY","Infosys"), "HDFCBANK.NS":("HDFCBANK","HDFC Bank"),
    "ICICIBANK.NS":("ICICIBANK","ICICI Bank"), "SBIN.NS":("SBIN","State Bank of India"),
    "ITC.NS":("ITC","ITC Limited"), "BHARTIARTL.NS":("BHARTIARTL","Bharti Airtel"),
    "LT.NS":("LT","Larsen & Toubro"), "WIPRO.NS":("WIPRO","Wipro"),
    "HCLTECH.NS":("HCLTECH","HCL Technologies"), "MARUTI.NS":("MARUTI","Maruti Suzuki India"),
    "SUNPHARMA.NS":("SUNPHARMA","Sun Pharmaceutical"), "TATASTEEL.NS":("TATASTEEL","Tata Steel"),
    "TATAMOTORS.NS":("TATAMOTORS","Tata Motors"), "BAJFINANCE.NS":("BAJFINANCE","Bajaj Finance"),
    "AXISBANK.NS":("AXISBANK","Axis Bank"), "KOTAKBANK.NS":("KOTAKBANK","Kotak Mahindra Bank"),
    "ASIANPAINT.NS":("ASIANPAINT","Asian Paints"), "TITAN.NS":("TITAN","Titan Company"),
    "ADANIENT.NS":("ADANIENT","Adani Enterprises"), "ADANIPORTS.NS":("ADANIPORTS","Adani Ports"),
    "NTPC.NS":("NTPC","NTPC Limited"), "POWERGRID.NS":("POWERGRID","Power Grid Corporation"),
    "ONGC.NS":("ONGC","Oil & Natural Gas Corporation"), "COALINDIA.NS":("COALINDIA","Coal India"),
    "BEL.NS":("BEL","Bharat Electronics"), "HAL.NS":("HAL","Hindustan Aeronautics"),
    "IRFC.NS":("IRFC","Indian Railway Finance Corporation"), "IREDA.NS":("IREDA","Indian Renewable Energy Development Agency")
}
INDICES = {"^NSEI":("NIFTY 50","NIFTY 50"), "^NSEBANK":("BANK NIFTY","NIFTY Bank"), "^BSESN":("SENSEX","BSE SENSEX")}


def number(v):
    try:
        v=float(v)
        return v if np.isfinite(v) else None
    except Exception:
        return None


def _quote_from_frame(frame):
    if frame is None or frame.empty or "Close" not in frame.columns:
        return None
    close=frame["Close"].dropna()
    if close.empty:
        return None
    price=number(close.iloc[-1])
    previous=number(close.iloc[-2]) if len(close)>1 else None
    high=number(frame["High"].dropna().iloc[-1]) if "High" in frame and not frame["High"].dropna().empty else None
    low=number(frame["Low"].dropna().iloc[-1]) if "Low" in frame and not frame["Low"].dropna().empty else None
    volume=number(frame["Volume"].dropna().iloc[-1]) if "Volume" in frame and not frame["Volume"].dropna().empty else None
    change=price-previous if price is not None and previous is not None else None
    pct=change/previous*100 if change is not None and previous else None
    return {"price":price,"previous":previous,"change":change,"change_pct":pct,"high":high,"low":low,"volume":volume}


@st.cache_data(ttl=15, show_spinner=False)
def get_live_quotes(tickers):
    """Batch Yahoo Finance request. This avoids one request per ticker and reduces Yahoo rate-limit/API errors."""
    tickers=tuple(tickers)
    result={}
    if not tickers:
        return result
    try:
        data=yf.download(list(tickers), period="1d", interval="1m", auto_adjust=False, progress=False, threads=True, group_by="ticker")
        for ticker in tickers:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker in data.columns.get_level_values(0):
                        frame=data[ticker]
                    elif ticker in data.columns.get_level_values(1):
                        frame=data.xs(ticker, axis=1, level=1)
                    else:
                        frame=None
                else:
                    frame=data if len(tickers)==1 else None
                q=_quote_from_frame(frame)
                if q:
                    result[ticker]=q
            except Exception:
                continue
    except Exception:
        pass
    return result


@st.cache_data(ttl=120, show_spinner=False)
def get_history(ticker, period="1y"):
    try:
        df=yf.download(ticker, period=period, interval="1d", auto_adjust=False, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns,pd.MultiIndex):
            df=df.xs(ticker,axis=1,level=1) if ticker in df.columns.get_level_values(1) else df.droplevel(1,axis=1)
        df.columns=[str(c).lower() for c in df.columns]
        cols=[c for c in ["open","high","low","close","volume"] if c in df.columns]
        return df[cols].dropna(subset=["close"])
    except Exception:
        return pd.DataFrame()


def rsi(series, period=14):
    delta=series.diff(); gain=delta.clip(lower=0).rolling(period).mean(); loss=(-delta.clip(upper=0)).rolling(period).mean()
    rs=gain/loss.replace(0,np.nan)
    return 100-100/(1+rs)


def indicators(df):
    df=df.copy(); df["sma20"]=df.close.rolling(20).mean(); df["sma50"]=df.close.rolling(50).mean()
    df["rsi"]=rsi(df.close); df["momentum20"]=df.close.pct_change(20)*100
    df["volatility"]=df.close.pct_change().rolling(20).std()*np.sqrt(252)*100
    return df


def signal(df):
    if df.empty:return "HOLD"
    last=df.iloc[-1]; score=0
    if pd.notna(last.sma20): score+=1 if last.close>last.sma20 else -1
    if pd.notna(last.sma50): score+=1 if last.close>last.sma50 else -1
    if pd.notna(last.rsi):
        if last.rsi<35:score+=2
        elif last.rsi>70:score-=2
    return "BUY" if score>=2 else "SELL" if score<=-2 else "HOLD"


def money(v): return "₹—" if v is None or pd.isna(v) else f"₹{v:,.2f}"

st.markdown('<div class="brand">SMA</div><div class="muted">STOCK MARKET ANALYSIS · INDIAN MARKETS</div>',unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>Indian Stock Market Analysis</h1><p class="muted">Yahoo Finance market data, technical indicators and estimated price analysis.</p></div>',unsafe_allow_html=True)

page=st.radio("Navigation",["Market Overview","Stock Analysis","All Stocks"],horizontal=True,label_visibility="collapsed")

# Only one batched Yahoo request for the three indices.
index_quotes=get_live_quotes(tuple(INDICES.keys()))
st.subheader("Live Market")
cols=st.columns(3)
for col,(ticker,(symbol,name)) in zip(cols,INDICES.items()):
    q=index_quotes.get(ticker)
    with col:
        if q:
            cls="buy" if (q["change_pct"] or 0)>=0 else "sell"
            st.markdown(f'<div class="card"><b>{symbol}</b><br><span style="font-size:28px;font-weight:800">{money(q["price"])}</span><br><span class="{cls}">{q["change_pct"]:+.2f}%</span> today</div>',unsafe_allow_html=True)
        else:
            st.warning(f"{symbol}: Yahoo Finance data unavailable")

st.caption("Yahoo Finance is queried in batches and refreshed every 15 seconds. During market closures, the latest available quote may be shown. Yahoo Finance is a third-party data source and is not an exchange-direct feed.")

if page=="Market Overview":
    st.subheader("Market Status")
    if index_quotes: st.success("Yahoo Finance connection is active.")
    else: st.error("Yahoo Finance is currently not returning index data. Try again after a short delay.")

elif page=="Stock Analysis":
    labels={f"{v[0]} — {v[1]}":k for k,v in STOCKS.items()}
    selected=st.selectbox("Select NSE stock",list(labels.keys()))
    ticker=labels[selected]
    quote=get_live_quotes((ticker,)).get(ticker)
    hist=indicators(get_history(ticker))
    if quote:
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Latest Price",money(quote["price"]))
        c2.metric("Day Change",money(quote["change"]),f'{quote["change_pct"]:+.2f}%' if quote["change_pct"] is not None else None)
        c3.metric("Day High",money(quote["high"]))
        c4.metric("Day Low",money(quote["low"]))
    else:
        st.warning("Yahoo Finance did not return a current quote for this stock.")
    if not hist.empty:
        sig=signal(hist); last=hist.iloc[-1]; momentum=0 if pd.isna(last.momentum20) else float(last.momentum20)
        estimated=quote["price"]*(1+momentum*.25/100) if quote and quote["price"] else None
        st.subheader("Technical Analysis")
        a,b,c,d=st.columns(4); a.metric("SMA 20",money(last.sma20)); b.metric("SMA 50",money(last.sma50)); c.metric("RSI",f'{last.rsi:.2f}' if pd.notna(last.rsi) else "—"); d.metric("20D Momentum",f'{momentum:+.2f}%')
        st.line_chart(hist[["close","sma20","sma50"]].dropna(),height=420)
        cls="buy" if sig=="BUY" else "sell" if sig=="SELL" else "hold"
        st.markdown(f'<div class="card"><h3>Signal: <span class="{cls}">{sig}</span></h3><p>Estimated price: <b>{money(estimated)}</b></p><p class="muted">Estimated price is a momentum-based indicator, not a guaranteed forecast.</p></div>',unsafe_allow_html=True)
    else: st.error("Historical data could not be loaded from Yahoo Finance.")

else:
    search=st.text_input("Search NSE stocks",placeholder="Search symbol or company name...").strip().lower()
    tickers=tuple(t for t,(s,n) in STOCKS.items() if not search or search in s.lower() or search in n.lower())
    quotes=get_live_quotes(tickers)
    rows=[]
    for ticker in tickers:
        q=quotes.get(ticker)
        if q:
            symbol,name=STOCKS[ticker]
            rows.append({"Symbol":symbol,"Company":name,"Exchange":"NSE","Live Price":q["price"],"Change %":q["change_pct"]})
    if rows:
        st.dataframe(pd.DataFrame(rows).sort_values("Change %",ascending=False),use_container_width=True,hide_index=True)
    else: st.warning("No live stock data available from Yahoo Finance right now.")

st.markdown('<div class="footer">SMA · Data provided by Yahoo Finance · For informational purposes only.</div>',unsafe_allow_html=True)

time.sleep(15)
st.rerun()
