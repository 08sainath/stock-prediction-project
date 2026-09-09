import json
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_local_storage import LocalStorage

STARTING_CASH = 100000.0
STORAGE_KEY = "sma_paper_trading_v1"


@st.cache_resource

def _local_storage():
    return LocalStorage()


def _default_portfolio():
    return {
        "paper_cash": STARTING_CASH,
        "paper_holdings": {},
        "paper_orders": [],
        "paper_watchlist": [],
        "paper_realized_pnl": 0.0,
        "paper_selected_stock": "",
    }


def _persist():
    payload = {
        "paper_cash": float(st.session_state.get("paper_cash", STARTING_CASH)),
        "paper_holdings": st.session_state.get("paper_holdings", {}),
        "paper_orders": st.session_state.get("paper_orders", []),
        "paper_watchlist": st.session_state.get("paper_watchlist", []),
        "paper_realized_pnl": float(st.session_state.get("paper_realized_pnl", 0.0)),
        "paper_selected_stock": st.session_state.get("paper_selected_stock", ""),
    }
    try:
        _local_storage().setItem(STORAGE_KEY, json.dumps(payload, ensure_ascii=False))
    except Exception:
        # The app still works with Streamlit session state if browser storage is unavailable.
        pass


def _init():
    if st.session_state.get("paper_storage_loaded"):
        return

    defaults = _default_portfolio()
    loaded = None
    try:
        raw = _local_storage().getItem(STORAGE_KEY)
        if raw:
            loaded = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        loaded = None

    if isinstance(loaded, dict):
        defaults.update({k: loaded[k] for k in defaults if k in loaded})

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    st.session_state["paper_storage_loaded"] = True


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


def _add_watchlist(row):
    watchlist = st.session_state["paper_watchlist"]
    symbol = row["symbol"]
    if not any(x["symbol"] == symbol and x["exchange"] == row["exchange"] for x in watchlist):
        watchlist.append({
            "symbol": symbol,
            "company": row["company"],
            "exchange": row["exchange"],
            "yahoo": row["yahoo"],
        })


def _remove_watchlist(symbol, exchange):
    st.session_state["paper_watchlist"] = [
        x for x in st.session_state["paper_watchlist"]
        if not (x["symbol"] == symbol and x["exchange"] == exchange)
    ]


