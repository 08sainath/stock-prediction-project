import streamlit as st

def render_mobile_paper_css():
    st.markdown('''<style>
[data-testid="stMetric"] { background:#fff !important; border:1px solid #e9e3da !important; border-radius:14px !important; padding:10px !important; min-height:70px !important; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color:#77736d !important; opacity:1 !important; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div { color:#171717 !important; opacity:1 !important; }
[data-testid="stMetricDelta"], [data-testid="stMetricDelta"] div { opacity:1 !important; }
.stButton > button { min-height:44px !important; color:#171717 !important; background:#fff !important; border:1px solid #d9d3ca !important; border-radius:10px !important; }
.stButton > button p { color:inherit !important; }
.stButton > button[kind="primary"] { color:#fff !important; background:#171717 !important; border-color:#171717 !important; }
.stTextInput input, .stNumberInput input { color:#171717 !important; background:#fff !important; border-color:#d9d3ca !important; }
.stTextInput input::placeholder { color:#77736d !important; opacity:1 !important; }
@media (max-width:430px) {
  [data-testid="stMetric"] { width:100% !important; box-sizing:border-box !important; margin-bottom:2px !important; }
  [data-testid="stMetricValue"] { font-size:19px !important; }
  [data-testid="stMetricLabel"] { font-size:11px !important; }
  .stButton > button { width:100% !important; }
  .bottom-nav { z-index:9999 !important; }
  .bottom-nav label { color:#171717 !important; opacity:1 !important; }
  .bottom-nav label p, .bottom-nav label span { color:inherit !important; opacity:1 !important; }
  .bottom-nav label:has(input:checked) { color:#fff !important; background:#171717 !important; }
}
</style>''', unsafe_allow_html=True)
