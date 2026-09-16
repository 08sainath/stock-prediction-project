# SMA runtime launcher
# Loads the known-good SMA app from a commit ref, then applies the market-session
# estimator patch in memory. Using a commit SHA (not a blob SHA) keeps the raw URL valid.
import re
import urllib.request
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

import streamlit as st

SOURCE_URL = "https://raw.githubusercontent.com/08sainath/stock-prediction-project/3b96ac43c76c6b3a910fb258b0f4c025acb7f9b9/app.py"

try:
    from streamlit_autorefresh import st_autorefresh
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    if now.weekday() < 5 and dt_time(9, 0) <= now.time() < dt_time(15, 30):
        st_autorefresh(interval=60_000, key="sma_market_minute_refresh")
except Exception:
    pass

source = urllib.request.urlopen(SOURCE_URL, timeout=20).read().decode("utf-8")

new_estimator = r'''def estimate_signal(current, hist, current_return_pct=None, technical_override=None):
    if current is None:
        return None, None, None, []
    if technical_override is not None:
        technical_change = float(np.clip(technical_override, -6, 6))
        live_return = num(current_return_pct)
        expected_change = float(np.clip(live_return + 0.20 * technical_change, -15, 15)) if live_return is not None else technical_change
        estimated = current * (1 + expected_change / 100)
        signal = "BUY" if technical_change >= 1.5 else ("SELL" if technical_change <= -1.5 else "HOLD")
        confidence = int(np.clip(58 + abs(technical_change) * 4, 58, 92))
        return estimated, signal, confidence, [f"Morning technical bias: {technical_change:+.2f}%.", "Live price is refreshed during the market session.", "Estimated price uses the morning analysis as the intraday baseline."]
    if hist.empty or len(hist) < 20:
        return current, "HOLD", 50, ["Not enough recent history for a stronger technical estimate."]
    h = technicals(hist)
    last = h.iloc[-1]
    sma20 = num(last.get("sma20")); sma50 = num(last.get("sma50")); rsi = num(last.get("rsi"))
    momentum5 = ((current / h["close"].iloc[-6]) - 1) * 100 if len(h) >= 6 and h["close"].iloc[-6] else 0
    momentum20 = ((current / h["close"].iloc[-21]) - 1) * 100 if len(h) >= 21 and h["close"].iloc[-21] else 0
    trend = ((sma20 / sma50) - 1) * 100 if sma20 and sma50 else 0
    technical_change = float(np.clip(0.50 * momentum5 + 0.30 * momentum20 + 0.20 * trend, -6, 6))
    live_return = num(current_return_pct)
    expected_change = float(np.clip(live_return + 0.20 * technical_change, -15, 15)) if live_return is not None else technical_change
    estimated = current * (1 + expected_change / 100)
    reasons = [f"5-day momentum: {momentum5:+.2f}%.", f"20-day momentum: {momentum20:+.2f}%."]
    if sma20 and sma50:
        reasons.append("SMA20 is above SMA50, supporting the trend." if sma20 > sma50 else "SMA20 is below SMA50, showing weaker trend structure.")
    if rsi is not None:
        reasons.append(f"RSI is {rsi:.1f}.")
    signal = "BUY" if technical_change >= 1.5 and (rsi is None or rsi < 72) else ("SELL" if technical_change <= -1.5 or (rsi is not None and rsi > 78) else "HOLD")
    confidence = int(np.clip(58 + abs(technical_change) * 4 + min(8, len(h) / 40), 58, 92))
    return estimated, signal, confidence, reasons
'''
source = re.sub(r"def estimate_signal\(current, hist\):.*?(?=\n\n@st\.cache_data\(ttl=120, show_spinner=False\)\ndef stock_snapshot)", new_estimator, source, count=1, flags=re.S)

