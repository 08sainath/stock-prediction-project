from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')
start = s.index('def navigation():')
end = s.index('\n\nif "page" not in st.session_state:', start)
new = '''def navigation():
    options = ["Home", "All Stocks", "Analysis", "Paper Trading"]

    def _change_page():
        st.session_state["page"] = st.session_state["bottom_navigation"]

    current = st.session_state.get("page", "Home")
    if current not in options:
        current = "Home"
        st.session_state["page"] = current

    # Keep the widget synchronized with the actual page before rendering it.
    if st.session_state.get("bottom_navigation") not in options:
        st.session_state["bottom_navigation"] = current

    st.markdown('<div class="bottom-nav">', unsafe_allow_html=True)
    st.radio(
        "Navigation",
        options,
        horizontal=True,
        label_visibility="collapsed",
        key="bottom_navigation",
        on_change=_change_page,
    )
    st.markdown('</div>', unsafe_allow_html=True)
'''
p.write_text(s[:start] + new + s[end:], encoding='utf-8')
print('navigation fixed')
