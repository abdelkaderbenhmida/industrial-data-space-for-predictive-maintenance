import streamlit as st
import time
from components import render_factory_status, render_sensor_charts, render_model_metrics, render_alerts

st.set_page_config(
    page_title="Industrial Data Space Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid #0f3460;
        color: white;
    }
    .status-ok { color: #00e676; }
    .status-warn { color: #ffc107; }
    .status-crit { color: #ff5252; }
    div[data-testid="stMetric"] {
        background: #0e1117;
        border: 1px solid #262730;
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="stMetric"] label {
        color: #a0a0a0;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff;
    }
    .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "api_base" not in st.session_state:
    st.session_state.api_base = "http://localhost:8000"

with st.sidebar:
    st.title("🏭 Controls")
    st.divider()
    api_url = st.text_input("API Base URL", value=st.session_state.api_base)
    st.session_state.api_base = api_url
    refresh_rate = st.slider("Refresh interval (s)", 5, 30, 5)
    st.divider()
    if st.button("▶ Start Simulation", use_container_width=True):
        st.toast("Simulation start requested", icon="▶")
    if st.button("⏹ Stop Simulation", use_container_width=True):
        st.toast("Simulation stop requested", icon="⏹")
    st.divider()
    st.caption("Industrial Data Space v1.0")

header_col, clock_col = st.columns([5, 1])
with header_col:
    st.title("🏭 Industrial Data Space Dashboard")
with clock_col:
    clock_placeholder = st.empty()

status_col, alerts_col, model_col, uptime_col = st.columns(4)
status_placeholder = status_col.empty()
alerts_placeholder = alerts_col.empty()
model_placeholder = model_col.empty()
uptime_placeholder = uptime_col.empty()

factory_col, chart_col = st.columns([1, 2])
factory_placeholder = factory_col.empty()
chart_placeholder = chart_col.empty()

metrics_col, alerts_detail_col = st.columns(2)
metrics_placeholder = metrics_col.empty()
alerts_detail_placeholder = alerts_detail_col.empty()

footer = st.container()
with footer:
    st.divider()
    last_refresh = st.empty()

iteration = 0
while True:
    iteration += 1
    from datetime import datetime
    now = datetime.now()

    with clock_placeholder.container():
        st.markdown(
            f"<div style='text-align:right;font-size:1.1rem;color:#a0a0a0;'>"
            f"🕐 {now.strftime('%H:%M:%S')}"
            f"</div>",
            unsafe_allow_html=True,
        )

    try:
        render_factory_status(factory_placeholder)
    except Exception:
        factory_placeholder.warning("Factory data unavailable")

    try:
        render_sensor_charts(chart_placeholder)
    except Exception:
        chart_placeholder.warning("Sensor data unavailable")

    try:
        render_model_metrics(metrics_placeholder)
    except Exception:
        metrics_placeholder.warning("Model metrics unavailable")

    try:
        render_alerts(alerts_detail_placeholder)
    except Exception:
        alerts_detail_placeholder.warning("Alerts unavailable")

    with status_placeholder.container():
        st.metric(label="Factories Online", value="3 / 3")
    with alerts_placeholder.container():
        st.metric(label="Active Alerts", value="2")
    with model_placeholder.container():
        st.metric(label="Model Accuracy", value="94.2%")
    with uptime_placeholder.container():
        st.metric(label="Uptime", value=f"{iteration * refresh_rate}s")

    with last_refresh.container():
        st.caption(f"Last refresh: {now.strftime('%H:%M:%S')} | Iteration {iteration}")

    time.sleep(refresh_rate)
    st.rerun()