new_snapshot = r'''MARKET_TZ = ZoneInfo("Asia/Kolkata")
ANALYSIS_START = dt_time(9, 0)
ESTIMATE_START = dt_time(10, 0)
MARKET_CLOSE = dt_time(15, 30)

def _market_phase(now):
    if now.weekday() >= 5:
        return "closed"
    t = now.time()
    if ANALYSIS_START <= t < ESTIMATE_START:
        return "analysis"
    if ESTIMATE_START <= t < MARKET_CLOSE:
        return "estimate"
    return "closed"

@st.cache_data(ttl=86400, show_spinner=False)
def morning_analysis(ticker, session_date):
    q = yahoo_chart(ticker, "1d", "1m") or yahoo_chart(ticker, "5d", "1d")
    hist = historical(ticker)
    if not q:
        return None
    estimated, signal, confidence, reasons = estimate_signal(q["price"], hist, q.get("change_pct"))
    technical_bias = ((estimated / q["price"]) - 1) * 100 if estimated is not None and q.get("price") else 0.0
    return {"analysis_price": q.get("price"), "morning_return": q.get("change_pct"), "technical_bias": float(np.clip(technical_bias, -6, 6)), "signal": signal, "confidence": confidence, "reasons": reasons, "session_date": session_date}

@st.cache_data(ttl=20, show_spinner=False)
def _live_market_quote(ticker):
    return yahoo_chart(ticker, "1d", "1m") or yahoo_chart(ticker, "5d", "1d")

@st.cache_data(ttl=120, show_spinner=False)
def stock_snapshot(ticker):
    now = datetime.now(MARKET_TZ)
    phase = _market_phase(now)
    session_date = now.date().isoformat()
    if phase in ("analysis", "estimate"):
        q = _live_market_quote(ticker)
    else:
        q = yahoo_chart(ticker, "5d", "1d")
        if q and q.get("closes"):
            closes = [x for x in q["closes"] if x is not None]
            if closes:
                q["price"] = closes[-1]
                q["close"] = closes[-2] if len(closes) > 1 else None
                q["change"] = q["price"] - q["close"] if q["close"] not in (None, 0) else None
                q["change_pct"] = (q["change"] / q["close"] * 100) if q["change"] is not None and q["close"] not in (None, 0) else None
    if not q:
        return None
    hist = historical(ticker)
    morning = morning_analysis(ticker, session_date) if phase in ("analysis", "estimate") else None
    if phase == "estimate" and morning:
        estimated, signal, confidence, reasons = estimate_signal(q["price"], hist, q.get("change_pct"), morning.get("technical_bias"))
    elif phase == "analysis" and morning:
        estimated = morning.get("analysis_price") * (1 + morning.get("technical_bias", 0) / 100) if morning.get("analysis_price") else q.get("price")
        signal, confidence, reasons = morning.get("signal"), morning.get("confidence"), morning.get("reasons", [])
    else:
        estimated, signal, confidence, reasons = estimate_signal(q["price"], hist, q.get("change_pct"))
    latest = technicals(hist).iloc[-1] if not hist.empty else pd.Series(dtype=float)
    return {**q, "estimated": estimated, "signal": signal, "confidence": confidence, "reasons": reasons, "session_phase": phase, "analysis_date": session_date, "analysis_window": "09:00–10:00 IST" if phase in ("analysis", "estimate") else "Last completed session", "estimate_window": "10:00–15:00 IST" if phase == "estimate" else "Next market session", "sma20": num(latest.get("sma20")) if not latest.empty else None, "sma50": num(latest.get("sma50")) if not latest.empty else None, "rsi": num(latest.get("rsi")) if not latest.empty else None}
'''
source = re.sub(r"@st\.cache_data\(ttl=120, show_spinner=False\)\ndef stock_snapshot\(ticker\):.*?(?=\n\n# ============================================================\n# Market index quotes)", new_snapshot, source, count=1, flags=re.S)
source = source.replace("The estimated price, signal and confidence are calculated by SMA from recent price momentum and moving-average/RSI indicators. They are estimates, not investment guarantees.", "SMA runs daily analysis from 09:00–10:00 IST, then refreshes live prices and estimates from 10:00–15:00 IST using that morning baseline. Estimates are not investment guarantees.")
exec(compile(source, SOURCE_URL, "exec"), globals(), globals())
