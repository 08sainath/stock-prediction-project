from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

imp = "from modules.paper_trading import render_paper_trading_page\n"
if imp not in s:
    marker = "import plotly.graph_objects as go\n"
    if marker not in s:
        raise SystemExit("plotly import marker not found")
    s = s.replace(marker, marker + imp, 1)

s = s.replace('options = ["Home", "All Stocks", "Analysis"]', 'options = ["Home", "All Stocks", "Analysis", "Paper Trading"]')

old_home = '''    if nav != "Home":\n        if nav == "All Stocks":\n            all_stocks_page()\n        else:\n            analysis_page()\n        return\n'''
new_home = '''    if nav != "Home":\n        if nav == "All Stocks":\n            all_stocks_page()\n        elif nav == "Analysis":\n            analysis_page()\n        else:\n            render_paper_trading_page(resolve_stock, stock_snapshot)\n        return\n'''
if old_home not in s:
    raise SystemExit("home navigation block not found")
s = s.replace(old_home, new_home, 1)

old_bottom = '''page = st.session_state["page"]\nif page == "Home":\n    home_page()\nelif page == "All Stocks":\n    all_stocks_page()\nelse:\n    analysis_page()\n'''
new_bottom = '''page = st.session_state["page"]\nif page == "Home":\n    home_page()\nelif page == "All Stocks":\n    all_stocks_page()\nelif page == "Analysis":\n    analysis_page()\nelse:\n    render_paper_trading_page(resolve_stock, stock_snapshot)\n'''
if old_bottom not in s:
    raise SystemExit("main page routing block not found")
s = s.replace(old_bottom, new_bottom, 1)

p.write_text(s, encoding="utf-8")
print("paper trading integrated")
