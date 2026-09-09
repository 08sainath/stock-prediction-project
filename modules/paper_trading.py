import streamlit as st
import pandas as pd
from datetime import datetime

STARTING_CASH = 100000.0


def _init():
    if "paper_cash" not in st.session_state:
        st.session_state["paper_cash"] = STARTING_CASH
    if "paper_holdings" not in st.session_state:
        st.session_state["paper_holdings"] = {}
    if "paper_orders" not in st.session_state:
        st.session_state["paper_orders"] = []


def _money(v):
    return "₹—" if v is None else f"₹{float(v):,.2f}"


def _pct(v):
    return "—" if v is None else f"{float(v):+.2f}%"


def _current_price(symbol, resolve_stock, stock_snapshot):
    row = resolve_stock(symbol)
    if not row:
        return None, None
    snap = stock_snapshot(row["yahoo"])
    return (snap.get("price") if snap else None), row


def _record_order(side, row, qty, price):
    st.session_state["paper_orders"].insert(0, {
        "Time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "Side": side,
        "Symbol": row["symbol"],
        "Exchange": row["exchange"],
        "Qty": int(qty),
        "Price": float(price),
        "Value": float(qty * price),
    })


def render_paper_trading_page(resolve_stock, stock_snapshot):
    _init()
    st.markdown('<div class="brand">SMA</div><div class="page-title">Paper Trading</div><div class="page-sub">Practice buying and selling stocks with virtual money. No real money is used.</div>', unsafe_allow_html=True)

    holdings = st.session_state["paper_holdings"]
    cash = float(st.session_state["paper_cash"])

    current_values = []
    for symbol, pos in list(holdings.items()):
        price, row = _current_price(symbol, resolve_stock, stock_snapshot)
        if price is not None:
            current_values.append(float(pos["qty"]) * float(price))
    invested = sum(float(p["qty"]) * float(p["avg_price"]) for p in holdings.values())
    current_value = sum(current_values)
    total_value = cash + current_value
    total_pnl = current_value - invested
    return_pct = (total_pnl / invested * 100) if invested else 0.0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Virtual Cash", _money(cash))
    with m2:
        st.metric("Invested", _money(invested))
    with m3:
        st.metric("Portfolio Value", _money(total_value), _pct(return_pct))
    with m4:
        st.metric("P&L", _money(total_pnl))

    st.markdown('<div class="section-title">Buy / Sell</div>', unsafe_allow_html=True)
    left, right = st.columns([2, 1])
    with left:
        query = st.text_input("Stock", placeholder="Enter symbol or company name — TCS, Reliance…", key="paper_stock_search")
    with right:
        qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="paper_qty")

    match = resolve_stock(query) if query.strip() else None
    price = None
    if match:
        snap = stock_snapshot(match["yahoo"])
        price = snap.get("price") if snap else None
        if price is not None:
            st.markdown(f'<div class="data-card"><b>{match["symbol"]}</b> · {match["company"]} · {match["exchange"]}<br><span style="font-size:22px;font-weight:900">{_money(price)}</span> <span class="small-note">current market price</span></div>', unsafe_allow_html=True)
        else:
            st.warning("Current market price is unavailable. Try again in a moment.")
    elif query.strip():
        st.error("Stock not found. Try an exact NSE/BSE symbol or company name.")

    b1, b2, b3 = st.columns([1, 1, 2])
    with b1:
        buy = st.button("BUY", type="primary", use_container_width=True, disabled=not bool(match and price))
    with b2:
        sell = st.button("SELL", use_container_width=True, disabled=not bool(match and price))
    with b3:
        if st.button("Reset Paper Portfolio", use_container_width=True):
            st.session_state["paper_cash"] = STARTING_CASH
            st.session_state["paper_holdings"] = {}
            st.session_state["paper_orders"] = []
            st.rerun()

    if match and price and (buy or sell):
        symbol = match["symbol"]
        q = int(qty)
        trade_value = q * float(price)
        pos = holdings.get(symbol)

        if buy:
            if trade_value > float(st.session_state["paper_cash"]):
                st.error(f"Insufficient virtual cash. Required {_money(trade_value)}, available {_money(st.session_state['paper_cash'])}.")
            else:
                old_qty = int(pos["qty"]) if pos else 0
                old_avg = float(pos["avg_price"]) if pos else 0.0
                new_qty = old_qty + q
                new_avg = ((old_qty * old_avg) + trade_value) / new_qty
                holdings[symbol] = {"qty": new_qty, "avg_price": new_avg, "company": match["company"], "exchange": match["exchange"]}
                st.session_state["paper_cash"] -= trade_value
                _record_order("BUY", match, q, price)
                st.success(f"Bought {q} × {symbol} at {_money(price)}")
                st.rerun()

        if sell:
            owned = int(pos["qty"]) if pos else 0
            if owned < q:
                st.error(f"You only own {owned} share(s) of {symbol}.")
            else:
                remaining = owned - q
                if remaining == 0:
                    holdings.pop(symbol, None)
                else:
                    holdings[symbol]["qty"] = remaining
                st.session_state["paper_cash"] += trade_value
                _record_order("SELL", match, q, price)
                st.success(f"Sold {q} × {symbol} at {_money(price)}")
                st.rerun()

    st.markdown('<div class="section-title">Holdings</div>', unsafe_allow_html=True)
    if not holdings:
        st.info("No holdings yet. Search a stock above and place your first virtual BUY order.")
    else:
        rows = []
        for symbol, pos in holdings.items():
            live_price, _ = _current_price(symbol, resolve_stock, stock_snapshot)
            value = float(pos["qty"]) * float(live_price) if live_price is not None else None
            invested_pos = float(pos["qty"]) * float(pos["avg_price"])
            pnl = (value - invested_pos) if value is not None else None
            pnl_pct = (pnl / invested_pos * 100) if pnl is not None and invested_pos else None
            rows.append({
                "Symbol": symbol,
                "Company": pos["company"],
                "Qty": int(pos["qty"]),
                "Avg. Buy": float(pos["avg_price"]),
                "Current": float(live_price) if live_price is not None else None,
                "Invested": invested_pos,
                "Value": value,
                "P&L": pnl,
                "Return": pnl_pct,
            })
        table = pd.DataFrame(rows)
        st.dataframe(table, use_container_width=True, hide_index=True, column_config={
            "Avg. Buy": st.column_config.NumberColumn("Avg. Buy", format="₹%.2f"),
            "Current": st.column_config.NumberColumn("Current", format="₹%.2f"),
            "Invested": st.column_config.NumberColumn("Invested", format="₹%.2f"),
            "Value": st.column_config.NumberColumn("Value", format="₹%.2f"),
            "P&L": st.column_config.NumberColumn("P&L", format="₹%.2f"),
            "Return": st.column_config.NumberColumn("Return", format="%.2f%%"),
        })

    st.markdown('<div class="section-title">Order History</div>', unsafe_allow_html=True)
    orders = st.session_state["paper_orders"]
    if orders:
        st.dataframe(pd.DataFrame(orders), use_container_width=True, hide_index=True, column_config={
            "Price": st.column_config.NumberColumn("Price", format="₹%.2f"),
            "Value": st.column_config.NumberColumn("Value", format="₹%.2f"),
        })
    else:
        st.info("No paper orders yet.")

    st.markdown('<div class="small-note" style="margin-top:14px">Paper trading uses virtual ₹1,00,000. Orders are simulated at the latest available market quote; this does not place real NSE/BSE orders.</div>', unsafe_allow_html=True)
