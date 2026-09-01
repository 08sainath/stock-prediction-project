import io
import time
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="SMA · Stock Market Analysis", page_icon="₹", layout="wide", initial_sidebar_state="collapsed")

# -----------------------------
# Luxury / light UI
# -----------------------------
st.markdown(
    """
<style>
:root { --ink:#161616; --muted:#77736d; --gold:#b48a3b; --line:#e8e2d8; --paper:#fbfaf7; --green:#177245; --red:#b73b3b; }
.stApp { background:var(--paper); color:var(--ink); }
.block-container { max-width:1180px; padding:24px 24px 110px; }
header[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { display:none; }
.brand { font-size:14px; letter-spacing:5px; font-weight:800; color:var(--gold); margin-bottom:2px; }
.title { font-size:34px; line-height:1.05; font-weight:850; letter-spacing:-1.2px; margin:0 0 8px; }
.subtle { color:var(--muted); font-size:14px; }
.market-strip { display:flex; gap:10px; overflow-x:auto; padding:6px 0 18px; }
.market-chip { min-width:145px; padding:10px 14px; border:1px solid var(--line); border-radius:14px; background:white; }
.market-chip b { font-size:12px; letter-spacing:.5px; }
.market-chip span { display:block; margin-top:3px; font-size:15px; font-weight:750; }
.up { color:var(--green)!important; font-weight:750; }
.down { color:var(--red)!important; font-weight:750; }
.hero { background:white; border:1px solid var(--line); border-radius:24px; padding:24px; margin:8px 0 22px; box-shadow:0 10px 28px rgba(38,31,20,.05); }
.hero h2 { margin:0; font-size:25px; }
.hero p { color:var(--muted); margin:7px 0 0; }
.section-title { font-size:19px; font-weight:800; margin:22px 0 12px; }
.stock-card { background:#fff; border:1px solid var(--line); border-radius:20px; padding:18px; min-height:150px; box-shadow:0 8px 22px rgba(38,31,20,.035); }
.stock-card .name { font-size:18px; font-weight:800; }
.stock-card .company { color:var(--muted); font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.stock-card .price { font-size:25px; font-weight:850; margin-top:18px; }
.stock-card .expected { color:var(--muted); font-size:12px; margin-top:2px; }
.badge { display:inline-block; padding:5px 9px; border-radius:999px; font-size:11px; font-weight:800; letter-spacing:.3px; }
.badge-buy { background:#eaf6ef; color:var(--green); }
.badge-sell { background:#fcecec; color:var(--red); }
.badge-hold { background:#f8f0df; color:#946b1f; }
.conf { color:var(--muted); font-size:12px; margin-top:12px; }
.detail { background:white; border:1px solid var(--line); border-radius:22px; padding:22px; margin-top:12px; }
.metric { background:#fff; border:1px solid var(--line); border-radius:16px; padding:14px; }
.metric .label { color:var(--muted); font-size:11px; }
.metric .value { font-size:21px; font-weight:800; margin-top:4px; }
.reason { padding:12px 0; border-bottom:1px solid #eee9e1; }
.reason:last-child { border-bottom:0; }
.table-row { background:white; border:1px solid var(--line); border-radius:15px; padding:13px 15px; margin:7px 0; }
.table-row b { font-size:14px; }
.table-muted { color:var(--muted); font-size:11px; }
.bottom-nav { position:fixed; z-index:999; left:50%; transform:translateX(-50%); bottom:16px; width:min(650px,calc(100% - 28px)); background:rgba(255,255,255,.96); border:1px solid var(--line); border-radius:20px; padding:7px; box-shadow:0 14px 35px rgba(0,0,0,.12); backdrop-filter:blur(12px); }
.bottom-nav [data-testid="stRadio"] { margin:0; }
.bottom-nav [role="radiogroup"] { justify-content:space-around; gap:4px; }
.bottom-nav label { flex:1; justify-content:center; border-radius:14px; padding:9px 5px; font-size:12px; }
.bottom-nav label:has(input:checked) { background:#171717; color:white; }
button[kind="secondary"] { border-color:var(--line)!important; }
[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:16px; padding:12px; }
footer { visibility:hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Helpers
# -----------------------------
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
})


def number(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else None
    except Exception:
        return None


def money(v):
    return "₹—" if v is None or pd.isna(v) else f"₹{v:,.2f}"


def pct(v):
    return "—" if v is None or pd.isna(v) else f"{v:+.2f}%"


def yahoo_ticker(exchange, symbol, code=None):
    if exchange == "NSE":
        return f"{symbol}.NS"
    return f"{str(code).zfill(6)}.BO" if code else f"{symbol}.BO"

# -----------------------------
# Dynamic NSE + BSE universe
# -----------------------------
FALLBACK = [
    ("NSE","RELIANCE","Reliance Industries",None,"RELIANCE.NS"),
    ("NSE","TCS","Tata Consultancy Services",None,"TCS.NS"),
    ("NSE","INFY","Infosys",None,"INFY.NS"),
    ("NSE","HDFCBANK","HDFC Bank",None,"HDFCBANK.NS"),
    ("NSE","ICICIBANK","ICICI Bank",None,"ICICIBANK.NS"),
    ("NSE","SBIN","State Bank of India",None,"SBIN.NS"),
    ("NSE","ITC","ITC Limited",None,"ITC.NS"),
    ("NSE","BHARTIARTL","Bharti Airtel",None,"BHARTIARTL.NS"),
    ("NSE","LT","Larsen & Toubro",None,"LT.NS"),
    ("NSE","WIPRO","Wipro",None,"WIPRO.NS"),
    ("NSE","HCLTECH","HCL Technologies",None,"HCLTECH.NS"),
    ("NSE","MARUTI","Maruti Suzuki India",None,"MARUTI.NS"),
    ("NSE","SUNPHARMA","Sun Pharmaceutical",None,"SUNPHARMA.NS"),
    ("NSE","TATASTEEL","Tata Steel",None,"TATASTEEL.NS"),
    ("NSE","TATAMOTORS","Tata Motors",None,"TATAMOTORS.NS"),
    ("NSE","BAJFINANCE","Bajaj Finance",None,"BAJFINANCE.NS"),
    ("NSE","AXISBANK","Axis Bank",None,"AXISBANK.NS"),
    ("NSE","KOTAKBANK","Kotak Mahindra Bank",None,"KOTAKBANK.NS"),
    ("NSE","ASIANPAINT","Asian Paints",None,"ASIANPAINT.NS"),
    ("NSE","TITAN","Titan Company",None,"TITAN.NS"),
    ("NSE","ADANIENT","Adani Enterprises",None,"ADANIENT.NS"),
    ("NSE","ADANIPORTS","Adani Ports",None,"ADANIPORTS.NS"),
    ("NSE","NTPC","NTPC Limited",None,"NTPC.NS"),
    ("NSE","POWERGRID","Power Grid Corporation",None,"POWERGRID.NS"),
    ("NSE","ONGC","Oil & Natural Gas Corporation",None,"ONGC.NS"),
    ("NSE","COALINDIA","Coal India",None,"COALINDIA.NS"),
    ("NSE","BEL","Bharat Electronics",None,"BEL.NS"),
    ("NSE","HAL","Hindustan Aeronautics",None,"HAL.NS"),
    ("NSE","IRFC","Indian Railway Finance Corporation",None,"IRFC.NS"),
    ("NSE","IREDA","Indian Renewable Energy Development Agency",None,"IREDA.NS"),
]

@st.cache_data(ttl=86400, show_spinner=False)
def load_nse_universe():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    r = SESSION.get(url, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    df.columns = [str(c).strip().upper() for c in df.columns]
    symbol_col = next((c for c in ["SYMBOL","SYMBOL "] if c in df.columns), None)
    name_col = next((c for c in ["NAME OF COMPANY","NAME_OF_COMPANY"] if c in df.columns), None)
    if not symbol_col or not name_col:
        raise ValueError("Unexpected NSE securities CSV format")
    out = []
    for _, row in df.iterrows():
        symbol = str(row[symbol_col]).strip()
        name = str(row[name_col]).strip()
        if symbol and symbol.lower() != "nan":
            out.append({"exchange":"NSE","symbol":symbol,"company":name,"code":"","yahoo":f"{symbol}.NS"})
    return pd.DataFrame(out).drop_duplicates("yahoo")

@st.cache_data(ttl=86400, show_spinner=False)
def load_bse_universe():
    url = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
    params = {"scripcode":"", "Group":"", "industry":"", "segment":"Equity", "status":"Active"}
    r = SESSION.get(url, params=params, timeout=25, headers={"Referer":"https://www.bseindia.com/"})
    r.raise_for_status()
    data = r.json()
    rows = data.get("Table", data if isinstance(data, list) else [])
    out = []
    for x in rows:
        code = str(x.get("SCRIP_CD") or x.get("scripcode") or x.get("Scripcode") or x.get("SCRIP_CODE") or "").strip()
        name = str(x.get("NAME") or x.get("Scrip_Name") or x.get("scripname") or x.get("CompanyName") or "").strip()
        symbol = str(x.get("SYMBOL") or x.get("symbol") or x.get("Scrip_Code") or "").strip()
        if code.isdigit() and name and name.lower() != "nan":
            out.append({"exchange":"BSE","symbol":symbol or code,"company":name,"code":code,"yahoo":f"{code.zfill(6)}.BO"})
    return pd.DataFrame(out).drop_duplicates("yahoo")

@st.cache_data(ttl=86400, show_spinner=False)
def load_universe():
    frames = []
    try:
        frames.append(load_nse_universe())
    except Exception:
        pass
    try:
        frames.append(load_bse_universe())
    except Exception:
        pass
    if not frames:
        return pd.DataFrame(FALLBACK, columns=["exchange","symbol","company","code","yahoo"])
    result = pd.concat(frames, ignore_index=True)
    fallback = pd.DataFrame(FALLBACK, columns=["exchange","symbol","company","code","yahoo"])
    result = pd.concat([result, fallback], ignore_index=True).drop_duplicates(["exchange","yahoo"])
    return result.sort_values(["exchange","symbol"]).reset_index(drop=True)

UNIVERSE = load_universe()

# -----------------------------
# Yahoo Finance chart API
# -----------------------------
@st.cache_data(ttl=15, show_spinner=False)
def yahoo_chart(ticker, range_value="1d", interval="1m"):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        r = SESSION.get(url, params={"range":range_value,"interval":interval,"includePrePost":"false","events":"div,splits"}, timeout=12)
        r.raise_for_status()
        payload = r.json()
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result:
            return None
        meta = result.get("meta", {})
        price = number(meta.get("regularMarketPrice"))
        previous = number(meta.get("previousClose")) or number(meta.get("chartPreviousClose"))
        high = number(meta.get("regularMarketDayHigh")); low = number(meta.get("regularMarketDayLow"))
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes = [number(x) for x in quote.get("close", [])]
        closes = [x for x in closes if x is not None]
        if price is None and closes: price = closes[-1]
        if not closes: return None
        change = price - previous if price is not None and previous is not None else None
        change_pct = change / previous * 100 if change is not None and previous not in (None, 0) else None
        return {"price":price,"previous":previous,"change":change,"change_pct":change_pct,"high":high,"low":low,"closes":closes}
    except Exception:
        return None

@st.cache_data(ttl=180, show_spinner=False)
def history(ticker):
    q = yahoo_chart(ticker, "1y", "1d")
    if not q: return pd.DataFrame()
    # Re-request timestamps because chart cache payload is intentionally reduced.
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        r = SESSION.get(url, params={"range":"1y","interval":"1d","includePrePost":"false"}, timeout=15)
        r.raise_for_status(); result = (r.json().get("chart", {}).get("result") or [None])[0]
        if not result: return pd.DataFrame()
        ts = result.get("timestamp") or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        close = quote.get("close") or []
        high = quote.get("high") or []
        low = quote.get("low") or []
        frame = pd.DataFrame({"date":pd.to_datetime(ts, unit="s", utc=True),"close":close,"high":high,"low":low})
        return frame.dropna(subset=["close"]).set_index("date")
    except Exception:
        return pd.DataFrame()


def indicators(df):
    df = df.copy()
    df["sma20"] = df.close.rolling(20).mean()
    df["sma50"] = df.close.rolling(50).mean()
    delta = df.close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - 100/(1+rs)
    df["momentum20"] = df.close.pct_change(20)*100
    return df


def analysis(ticker):
    q = yahoo_chart(ticker, "1d", "1m")
    h = indicators(history(ticker))
    if h.empty:
        return q, h, "HOLD", 50, None
    last = h.iloc[-1]
    score = 0
    reasons = []
    if pd.notna(last.sma20):
        if last.close > last.sma20: score += 1; reasons.append("Price is above the 20-day trend line.")
        else: score -= 1; reasons.append("Price is below the 20-day trend line.")
    if pd.notna(last.sma50):
        if last.close > last.sma50: score += 1; reasons.append("Price is above the 50-day trend line.")
        else: score -= 1; reasons.append("Price is below the 50-day trend line.")
    if pd.notna(last.rsi):
        if last.rsi < 35: score += 2; reasons.append("RSI is in an oversold zone, which can support a rebound setup.")
        elif last.rsi > 70: score -= 2; reasons.append("RSI is in an overbought zone, increasing pullback risk.")
        else: reasons.append(f"RSI is {last.rsi:.1f}, inside a neutral range.")
    if pd.notna(last.momentum20):
        reasons.append(f"20-day momentum is {last.momentum20:+.2f}%.")
    signal = "BUY" if score >= 2 else "SELL" if score <= -2 else "HOLD"
    confidence = int(np.clip(50 + abs(score)*12 + (10 if pd.notna(last.momentum20) and abs(last.momentum20) > 5 else 0), 50, 92))
    expected = q["price"]*(1 + float(last.momentum20)*0.25/100) if q and q.get("price") is not None and pd.notna(last.momentum20) else (q.get("price") if q else None)
    return q, h, signal, confidence, {"expected":expected,"reasons":reasons,"rsi":last.rsi,"sma20":last.sma20,"sma50":last.sma50,"momentum":last.momentum20}


def badge(signal):
    cls = {"BUY":"badge-buy","SELL":"badge-sell","HOLD":"badge-hold"}.get(signal,"badge-hold")
    return f'<span class="badge {cls}">{signal}</span>'

# -----------------------------
# Header / market strip
# -----------------------------
st.markdown('<div class="brand">SMA</div>', unsafe_allow_html=True)
st.markdown('<div class="title">Stock Market Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">NSE + BSE · live Yahoo Finance prices · technical analysis</div>', unsafe_allow_html=True)

indices = [("NIFTY 50","^NSEI"),("BANK NIFTY","^NSEBANK"),("SENSEX","^BSESN")]
chips = []
for name, ticker in indices:
    q = yahoo_chart(ticker, "1d", "1m")
    if q and q.get("price") is not None:
        cls = "up" if (q.get("change_pct") or 0) >= 0 else "down"
        chips.append(f'<div class="market-chip"><b>{name}</b><span>{money(q["price"])}</span><small class="{cls}">{pct(q.get("change_pct"))}</small></div>')
    else:
        chips.append(f'<div class="market-chip"><b>{name}</b><span>₹—</span><small>temporarily unavailable</small></div>')
st.markdown('<div class="market-strip">'+''.join(chips)+'</div>', unsafe_allow_html=True)

# -----------------------------
# Bottom navigation
# -----------------------------
st.markdown('<div class="bottom-nav">', unsafe_allow_html=True)
page = st.radio("Navigation", ["⌂  Home", "▤  All Stocks", "⌕  Analysis"], horizontal=True, label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Home
# -----------------------------
if page == "⌂  Home":
    st.markdown('<div class="hero"><h2>Find the next opportunity.</h2><p>Scan listed Indian equities, compare current and expected prices, and understand the BUY / SELL / HOLD signal before making a decision.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Best stocks to buy</div>', unsafe_allow_html=True)

    # Analyze a manageable, liquid starter set for the home screen.
    featured = ["TCS.NS","INFY.NS","RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS"]
    featured_rows = []
    for ticker in featured:
        row = UNIVERSE[UNIVERSE.yahoo.eq(ticker)]
        if row.empty: continue
        q,h,sig,conf,details = analysis(ticker)
        if q and q.get("price") is not None:
            featured_rows.append((row.iloc[0],q,sig,conf,details))
    featured_rows.sort(key=lambda x: (1 if x[2]=="BUY" else 0, x[3]), reverse=True)
    if featured_rows:
        cols = st.columns(min(3,len(featured_rows)))
        for col, (row,q,sig,conf,details) in zip(cols, featured_rows[:3]):
            expected = details.get("expected") if details else None
            with col:
                st.markdown(f'<div class="stock-card"><div class="name">{row.symbol}</div><div class="company">{row.company}</div><div style="margin-top:10px">{badge(sig)}</div><div class="price">{money(q["price"])}</div><div class="expected">Expected · {money(expected)}</div><div class="conf">Confidence · {conf}%</div></div>', unsafe_allow_html=True)
    else:
        st.info("Yahoo Finance is temporarily unavailable. Press Refresh below.")

    st.markdown('<div class="section-title">Why BUY / SELL / HOLD?</div>', unsafe_allow_html=True)
    a,b,c = st.columns(3)
    with a:
        st.markdown('<div class="detail"><b>01 · Price trend</b><div class="subtle">20D and 50D moving averages show whether price is above or below recent trend.</div></div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="detail"><b>02 · Technical analysis</b><div class="subtle">RSI and momentum help identify strength, weakness and stretched conditions.</div></div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="detail"><b>03 · Recent market</b><div class="subtle">NIFTY, BANK NIFTY and SENSEX movement gives broader market context.</div></div>', unsafe_allow_html=True)

    st.caption(f"Universe loaded: {len(UNIVERSE):,} NSE/BSE equity securities. The exchange lists are refreshed daily in the app cache.")

# -----------------------------
# All stocks
# -----------------------------
elif page == "▤  All Stocks":
    st.markdown('<div class="section-title">All Stocks</div>', unsafe_allow_html=True)
    st.caption("The list is built from the current NSE equity securities file and BSE active equity scrip list. Live prices are requested from Yahoo Finance only when needed, to avoid rate-limit storms.")
    c1,c2,c3 = st.columns([2,1,1])
    with c1: search = st.text_input("Search", placeholder="TCS, Reliance, Infosys…", label_visibility="collapsed")
    with c2: exchange = st.selectbox("Exchange", ["All","NSE","BSE"], label_visibility="collapsed")
    with c3: sort_by = st.selectbox("Sort", ["Symbol","Company"], label_visibility="collapsed")
    filtered = UNIVERSE.copy()
    if search:
        s = search.lower().strip(); filtered = filtered[filtered.symbol.str.lower().str.contains(s, na=False) | filtered.company.str.lower().str.contains(s, na=False)]
    if exchange != "All": filtered = filtered[filtered.exchange.eq(exchange)]
    filtered = filtered.sort_values(sort_by.lower()).reset_index(drop=True)
    st.write(f"**{len(filtered):,} stocks**")

    # Load prices in batches of visible rows only. The complete exchange universe remains available even when prices are not requested.
    load_count = min(50, len(filtered))
    if st.button(f"Load live prices for first {load_count} stocks", use_container_width=True):
        st.session_state["load_all_live"] = True
    if st.session_state.get("load_all_live"):
        display = filtered.head(load_count)
        for _, row in display.iterrows():
            q = yahoo_chart(row.yahoo, "1d", "1m")
            price = q.get("price") if q else None
            change = q.get("change_pct") if q else None
            h = indicators(history(row.yahoo))
            sig = "HOLD"; expected = price; conf = 50
            if not h.empty and price is not None:
                last = h.iloc[-1]
                score = (1 if pd.notna(last.sma20) and last.close > last.sma20 else -1 if pd.notna(last.sma20) else 0) + (1 if pd.notna(last.sma50) and last.close > last.sma50 else -1 if pd.notna(last.sma50) else 0)
                sig = "BUY" if score >= 2 else "SELL" if score <= -2 else "HOLD"
                mom = number(last.momentum20)
                expected = price*(1+mom*.25/100) if mom is not None else price
                conf = int(np.clip(50+abs(score)*12,50,86))
            cls = "up" if (change or 0) >= 0 else "down"
            st.markdown(f'<div class="table-row"><b>{row.symbol}</b> <span class="table-muted">{row.exchange} · {row.company}</span><br><span>{money(price)}</span> &nbsp; <span class="{cls}">{pct(change)}</span> &nbsp; {badge(sig)} &nbsp; <span class="table-muted">Expected {money(expected)} · {conf}%</span></div>', unsafe_allow_html=True)
    else:
        for _, row in filtered.head(100).iterrows():
            st.markdown(f'<div class="table-row"><b>{row.symbol}</b> <span class="table-muted">{row.exchange} · {row.company}</span><span style="float:right" class="table-muted">Live price not loaded</span></div>', unsafe_allow_html=True)
        if len(filtered) > 100: st.caption("Showing the first 100 rows. Use search to find any listed stock, then load live prices.")

# -----------------------------
# Analysis
# -----------------------------
else:
    st.markdown('<div class="section-title">Stock Analysis</div>', unsafe_allow_html=True)
    labels = (UNIVERSE["exchange"]+" · "+UNIVERSE["symbol"]+" — "+UNIVERSE["company"]).tolist()
    selected = st.selectbox("Select a stock", labels)
    idx = labels.index(selected)
    row = UNIVERSE.iloc[idx]
    q,h,sig,conf,details = analysis(row.yahoo)
    if q and q.get("price") is not None:
        st.markdown(f'<div class="detail"><div class="name" style="font-size:23px;font-weight:850">{row.symbol} <span class="table-muted">{row.exchange}</span></div><div class="subtle">{row.company}</div><div style="margin-top:14px">{badge(sig)}</div><div class="price" style="font-size:34px;font-weight:850">{money(q["price"])}</div><div class="subtle">Today <span class="{("up" if (q.get("change_pct") or 0)>=0 else "down")}">{pct(q.get("change_pct"))}</span></div></div>', unsafe_allow_html=True)
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Expected price", money(details.get("expected") if details else None))
        m2.metric("Confidence", f"{conf}%")
        m3.metric("Day high", money(q.get("high")))
        m4.metric("Day low", money(q.get("low")))
        if not h.empty:
            last = h.iloc[-1]
            a,b,c,d = st.columns(4)
            a.metric("SMA 20", money(last.sma20)); b.metric("SMA 50", money(last.sma50)); c.metric("RSI", f"{last.rsi:.1f}" if pd.notna(last.rsi) else "—"); d.metric("20D momentum", pct(last.momentum20))
            st.markdown('<div class="section-title">Why this signal?</div>', unsafe_allow_html=True)
            st.markdown('<div class="detail">'+''.join(f'<div class="reason">• {x}</div>' for x in details.get("reasons",[]))+'</div>', unsafe_allow_html=True)
            chart = h[["close","sma20","sma50"]].dropna()
            if not chart.empty: st.line_chart(chart, height=380)
        st.caption("Expected price and BUY/SELL/HOLD are SMA model indicators, not guaranteed forecasts or investment advice.")
    else:
        st.error("Yahoo Finance could not return this quote right now. Try Refresh and select the stock again.")

# Refresh control
st.divider()
left,right = st.columns([1,4])
with left:
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear(); st.rerun()
with right:
    st.caption(f"Last page refresh: {time.strftime('%H:%M:%S')} IST · Yahoo Finance data may be delayed or temporarily unavailable.")