def render_paper_trading_page(resolve_stock, stock_snapshot):
    _init()

    st.markdown(
        '<div class="brand">SMA</div>'
        '<div class="page-title">Paper Trading</div>'
        '<div class="page-sub">Search real NSE/BSE stocks, add them to your watchlist, and trade with virtual money using the latest available market quote.</div>',
        unsafe_allow_html=True,
    )

    holdings = st.session_state["paper_holdings"]
    cash = float(st.session_state["paper_cash"])

    r1, r2 = st.columns([1, 5])
    with r1:
        if st.button("↻ Refresh Prices", use_container_width=True):
            try:
                stock_snapshot.clear()
            except Exception:
                pass
            st.rerun()
    with r2:
        st.caption("Quotes are refreshed from the app's market-data source. Paper orders never reach NSE/BSE.")

    portfolio_rows = []
    current_value = 0.0
    invested = 0.0
    for symbol, pos in list(holdings.items()):
        live_price, _ = _current_price(symbol, resolve_stock, stock_snapshot)
        qty = int(pos["qty"])
        invested_pos = qty * float(pos["avg_price"])
        invested += invested_pos
        value = qty * float(live_price) if live_price is not None else None
        if value is not None:
            current_value += value
        portfolio_rows.append((symbol, pos, live_price, value, invested_pos))

    unrealized_pnl = current_value - invested
    realized_pnl = float(st.session_state["paper_realized_pnl"])
    total_pnl = unrealized_pnl + realized_pnl
    total_value = cash + current_value
    return_pct = (total_pnl / invested * 100) if invested else 0.0

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Available Cash", _money(cash))
    with m2:
        st.metric("Invested", _money(invested))
    with m3:
        st.metric("Holdings Value", _money(current_value))
    with m4:
        st.metric("Portfolio Value", _money(total_value))
    with m5:
        st.metric("Total P&L", _money(total_pnl), _pct(return_pct))

    st.markdown('<div class="section-title">Search & Trade</div>', unsafe_allow_html=True)
    query = st.text_input(
        "Search stocks",
        value=st.session_state.get("paper_selected_stock", ""),
        placeholder="Search TCS, Reliance, Infosys, HDFC Bank…",
        key="paper_stock_search",
    )

    match = resolve_stock(query) if query.strip() else None
    price = None
    if match:
        snap = stock_snapshot(match["yahoo"])
        price = snap.get("price") if snap else None
        change = snap.get("change_pct") if snap else None
        if price is not None:
            c1, c2, c3, c4 = st.columns([2.4, 1.2, 1.2, 1.2])
            with c1:
                st.markdown(
                    f'<div class="data-card"><b>{match["symbol"]}</b> · {match["company"]}<br>'
                    f'<span class="small-note">{match["exchange"]}</span></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                st.metric("Live Price", _money(price))
            with c3:
                st.metric("Day Change", _pct(change))
            with c4:
                is_watched = any(x["symbol"] == match["symbol"] and x["exchange"] == match["exchange"] for x in st.session_state["paper_watchlist"])
                if is_watched:
                    if st.button("★ Watching", use_container_width=True, key="unwatch_search"):
                        _remove_watchlist(match["symbol"], match["exchange"])
                        _persist()
                        st.rerun()
                else:
                    if st.button("☆ Add Watchlist", use_container_width=True, key="watch_search"):
                        _add_watchlist(match)
                        _persist()
                        st.success(f"{match['symbol']} added to Watchlist")
                        st.rerun()
        else:
            st.warning("Live price is temporarily unavailable. Press Refresh Prices and try again.")
    elif query.strip():
        st.error("Stock not found. Try an NSE/BSE symbol or company name.")

    if match and price is not None:
        q1, q2, q3 = st.columns([1, 1, 3])
        with q1:
            qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="paper_qty")
        with q2:
            trade_value = int(qty) * float(price)
            st.metric("Order Value", _money(trade_value))
        with q3:
            st.write("")
            buy, sell = st.columns(2)
            with buy:
                buy_clicked = st.button("BUY", type="primary", use_container_width=True, key="paper_buy")
            with sell:
                sell_clicked = st.button("SELL", use_container_width=True, key="paper_sell")

        if buy_clicked or sell_clicked:
            symbol = match["symbol"]
            q = int(qty)
            trade_value = q * float(price)
            pos = holdings.get(symbol)

            if buy_clicked:
                if trade_value > float(st.session_state["paper_cash"]):
                    st.error(f"Insufficient virtual cash. Required {_money(trade_value)}, available {_money(st.session_state['paper_cash'])}.")
                else:
                    old_qty = int(pos["qty"]) if pos else 0
                    old_avg = float(pos["avg_price"]) if pos else 0.0
                    new_qty = old_qty + q
                    new_avg = ((old_qty * old_avg) + trade_value) / new_qty
                    holdings[symbol] = {
                        "qty": new_qty,
                        "avg_price": new_avg,
                        "company": match["company"],
                        "exchange": match["exchange"],
                        "yahoo": match["yahoo"],
                    }
                    st.session_state["paper_cash"] -= trade_value
                    _record_order("BUY", match, q, price)
                    _persist()
                    st.success(f"Bought {q} × {symbol} at {_money(price)}")
                    st.rerun()

            if sell_clicked:
                owned = int(pos["qty"]) if pos else 0
                if owned < q:
                    st.error(f"You only own {owned} share(s) of {symbol}.")
                else:
                    avg = float(pos["avg_price"])
                    realized = (float(price) - avg) * q
                    st.session_state["paper_realized_pnl"] += realized
                    remaining = owned - q
                    if remaining == 0:
                        holdings.pop(symbol, None)
                    else:
                        holdings[symbol]["qty"] = remaining
                    st.session_state["paper_cash"] += trade_value
                    _record_order("SELL", match, q, price)
                    _persist()
                    st.success(f"Sold {q} × {symbol} at {_money(price)} · Realized P&L {_money(realized)}")
                    st.rerun()

    st.markdown('<div class="section-title">Watchlist</div>', unsafe_allow_html=True)
    watchlist = st.session_state["paper_watchlist"]
    if not watchlist:
        st.info("Your Watchlist is empty. Search any NSE/BSE stock above and click ☆ Add Watchlist.")
    else:
        for i, item in enumerate(list(watchlist)):
            live = stock_snapshot(item["yahoo"])
            live_price = live.get("price") if live else None
            day_change = live.get("change_pct") if live else None
            c1, c2, c3, c4 = st.columns([2.6, 1.3, 1.2, 1])
            with c1:
                st.markdown(f'**{item["symbol"]}**  ·  {item["company"]}  ·  {item["exchange"]}')
            with c2:
                st.write(_money(live_price))
            with c3:
                st.write(_pct(day_change))
            with c4:
                if st.button("Remove", key=f"remove_watch_{i}", use_container_width=True):
                    _remove_watchlist(item["symbol"], item["exchange"])
                    _persist()
                    st.rerun()

    st.markdown('<div class="section-title">Holdings</div>', unsafe_allow_html=True)
    if not portfolio_rows:
        st.info("No holdings yet. Search a stock and place a virtual BUY order.")
    else:
        rows = []
        for symbol, pos, live_price, value, invested_pos in portfolio_rows:
            pnl = (value - invested_pos) if value is not None else None
            pnl_pct = (pnl / invested_pos * 100) if pnl is not None and invested_pos else None
            rows.append({
                "Symbol": symbol,
                "Company": pos["company"],
                "Exchange": pos["exchange"],
                "Qty": int(pos["qty"]),
                "Avg Buy": float(pos["avg_price"]),
                "Live Price": float(live_price) if live_price is not None else None,
                "Invested": invested_pos,
                "Current Value": value,
                "P&L": pnl,
                "Return": pnl_pct,
            })
        table = pd.DataFrame(rows)
        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Avg Buy": st.column_config.NumberColumn("Avg Buy", format="₹%.2f"),
                "Live Price": st.column_config.NumberColumn("Live Price", format="₹%.2f"),
                "Invested": st.column_config.NumberColumn("Invested", format="₹%.2f"),
                "Current Value": st.column_config.NumberColumn("Current Value", format="₹%.2f"),
                "P&L": st.column_config.NumberColumn("P&L", format="₹%.2f"),
                "Return": st.column_config.NumberColumn("Return", format="%.2f%%"),
            },
        )

    st.markdown('<div class="section-title">Order History</div>', unsafe_allow_html=True)
    orders = st.session_state["paper_orders"]
    if orders:
        st.dataframe(
            pd.DataFrame(orders),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Price": st.column_config.NumberColumn("Price", format="₹%.2f"),
                "Value": st.column_config.NumberColumn("Value", format="₹%.2f"),
            },
        )
    else:
        st.info("No paper orders yet.")

    st.markdown(
        '<div class="small-note" style="margin-top:14px">Paper trading starts with virtual ₹1,00,000. BUY/SELL executions are simulated using the latest available quote; no real NSE/BSE order is placed. Watchlist, holdings, cash, orders and P&L are saved in this browser and survive page navigation and browser refresh.</div>',
        unsafe_allow_html=True,
    )

    if st.button("Reset Paper Portfolio", use_container_width=True, key="reset_paper"):
        for key, value in _default_portfolio().items():
            st.session_state[key] = value
        _persist()
        st.rerun()
