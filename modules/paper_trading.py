import json
from datetime import datetime

import pandas as pd
import streamlit as st
from modules.mobile_css import render_mobile_paper_css

STARTING_CASH = 100000.0


def _default_portfolio():
    return {"paper_cash": STARTING_CASH, "paper_holdings": {}, "paper_orders": [], "paper_watchlist": [], "paper_realized_pnl": 0.0, "paper_selected_stock": ""}


def _persist():
    st.session_state["paper_saved_payload"] = json.dumps({k: st.session_state.get(k, v) for k, v in _default_portfolio().items()}, ensure_ascii=False)


def _init():
    if st.session_state.get("paper_storage_loaded"):
        return
    defaults = _default_portfolio()
    try:
        raw = st.session_state.get("paper_saved_payload")
        if raw:
            loaded = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(loaded, dict):
                defaults.update({k: loaded[k] for k in defaults if k in loaded})
    except Exception:
        pass
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
    st.session_state["paper_orders"].insert(0, {"Time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"), "Side": side, "Symbol": row["symbol"], "Exchange": row["exchange"], "Qty": int(qty), "Price": float(price), "Value": float(qty * price)})


def _add_watchlist(row):
    if not any(x["symbol"] == row["symbol"] and x["exchange"] == row["exchange"] for x in st.session_state["paper_watchlist"]):
        st.session_state["paper_watchlist"].append({"symbol": row["symbol"], "company": row["company"], "exchange": row["exchange"], "yahoo": row["yahoo"]})


def _remove_watchlist(symbol, exchange):
    st.session_state["paper_watchlist"] = [x for x in st.session_state["paper_watchlist"] if not (x["symbol"] == symbol and x["exchange"] == exchange)]


