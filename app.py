import io
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="SMA · Stock Market Analysis",
    page_icon="₹",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# SMA — luxury / light, Groww-inspired investment dashboard
# ============================================================
st.markdown(
    """
<style>
:root {
  --ink:#171717; --muted:#77736d; --gold:#b58a3c; --line:#e9e3da;
  --paper:#faf9f6; --card:#ffffff; --green:#16834b; --red:#c63e3e; --amber:#9a701d;
}
.stApp { background:var(--paper); color:var(--ink); }
.block-container { max-width:1240px; padding:22px 24px 105px; }
header[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { display:none; }
footer { visibility:hidden; }
.brand { color:var(--gold); font-size:13px; font-weight:900; letter-spacing:5px; margin-bottom:5px; }
.page-title { font-size:32px; line-height:1.05; font-weight:850; letter-spacing:-1.1px; margin:0; }
.page-sub { color:var(--muted); font-size:13px; margin-top:7px; }
.hero { background:var(--card); border:1px solid var(--line); border-radius:24px; padding:24px; box-shadow:0 10px 30px rgba(40,32,20,.045); }
.hero-title { font-size:25px; font-weight:850; letter-spacing:-.5px; }
.hero-sub { color:var(--muted); font-size:13px; margin-top:4px; }
.section-title { font-size:19px; font-weight:850; margin:24px 0 11px; }
.market-strip { display:flex; gap:10px; overflow-x:auto; padding:5px 0 8px; }
.market-chip { min-width:155px; background:#fff; border:1px solid var(--line); border-radius:16px; padding:12px 14px; }
.market-chip .mname { font-size:11px; color:var(--muted); font-weight:750; }
.market-chip .mvalue { font-size:17px; font-weight:850; margin-top:3px; }
.market-chip .mchange { font-size:11px; margin-top:2px; }
.up { color:var(--green)!important; }
.down { color:var(--red)!important; }
.stock-card { background:#fff; border:1px solid var(--line); border-radius:20px; padding:17px; min-height:145px; box-shadow:0 8px 24px rgba(40,32,20,.035); }
.stock-name { font-size:17px; font-weight:850; }
.stock-company { color:var(--muted); font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-top:2px; }
.stock-price { font-size:23px; font-weight:900; margin-top:15px; }
.stock-meta { color:var(--muted); font-size:11px; margin-top:3px; }
.badge { display:inline-block; border-radius:999px; padding:5px 9px; font-size:10px; font-weight:850; letter-spacing:.25px; }
.badge-buy { background:#e8f6ee; color:var(--green); }
.badge-sell { background:#fcebea; color:var(--red); }
.badge-hold { background:#faf1df; color:var(--amber); }
.conf { color:var(--muted); font-size:11px; margin-top:9px; }
.data-card { background:#fff; border:1px solid var(--line); border-radius:18px; padding:15px; }
.data-label { color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.6px; }
.data-value { font-size:20px; font-weight:850; margin-top:4px; }
.search-box { background:#fff; border:1px solid var(--line); border-radius:18px; padding:12px; }
.reason { padding:11px 0; border-bottom:1px solid #eee9e1; font-size:13px; }
.reason:last-child { border-bottom:0; }
.small-note { color:var(--muted); font-size:11px; }
.bottom-nav { position:fixed; z-index:999; left:50%; transform:translateX(-50%); bottom:15px; width:min(680px,calc(100% - 26px)); background:rgba(255,255,255,.97); border:1px solid var(--line); border-radius:20px; padding:7px; box-shadow:0 15px 38px rgba(0,0,0,.12); backdrop-filter:blur(12px); }
.bottom-nav [role="radiogroup"] { justify-content:space-around; gap:4px; }
.bottom-nav label { flex:1; justify-content:center; border-radius:14px; padding:9px 5px; font-size:12px; }
.bottom-nav label:has(input:checked) { background:#171717; color:#fff; }
button[kind="secondary"] { border-color:var(--line)!important; }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:16px; overflow:hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# HTTP / helpers
# ============================================================
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-IN,en;q=0.9",
})


def num(value):
    try:
        x = float(value)
        return x if np.isfinite(x) else None
    except Exception:
        return None


def money(value):
    return "₹—" if value is None or pd.isna(value) else f"₹{value:,.2f}"


def pct(value):
    return "—" if value is None or pd.isna(value) else f"{value:+.2f}%"


def yahoo_ticker(exchange, symbol, code=""):
    if exchange == "NSE":
        return f"{str(symbol).strip()}.NS"
    return f"{str(code).zfill(6)}.BO" if str(code).strip() else f"{str(symbol).strip()}.BO"


# ============================================================
# NSE + BSE complete universe
# ============================================================
FALLBACK = [
    ("NSE","RELIANCE","Reliance Industries", "", "RELIANCE.NS"),
    ("NSE","TCS","Tata Consultancy Services", "", "TCS.NS"),
    ("NSE","INFY","Infosys Limited", "", "INFY.NS"),
    ("NSE","HDFCBANK","HDFC Bank Limited", "", "HDFCBANK.NS"),
    ("NSE","ICICIBANK","ICICI Bank Limited", "", "ICICIBANK.NS"),
    ("NSE","SBIN","State Bank of India", "", "SBIN.NS"),
    ("NSE","ITC","ITC Limited", "", "ITC.NS"),
    ("NSE","BHARTIARTL","Bharti Airtel Limited", "", "BHARTIARTL.NS"),
    ("NSE","LT","Larsen & Toubro Limited", "", "LT.NS"),
    ("NSE","WIPRO","Wipro Limited", "", "WIPRO.NS"),
    ("NSE","HCLTECH","HCL Technologies Limited", "", "HCLTECH.NS"),
    ("NSE","MARUTI","Maruti Suzuki India Limited", "", "MARUTI.NS"),
    ("NSE","SUNPHARMA","Sun Pharmaceutical Industries Limited", "", "SUNPHARMA.NS"),
    ("NSE","TATASTEEL","Tata Steel Limited", "", "TATASTEEL.NS"),
    ("NSE","TATAMOTORS","Tata Motors Limited", "", "TATAMOTORS.NS"),
]


@st.cache_data(ttl=86400, show_spinner=False)
def load_nse_universe():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    r = SESSION.get(url, timeout=25)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    df.columns = [str(c).strip().upper() for c in df.columns]
    symbol_col = "SYMBOL" if "SYMBOL" in df.columns else None
    name_col = "NAME OF COMPANY" if "NAME OF COMPANY" in df.columns else None
    if not symbol_col or not name_col:
        raise ValueError("NSE securities file format changed")
    rows = []
    for _, row in df.iterrows():
        symbol = str(row[symbol_col]).strip()
        company = str(row[name_col]).strip()
        if symbol and symbol.lower() != "nan":
            rows.append({"exchange":"NSE", "symbol":symbol, "company":company, "code":"", "yahoo":f"{symbol}.NS"})
    return pd.DataFrame(rows).drop_duplicates("yahoo")


@st.cache_data(ttl=86400, show_spinner=False)
def load_bse_universe():
    url = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
    params = {"scripcode":"", "Group":"", "industry":"", "segment":"Equity", "status":"Active"}
    r = SESSION.get(url, params=params, timeout=30, headers={"Referer":"https://www.bseindia.com/"})
    r.raise_for_status()
    data = r.json()
    rows = data.get("Table", data if isinstance(data, list) else [])
    out = []
    for x in rows:
        code = str(x.get("SCRIP_CD") or x.get("scripcode") or x.get("Scripcode") or x.get("SCRIP_CODE") or "").strip()
        company = str(x.get("NAME") or x.get("Scrip_Name") or x.get("scripname") or x.get("CompanyName") or "").strip()
        symbol = str(x.get("SYMBOL") or x.get("symbol") or "").strip()
        if code.isdigit() and company and company.lower() != "nan":
            out.append({"exchange":"BSE", "symbol":symbol or code, "company":company, "code":code, "yahoo":f"{code.zfill(6)}.BO"})
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
    fallback = pd.DataFrame(FALLBACK, columns=["exchange","symbol","company","code","yahoo"])
    result = pd.concat(frames + [fallback], ignore_index=True)
    return result.drop_duplicates(["exchange","yahoo"]).sort_values(["exchange","symbol"]).reset_index(drop=True)


UNIVERSE = load_universe()

# ============================================================
# Yahoo chart API — no yfinance dependency
# ============================================================
@st.cache_data(ttl=20, show_spinner=False)
def yahoo_chart(ticker, range_value="1d", interval="1d"):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {
            "range": range_value,
            "interval": interval,
            "includePrePost": "false",
            "events": "div,splits",
        }
        r = SESSION.get(url, params=params, timeout=15)
        r.raise_for_status()
        payload = r.json()
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result:
            return None
        meta = result.get("meta", {}) or {}
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        timestamps = result.get("timestamp") or []
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []

        price = num(meta.get("regularMarketPrice"))
        previous_close = num(meta.get("previousClose")) or num(meta.get("chartPreviousClose"))
        day_open = num(meta.get("regularMarketOpen"))
        day_high = num(meta.get("regularMarketDayHigh"))
        day_low = num(meta.get("regularMarketDayLow"))

        # Prefer today's chart candle when available; it gives reliable OHLC.
        if timestamps and closes:
            valid = []
            for i, close in enumerate(closes):
                if num(close) is not None:
                    valid.append(i)
            if valid:
                i = valid[-1]
                if day_open is None and i < len(opens): day_open = num(opens[i])
                if day_high is None and i < len(highs): day_high = num(highs[i])
                if day_low is None and i < len(lows): day_low = num(lows[i])
                chart_close = num(closes[i])
                if price is None: price = chart_close

        if price is None:
            return None
        if previous_close is None and closes:
            valid_closes = [num(x) for x in closes if num(x) is not None]
            if len(valid_closes) >= 2:
                previous_close = valid_closes[-2]

        change = price - previous_close if previous_close is not None else None
        change_pct = (change / previous_close * 100) if change is not None and previous_close not in (None, 0) else None
        return {
            "ticker": ticker,
            "price": price,
            "open": day_open,
            "close": previous_close,
            "high": day_high,
            "low": day_low,
            "change": change,
            "change_pct": change_pct,
            "closes": [num(x) for x in closes if num(x) is not None],
        }
    except Exception:
        return None


@st.cache_data(ttl=180, show_spinner=False)
def historical(ticker):
    q = yahoo_chart(ticker, "1y", "1d")
    if not q:
        return pd.DataFrame()
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        r = SESSION.get(url, params={"range":"1y", "interval":"1d", "includePrePost":"false"}, timeout=18)
        r.raise_for_status()
        result = (r.json().get("chart", {}).get("result") or [None])[0]
        if not result:
            return pd.DataFrame()
        ts = result.get("timestamp") or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        frame = pd.DataFrame({
            "date": pd.to_datetime(ts, unit="s", utc=True),
            "open": quote.get("open") or [],
            "high": quote.get("high") or [],
            "low": quote.get("low") or [],
            "close": quote.get("close") or [],
        })
        return frame.dropna(subset=["close"]).set_index("date")
    except Exception:
        return pd.DataFrame()


def technicals(df):
    if df.empty:
        return df
    out = df.copy()
    out["sma20"] = out["close"].rolling(20).mean()
    out["sma50"] = out["close"].rolling(50).mean()
    delta = out["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi"] = 100 - (100 / (1 + rs))
    return out


def estimate_signal(current, hist):
    if current is None:
        return None, None, None, []
    if hist.empty or len(hist) < 20:
        estimated = current
        return estimated, "HOLD", 50, ["Not enough recent history for a stronger technical estimate."]
    h = technicals(hist)
    last = h.iloc[-1]
    sma20 = num(last.get("sma20")); sma50 = num(last.get("sma50")); rsi = num(last.get("rsi"))
    momentum20 = ((current / h["close"].iloc[-21]) - 1) * 100 if len(h) >= 21 and h["close"].iloc[-21] else 0
    trend = ((sma20 / sma50) - 1) * 100 if sma20 and sma50 else 0

    # Transparent heuristic estimate: short-term momentum + moving-average trend.
    expected_change = 0.55 * momentum20 + 0.45 * trend
    expected_change = float(np.clip(expected_change, -15, 15))
    estimated = current * (1 + expected_change / 100)

    score = 50 + min(30, abs(expected_change) * 2.0)
    reasons = []
    if momentum20 > 1: reasons.append(f"20-day momentum is positive ({momentum20:+.2f}%).")
    elif momentum20 < -1: reasons.append(f"20-day momentum is negative ({momentum20:+.2f}%).")
    else: reasons.append(f"20-day momentum is relatively flat ({momentum20:+.2f}%).")
    if sma20 and sma50:
        if sma20 > sma50: reasons.append("SMA20 is above SMA50, supporting the trend.")
        else: reasons.append("SMA20 is below SMA50, showing weaker trend structure.")
    if rsi is not None:
        if rsi >= 70: reasons.append(f"RSI is high at {rsi:.1f}; upside may be stretched.")
        elif rsi <= 30: reasons.append(f"RSI is low at {rsi:.1f}; the stock is technically oversold.")
        else: reasons.append(f"RSI is {rsi:.1f}, inside a neutral zone.")

    if expected_change >= 3 and (rsi is None or rsi < 72):
        signal = "BUY"
    elif expected_change <= -3 or (rsi is not None and rsi > 78):
        signal = "SELL"
    else:
        signal = "HOLD"
    confidence = int(np.clip(55 + abs(expected_change) * 2 + min(10, len(h) / 30), 55, 92))
    return estimated, signal, confidence, reasons


@st.cache_data(ttl=120, show_spinner=False)
def stock_snapshot(ticker):
    q = yahoo_chart(ticker, "1d", "1m") or yahoo_chart(ticker, "5d", "1d")
    if not q:
        return None
    hist = historical(ticker)
    estimated, signal, confidence, reasons = estimate_signal(q["price"], hist)
    latest = technicals(hist).iloc[-1] if not hist.empty else pd.Series(dtype=float)
    return {
        **q,
        "estimated": estimated,
        "signal": signal,
        "confidence": confidence,
        "reasons": reasons,
        "sma20": num(latest.get("sma20")) if not latest.empty else None,
        "sma50": num(latest.get("sma50")) if not latest.empty else None,
        "rsi": num(latest.get("rsi")) if not latest.empty else None,
    }


# ============================================================
# Market index quotes
# ============================================================
INDEXES = [
    ("NIFTY 50", "^NSEI"),
    ("BANK NIFTY", "^NSEBANK"),
    ("SENSEX", "^BSESN"),
]


def index_snapshot(ticker):
    return yahoo_chart(ticker, "5d", "1d")


# ============================================================
# Universe search — no giant stock list on Analysis page
# ============================================================
def resolve_stock(query):
    q = str(query or "").strip().lower()
    if not q:
        return None
    exact_symbol = UNIVERSE[UNIVERSE["symbol"].astype(str).str.lower() == q]
    if not exact_symbol.empty:
        return exact_symbol.iloc[0].to_dict()
    exact_company = UNIVERSE[UNIVERSE["company"].astype(str).str.lower() == q]
    if not exact_company.empty:
        return exact_company.iloc[0].to_dict()
    contains = UNIVERSE[
        UNIVERSE["symbol"].astype(str).str.lower().str.contains(q, regex=False, na=False)
        | UNIVERSE["company"].astype(str).str.lower().str.contains(q, regex=False, na=False)
    ]
    if contains.empty:
        return None
    # Prefer NSE when the same company/symbol exists on both exchanges.
    nse = contains[contains["exchange"] == "NSE"]
    return (nse.iloc[0] if not nse.empty else contains.iloc[0]).to_dict()


# ============================================================
# UI helpers
# ============================================================
def signal_badge(signal):
    if signal == "BUY": return '<span class="badge badge-buy">BUY</span>'
    if signal == "SELL": return '<span class="badge badge-sell">SELL</span>'
    return '<span class="badge badge-hold">HOLD</span>'


def render_stock_card(row, snap):
    if not snap:
        st.markdown(
            f'<div class="stock-card"><div class="stock-name">{row.symbol}</div><div class="stock-company">{row.company}</div><div class="stock-price">₹—</div><div class="stock-meta">Live quote unavailable</div></div>',
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        f'<div class="stock-card">'
        f'<div class="stock-name">{row.symbol}</div>'
        f'<div class="stock-company">{row.company}</div>'
        f'<div class="stock-price">{money(snap["price"])}</div>'
        f'<div class="stock-meta">Est. {money(snap["estimated"])} · {pct(snap["change_pct"])}</div>'
        f'<div style="margin-top:9px">{signal_badge(snap["signal"])} <span class="conf">Confidence {snap["confidence"]}%</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_metric(label, value):
    st.markdown(
        f'<div class="data-card"><div class="data-label">{label}</div><div class="data-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


# ============================================================
# Pages
# ============================================================
def home_page():
    st.markdown('<div class="brand">SMA</div><div class="page-title">Good morning</div><div class="page-sub">Your Indian market dashboard — simple, clean and data-first.</div>', unsafe_allow_html=True)

    # Market strip, Groww-inspired.
    market_html = '<div class="market-strip">'
    for name, ticker in INDEXES:
        q = index_snapshot(ticker)
        if q:
            cls = "up" if (q["change_pct"] or 0) >= 0 else "down"
            market_html += f'<div class="market-chip"><div class="mname">{name}</div><div class="mvalue">{money(q["price"])}</div><div class="mchange {cls}">{pct(q["change_pct"])}</div></div>'
        else:
            market_html += f'<div class="market-chip"><div class="mname">{name}</div><div class="mvalue">₹—</div><div class="mchange">Live data unavailable</div></div>'
    market_html += '</div>'
    st.markdown(market_html, unsafe_allow_html=True)

    st.markdown('<div class="hero"><div class="hero-title">Find a stock</div><div class="hero-sub">Search any NSE or BSE company to open its full analysis.</div></div>', unsafe_allow_html=True)
    search = st.text_input("Search stocks", placeholder="Search TCS, Reliance, Infosys, 20 Microns…", label_visibility="collapsed", key="home_search")
    if search.strip():
        match = resolve_stock(search)
        if match:
            st.session_state["analysis_query"] = match["symbol"]
            st.session_state["page"] = "Analysis"
            st.rerun()
        else:
            st.warning("No NSE/BSE stock found for that search.")

    st.markdown('<div class="section-title">Stocks to watch</div>', unsafe_allow_html=True)
    watch_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"]
    watch = UNIVERSE[UNIVERSE.symbol.isin(watch_symbols)].drop_duplicates("symbol").head(6)
    cols = st.columns(3)
    for i, (_, row) in enumerate(watch.iterrows()):
        with cols[i % 3]:
            render_stock_card(row, stock_snapshot(row.yahoo))

    st.markdown('<div class="section-title">Best signals right now</div>', unsafe_allow_html=True)
    candidates = UNIVERSE[UNIVERSE.exchange == "NSE"].head(18)
    picks = []
    for _, row in candidates.iterrows():
        snap = stock_snapshot(row.yahoo)
        if snap and snap.get("signal"):
            picks.append((row, snap))
    picks = sorted(picks, key=lambda x: x[1].get("confidence", 0), reverse=True)[:3]
    if picks:
        cols = st.columns(3)
        for i, (row, snap) in enumerate(picks):
            with cols[i]: render_stock_card(row, snap)
    else:
        st.info("Live market data is temporarily unavailable.")

    st.markdown('<div class="small-note" style="margin-top:22px">Estimated price and confidence are SMA technical estimates, not guaranteed future prices.</div>', unsafe_allow_html=True)


def all_stocks_page():
    st.markdown('<div class="brand">SMA</div><div class="page-title">All stocks</div><div class="page-sub">Complete active NSE + BSE universe with the same quote fields for every row.</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2.2, 1, 1])
    with c1:
        query = st.text_input("Search", placeholder="Search symbol or company", label_visibility="collapsed", key="all_search")
    with c2:
        exchange = st.selectbox("Exchange", ["All", "NSE", "BSE"], label_visibility="collapsed", key="all_exchange")
    with c3:
        sort_by = st.selectbox("Sort", ["Symbol", "Current Price", "Confidence", "Estimated Price"], label_visibility="collapsed", key="all_sort")

    df = UNIVERSE.copy()
    if exchange != "All": df = df[df.exchange == exchange]
    if query.strip():
        q = query.strip().lower()
        df = df[df.symbol.astype(str).str.lower().str.contains(q, regex=False, na=False) | df.company.astype(str).str.lower().str.contains(q, regex=False, na=False)]
    if sort_by == "Symbol": df = df.sort_values("symbol")

    st.markdown(f'<div class="small-note">{len(df):,} stocks in this view · Live OHLC data is loaded page-by-page to avoid rate limits.</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("No stocks match your search.")
        return

    page_size = 60
    max_page = max(1, math.ceil(len(df) / page_size))
    page = st.number_input("Page", min_value=1, max_value=max_page, value=1, step=1)
    page_df = df.iloc[(page - 1) * page_size : page * page_size].copy()

    # The page is fully populated with the requested fields. Each row is fetched once and cached.
    rows = []
    progress = st.progress(0, text="Loading live market data…")
    items = list(page_df.iterrows())
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(stock_snapshot, row.yahoo): (idx, row) for idx, row in items}
        done = 0
        for future in as_completed(futures):
            idx, row = futures[future]
            snap = future.result()
            rows.append({
                "Symbol": row.symbol,
                "Company": row.company,
                "Exchange": row.exchange,
                "Current Price": snap.get("price") if snap else None,
                "Estimated Price": snap.get("estimated") if snap else None,
                "Open": snap.get("open") if snap else None,
                "Close": snap.get("close") if snap else None,
                "High": snap.get("high") if snap else None,
                "Low": snap.get("low") if snap else None,
                "Confidence": snap.get("confidence") if snap else None,
                "Signal": snap.get("signal") if snap else None,
            })
            done += 1
            progress.progress(done / max(1, len(items)), text=f"Loading live market data… {done}/{len(items)}")
    progress.empty()

    table = pd.DataFrame(rows)
    if sort_by == "Current Price": table = table.sort_values("Current Price", na_position="last", ascending=False)
    elif sort_by == "Confidence": table = table.sort_values("Confidence", na_position="last", ascending=False)
    elif sort_by == "Estimated Price": table = table.sort_values("Estimated Price", na_position="last", ascending=False)

    # Keep the dataframe numeric for correct sorting/display, with clear names.
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current Price": st.column_config.NumberColumn("Current Price", format="₹%.2f"),
            "Estimated Price": st.column_config.NumberColumn("Estimated Price", format="₹%.2f"),
            "Open": st.column_config.NumberColumn("Open", format="₹%.2f"),
            "Close": st.column_config.NumberColumn("Close", format="₹%.2f"),
            "High": st.column_config.NumberColumn("High", format="₹%.2f"),
            "Low": st.column_config.NumberColumn("Low", format="₹%.2f"),
            "Confidence": st.column_config.NumberColumn("Confidence", format="%d%%"),
        },
    )
    st.markdown('<div class="small-note">Open/High/Low are the current trading-day values when supplied by Yahoo Finance. Close is the previous official close. When the market is closed, the current price reflects the latest available market price.</div>', unsafe_allow_html=True)


def analysis_page():
    st.markdown('<div class="brand">SMA</div><div class="page-title">Stock analysis</div><div class="page-sub">Search one stock — only that stock is shown here. No giant NSE/BSE list.</div>', unsafe_allow_html=True)

    default_query = st.session_state.get("analysis_query", "")
    query = st.text_input("Stock search", value=default_query, placeholder="Enter symbol or company name — TCS, 20 Microns, Reliance…", label_visibility="collapsed", key="analysis_search")
    analyze = st.button("Analyze stock", type="primary", use_container_width=False)
    if analyze or query.strip():
        match = resolve_stock(query)
        if not match:
            st.error("Stock not found in the NSE/BSE universe. Try the exact symbol or company name.")
            return
        st.session_state["analysis_query"] = match["symbol"]
        row = pd.Series(match)
        snap = stock_snapshot(row.yahoo)
        if not snap:
            st.error("Live market data could not be loaded for this stock. Please try again in a moment.")
            return

        change_cls = "up" if (snap.get("change_pct") or 0) >= 0 else "down"
        st.markdown(
            f'<div class="hero"><div class="hero-title">{row.symbol}</div><div class="hero-sub">{row.company} · {row.exchange}</div>'
            f'<div style="font-size:31px;font-weight:900;margin-top:18px">{money(snap["price"])}</div>'
            f'<div class="{change_cls}" style="font-size:13px;margin-top:3px">{pct(snap["change_pct"])}</div>'
            f'<div style="margin-top:13px">{signal_badge(snap["signal"])} <span style="margin-left:7px;color:#777;font-size:12px">Confidence {snap["confidence"]}%</span></div></div>',
            unsafe_allow_html=True,
        )

        cols = st.columns(6)
        metrics = [
            ("Current", money(snap["price"])),
            ("Estimated", money(snap["estimated"])),
            ("Open", money(snap["open"])),
            ("Close", money(snap["close"])),
            ("High", money(snap["high"])),
            ("Low", money(snap["low"])),
        ]
        for col, (label, value) in zip(cols, metrics):
            with col: render_metric(label, value)

        st.markdown('<div class="section-title">Price trend</div>', unsafe_allow_html=True)
        hist = historical(row.yahoo)
        if not hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist["close"], mode="lines", name="Close", line=dict(width=2)))
            fig.update_layout(height=330, margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified", xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            tech = technicals(hist).iloc[-1]
            c1, c2, c3, c4 = st.columns(4)
            with c1: render_metric("SMA 20", money(num(tech.get("sma20"))))
            with c2: render_metric("SMA 50", money(num(tech.get("sma50"))))
            with c3: render_metric("RSI 14", "—" if num(tech.get("rsi")) is None else f'{num(tech.get("rsi")):.1f}')
            with c4: render_metric("20D momentum", pct(((snap["price"] / hist["close"].iloc[-21]) - 1) * 100) if len(hist) >= 21 else None)

        st.markdown('<div class="section-title">Why this signal?</div>', unsafe_allow_html=True)
        st.markdown('<div class="data-card">', unsafe_allow_html=True)
        reasons = snap.get("reasons") or ["No additional technical reason is available."]
        for reason in reasons:
            st.markdown(f'<div class="reason">{reason}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="small-note" style="margin-top:12px">The estimated price, signal and confidence are calculated by SMA from recent price momentum and moving-average/RSI indicators. They are estimates, not investment guarantees.</div>', unsafe_allow_html=True)


def navigation():
    st.markdown('<div class="bottom-nav">', unsafe_allow_html=True)
    options = ["Home", "All Stocks", "Analysis"]
    current = st.session_state.get("page", "Home")
    selected = st.radio("Navigation", options, index=options.index(current), horizontal=True, label_visibility="collapsed", key="bottom_navigation")
    st.session_state["page"] = selected
    st.markdown('</div>', unsafe_allow_html=True)


if "page" not in st.session_state:
    st.session_state["page"] = "Home"

page = st.session_state["page"]
if page == "Home":
    home_page()
elif page == "All Stocks":
    all_stocks_page()
else:
    analysis_page()

navigation()
