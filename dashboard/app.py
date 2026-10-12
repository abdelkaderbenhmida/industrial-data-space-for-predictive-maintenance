import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Industrial Data Space", page_icon="🏭", layout="wide")


def get_api(path):
    base_url = os.environ.get("DASHBOARD_API_URL", "http://localhost:8000")
    response = requests.get(f"{base_url}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


st.title("🏭 Industrial Data Space")
st.caption("Live factory telemetry and real federated-learning evaluation results")
if st.button("Refresh"):
    st.rerun()

try:
    factories = get_api("/api/factories")
    alerts = get_api("/api/alerts?limit=10")
    edc_status = get_api("/api/edc/status")
except requests.RequestException as exc:
    st.error(f"Dashboard API is unavailable: {exc}")
    st.stop()

online = sum(factory["status"] == "connected" for factory in factories)
latest_readings = [factory["last_reading"] for factory in factories if factory["last_reading"]]
one, two, three = st.columns(3)
one.metric("Factories reporting", f"{online} / {len(factories)}")
two.metric("Active alerts", len(alerts))
three.metric("Latest telemetry", latest_readings[-1]["timestamp"] if latest_readings else "Waiting")

st.subheader("EDC connectors")
edc_columns = st.columns(max(len(edc_status), 1))
for column, connector in zip(edc_columns, edc_status):
    state = connector.get("status", "unavailable")
    label = connector.get("connector_name") or connector.get("endpoint", "connector")
    column.metric(label, state.upper(), f"{connector.get('assets', 0)} assets")

st.subheader("Factory telemetry")
for factory in factories:
    st.markdown(f"### {factory['factory_id']}")
    try:
        sensor_data = get_api(f"/api/factories/{factory['factory_id']}/sensors?limit=100")
    except requests.HTTPError:
        st.info("Waiting for MQTT telemetry from this factory.")
        continue
    frame = pd.DataFrame(sensor_data["recent_readings"])
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        st.plotly_chart(
            px.line(frame, x="timestamp", y=["temperature", "vibrations", "pressure", "humidity", "power_consumption"],
                    title="Sensor trend"),
            use_container_width=True,
        )

st.subheader("Federated model evaluation")
try:
    performance = get_api("/api/model/performance")
except requests.HTTPError:
    st.info("Metrics will appear after the first federated training round.")
else:
    history = pd.DataFrame(performance["history"])
    current = performance["current_model"]
    accuracy, precision, recall, f1 = st.columns(4)
    accuracy.metric("Accuracy", f"{current['accuracy']:.1%}")
    precision.metric("Precision", f"{current['precision']:.1%}")
    recall.metric("Recall", f"{current['recall']:.1%}")
    f1.metric("F1 score", f"{current['f1_score']:.1%}")
    st.plotly_chart(px.line(history, x="round", y=["accuracy", "precision", "recall", "f1_score"], markers=True), use_container_width=True)

st.subheader("Maintenance alerts")
if alerts:
    st.dataframe(pd.DataFrame(alerts), use_container_width=True, hide_index=True)
else:
    st.success("No maintenance alerts from received telemetry.")