def render_paper_trading_page(resolve_stock, stock_snapshot):
    _init()
    render_mobile_paper_css()
    st.markdown('<div class="brand">SMA</div><div class="page-title">Paper Trading</div><div class="page-sub">Search real NSE/BSE stocks, add them to your watchlist, and trade with virtual money using the latest available market quote.</div>', unsafe_allow_html=True)
    holdings = st.session_state["paper_holdings"]
    cash = float(st.session_state["paper_cash"])

    r1, r2 = st.columns([1, 5])
    with r1:
        if st.button("↻ Refresh Prices", use_container_width=True):
            try: stock_snapshot.clear()
            except Exception: pass
            st.rerun()
    with r2: st.caption("Quotes use the app's market-data source. Paper orders never reach NSE/BSE.")

    portfolio_rows, current_value, invested = [], 0.0, 0.0
    for symbol, pos in list(holdings.items()):
        live_price, _ = _current_price(symbol, resolve_stock, stock_snapshot)
        qty = int(pos["qty"]); invested_pos = qty * float(pos["avg_price"]); invested += invested_pos
        value = qty * float(live_price) if live_price is not None else None
        if value is not None: current_value += value
        portfolio_rows.append((symbol, pos, live_price, value, invested_pos))
    unrealized_pnl = current_value - invested; realized_pnl = float(st.session_state["paper_realized_pnl"]); total_pnl = unrealized_pnl + realized_pnl; total_value = cash + current_value; return_pct = (total_pnl / invested * 100) if invested else 0.0
    m1,m2,m3,m4,m5=st.columns(5); m1.metric("Available Cash",_money(cash)); m2.metric("Invested",_money(invested)); m3.metric("Holdings Value",_money(current_value)); m4.metric("Portfolio Value",_money(total_value)); m5.metric("Total P&L",_money(total_pnl),_pct(return_pct))

    st.markdown('<div class="section-title">Search & Trade</div>', unsafe_allow_html=True)
    query=st.text_input("Search stocks",value=st.session_state.get("paper_selected_stock",""),placeholder="Search TCS, Reliance, Infosys, HDFC Bank…",key="paper_stock_search")
    match=resolve_stock(query) if query.strip() else None; price=None
    if match:
        snap=stock_snapshot(match["yahoo"]); price=snap.get("price") if snap else None; change=snap.get("change_pct") if snap else None
        if price is not None:
            c1,c2,c3,c4=st.columns([2.4,1.2,1.2,1.2]); c1.markdown(f'<div class="data-card"><b>{match["symbol"]}</b> · {match["company"]}<br><span class="small-note">{match["exchange"]}</span></div>',unsafe_allow_html=True); c2.metric("Live Price",_money(price)); c3.metric("Day Change",_pct(change))
            watched=any(x["symbol"]==match["symbol"] and x["exchange"]==match["exchange"] for x in st.session_state["paper_watchlist"])
            if watched:
                if c4.button("★ Watching",use_container_width=True,key="unwatch_search"): _remove_watchlist(match["symbol"],match["exchange"]); _persist(); st.rerun()
            elif c4.button("☆ Add Watchlist",use_container_width=True,key="watch_search"): _add_watchlist(match); _persist(); st.rerun()
        else: st.warning("Live price is temporarily unavailable. Press Refresh Prices and try again.")
    elif query.strip(): st.error("Stock not found. Try an NSE/BSE symbol or company name.")

    if match and price is not None:
        q1,q2,q3=st.columns([1,1,3]); qty=q1.number_input("Quantity",min_value=1,value=1,step=1,key="paper_qty"); trade_value=int(qty)*float(price); q2.metric("Order Value",_money(trade_value)); buy,sell=q3.columns(2); buy_clicked=buy.button("BUY",type="primary",use_container_width=True,key="paper_buy"); sell_clicked=sell.button("SELL",use_container_width=True,key="paper_sell")
        if buy_clicked or sell_clicked:
            symbol,q,pos=match["symbol"],int(qty),holdings.get(match["symbol"]); trade_value=q*float(price)
            if buy_clicked:
                if trade_value>float(st.session_state["paper_cash"]): st.error(f"Insufficient virtual cash. Required {_money(trade_value)}, available {_money(st.session_state['paper_cash'])}.")
                else:
                    old_qty,old_avg=(int(pos["qty"]),float(pos["avg_price"])) if pos else (0,0.0); new_qty=old_qty+q; holdings[symbol]={"qty":new_qty,"avg_price":((old_qty*old_avg)+trade_value)/new_qty,"company":match["company"],"exchange":match["exchange"],"yahoo":match["yahoo"]}; st.session_state["paper_cash"]-=trade_value; _record_order("BUY",match,q,price); _persist(); st.success(f"Bought {q} × {symbol} at {_money(price)}"); st.rerun()
            else:
                owned=int(pos["qty"]) if pos else 0
                if owned<q: st.error(f"You only own {owned} share(s) of {symbol}.")
                else:
                    realized=(float(price)-float(pos["avg_price"]))*q; st.session_state["paper_realized_pnl"]+=realized; holdings.pop(symbol,None) if owned==q else holdings[symbol].update({"qty":owned-q}); st.session_state["paper_cash"]+=trade_value; _record_order("SELL",match,q,price); _persist(); st.success(f"Sold {q} × {symbol} at {_money(price)} · Realized P&L {_money(realized)}"); st.rerun()

    st.markdown('<div class="section-title">Watchlist</div>',unsafe_allow_html=True)
    watchlist=st.session_state["paper_watchlist"]
    if not watchlist: st.info("Your Watchlist is empty. Search a stock above and add it.")
    else:
        for i,item in enumerate(list(watchlist)):
            live=stock_snapshot(item["yahoo"]); lp=live.get("price") if live else None; dc=live.get("change_pct") if live else None; c1,c2,c3,c4=st.columns([2.6,1.3,1.2,1]); c1.markdown(f'**{item["symbol"]}** · {item["company"]} · {item["exchange"]}'); c2.write(_money(lp)); c3.write(_pct(dc))
            if c4.button("Remove",key=f"remove_watch_{i}",use_container_width=True): _remove_watchlist(item["symbol"],item["exchange"]); _persist(); st.rerun()

    st.markdown('<div class="section-title">Holdings</div>',unsafe_allow_html=True)
    if not portfolio_rows: st.info("No holdings yet. Search a stock and place a virtual BUY order.")
    else:
        rows=[]
        for symbol,pos,lp,value,inv in portfolio_rows:
            pnl=(value-inv) if value is not None else None; pp=(pnl/inv*100) if pnl is not None and inv else None; rows.append({"Symbol":symbol,"Company":pos["company"],"Exchange":pos["exchange"],"Qty":int(pos["qty"]),"Avg Buy":float(pos["avg_price"]),"Live Price":float(lp) if lp is not None else None,"Invested":inv,"Current Value":value,"P&L":pnl,"Return":pp})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,column_config={"Avg Buy":st.column_config.NumberColumn(format="₹%.2f"),"Live Price":st.column_config.NumberColumn(format="₹%.2f"),"Invested":st.column_config.NumberColumn(format="₹%.2f"),"Current Value":st.column_config.NumberColumn(format="₹%.2f"),"P&L":st.column_config.NumberColumn(format="₹%.2f"),"Return":st.column_config.NumberColumn(format="%.2f%%")})

    st.markdown('<div class="section-title">Order History</div>',unsafe_allow_html=True); orders=st.session_state["paper_orders"]
    if orders: st.dataframe(pd.DataFrame(orders),use_container_width=True,hide_index=True)
    else: st.info("No paper orders yet.")
    st.markdown('<div class="small-note" style="margin-top:14px">Paper trading starts with virtual ₹1,00,000. Orders are simulated; no real NSE/BSE order is placed. Data is retained for the active Streamlit session.</div>',unsafe_allow_html=True)
    if st.button("Reset Paper Portfolio",use_container_width=True,key="reset_paper"):
        for key,value in _default_portfolio().items(): st.session_state[key]=value
        _persist(); st.rerun()
