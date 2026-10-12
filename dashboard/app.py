"""Industrial Data Space operations dashboard.

Uses the FastAPI service when available and falls back to deterministic demo data
so the interface remains useful in a local demo without MQTT or EDC running.
"""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


st.set_page_config(page_title="IDS · Operations Console", page_icon="IDS", layout="wide", initial_sidebar_state="expanded")

COLORS = {"bg": "#0b1118", "surface": "#111b26", "surface_2": "#162432", "border": "rgba(148, 163, 184, .16)", "text": "#eef4f8", "muted": "#8da1b2", "green": "#46d39a", "amber": "#f4b860", "red": "#f07178", "blue": "#66b6ff", "purple": "#ad9cff"}

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --bg:#0b1118; --surface:#111b26; --surface2:#162432; --border:rgba(148,163,184,.16); --text:#eef4f8; --muted:#8da1b2; --green:#46d39a; --amber:#f4b860; --red:#f07178; --blue:#66b6ff; }
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    .stApp { background: radial-gradient(circle at 72% -10%, rgba(43,92,121,.18), transparent 38%), var(--bg); color: var(--text); }
    [data-testid="stSidebar"] { background: #0d1721; border-right: 1px solid var(--border); }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem; }
    [data-testid="stSidebar"] .stRadio label { padding: .48rem .6rem; border-radius: 8px; }
    [data-testid="stSidebar"] .stRadio label:hover { background: rgba(102,182,255,.08); }
    .block-container { max-width: 1480px; padding: 2rem 3rem 3rem; }
    h1, h2, h3, h4 { letter-spacing: -.03em; } h1 { font-size: 2rem !important; margin-bottom: .2rem !important; } h2 { font-size: 1.12rem !important; margin-top: .2rem !important; }
    .mono { font-family: 'DM Mono', monospace; } .eyebrow { color: var(--blue); font: 500 .7rem 'DM Mono', monospace; letter-spacing: .16em; text-transform: uppercase; } .muted { color: var(--muted); }
    .topbar { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:1.7rem; } .brand { display:flex; align-items:center; gap:.8rem; } .brand-mark { width:36px; height:36px; border:1px solid rgba(102,182,255,.42); border-radius:9px; display:grid; place-items:center; color:var(--blue); font:600 .72rem 'DM Mono',monospace; box-shadow:0 0 24px rgba(102,182,255,.12); } .brand-name { font-weight:800; font-size:1rem; } .brand-sub { color:var(--muted); font-size:.68rem; margin-top:.1rem; }
    .system-pill { display:flex; align-items:center; gap:.5rem; padding:.45rem .75rem; border:1px solid rgba(70,211,154,.24); background:rgba(70,211,154,.07); border-radius:999px; color:var(--green); font-size:.75rem; } .pulse { width:7px; height:7px; border-radius:50%; background:var(--green); box-shadow:0 0 0 4px rgba(70,211,154,.12); }
    .hero { border:1px solid var(--border); background:linear-gradient(115deg, rgba(22,36,50,.92), rgba(17,27,38,.65)); padding:1.45rem 1.55rem; border-radius:14px; margin-bottom:1.1rem; } .hero-grid { display:flex; justify-content:space-between; align-items:flex-end; gap:2rem; } .hero h1 { margin-top:.35rem; } .hero-copy { max-width:620px; color:var(--muted); font-size:.86rem; line-height:1.6; } .hero-meta { display:flex; gap:1.5rem; white-space:nowrap; } .hero-meta strong { display:block; color:var(--text); font:500 1rem 'DM Mono',monospace; } .hero-meta span { display:block; color:var(--muted); font-size:.67rem; margin-top:.25rem; }
    .kpi { background:rgba(17,27,38,.83); border:1px solid var(--border); border-radius:12px; padding:1rem 1.05rem; min-height:96px; } .kpi-label { color:var(--muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.08em; } .kpi-value { color:var(--text); font:500 1.7rem 'DM Mono',monospace; margin-top:.45rem; } .kpi-note { font-size:.7rem; color:var(--muted); margin-top:.25rem; } .kpi-note.good { color:var(--green); } .kpi-note.warn { color:var(--amber); } .kpi-note.bad { color:var(--red); }
    .section-head { display:flex; justify-content:space-between; align-items:baseline; margin:1.8rem 0 .75rem; } .section-head h2 { margin:0 !important; } .section-note { color:var(--muted); font-size:.73rem; }
    .panel { border:1px solid var(--border); background:rgba(17,27,38,.72); border-radius:12px; padding:1rem 1.1rem; height:100%; } .panel-title { display:flex; justify-content:space-between; align-items:center; margin-bottom:.85rem; } .panel-title strong { font-size:.86rem; } .panel-title span { color:var(--muted); font:400 .68rem 'DM Mono',monospace; }
    .factory-row { padding:.75rem 0; border-top:1px solid rgba(148,163,184,.1); } .factory-row:first-of-type { border-top:0; padding-top:.1rem; } .row-top { display:flex; justify-content:space-between; align-items:center; } .factory-name { font-size:.82rem; font-weight:700; } .factory-location { color:var(--muted); font-size:.7rem; margin-left:.45rem; } .status { display:inline-flex; align-items:center; gap:.35rem; font-size:.68rem; font-weight:700; } .status-dot { width:6px; height:6px; border-radius:50%; display:inline-block; } .status.good { color:var(--green); } .status.good .status-dot { background:var(--green); } .status.warn { color:var(--amber); } .status.warn .status-dot { background:var(--amber); } .factory-stats { display:flex; gap:1.3rem; color:var(--muted); font:400 .67rem 'DM Mono',monospace; margin-top:.55rem; }
    .connector { display:flex; align-items:center; justify-content:space-between; padding:.75rem 0; border-top:1px solid rgba(148,163,184,.1); } .connector:first-of-type { border-top:0; padding-top:.1rem; } .connector-name { font-size:.78rem; font-weight:600; } .connector-url { color:var(--muted); font:400 .62rem 'DM Mono',monospace; margin-top:.2rem; } .connector-right { text-align:right; } .connector-assets { color:var(--muted); font:400 .64rem 'DM Mono',monospace; margin-top:.25rem; }
    .alert { border:1px solid rgba(240,113,120,.19); border-left:3px solid var(--red); background:rgba(240,113,120,.06); border-radius:9px; padding:.76rem .85rem; margin-bottom:.6rem; } .alert.warning { border-color:rgba(244,184,96,.2); border-left-color:var(--amber); background:rgba(244,184,96,.06); } .alert-head { display:flex; justify-content:space-between; gap:.75rem; } .alert-title { font-size:.76rem; font-weight:700; } .alert-meta { color:var(--muted); font:400 .62rem 'DM Mono',monospace; margin-top:.3rem; } .alert-badge { color:var(--red); font:500 .62rem 'DM Mono',monospace; text-transform:uppercase; } .warning .alert-badge { color:var(--amber); }
    .stButton > button { border-radius:8px; border:1px solid var(--border); background:var(--surface2); color:var(--text); min-height:2.3rem; transition:all .2s ease; } .stButton > button:hover { border-color:rgba(102,182,255,.5); color:white; background:#1b3042; } .stPlotlyChart { border-radius:10px; overflow:hidden; }
    @media (max-width: 900px) { .block-container { padding:1.2rem 1rem 2rem; } .hero-grid { display:block; } .hero-meta { margin-top:1rem; flex-wrap:wrap; } .topbar { align-items:flex-start; } }
    </style>
    """, unsafe_allow_html=True)

API = os.environ.get("DASHBOARD_API_URL", "http://localhost:8000").rstrip("/")

def api_get(path):
    try:
        response = requests.get(f"{API}{path}", timeout=2.5); response.raise_for_status(); return response.json(), True
    except (requests.RequestException, ValueError): return None, False

def api_post(path, payload=None):
    try:
        response = requests.post(f"{API}{path}", json=payload, timeout=3); response.raise_for_status(); return response.json(), True
    except (requests.RequestException, ValueError): return None, False

def demo_data():
    now = datetime.now(); rng = np.random.default_rng(12); factories, readings = [], {}
    locations = {"FactoryA": "Sfax, TN", "FactoryB": "Lyon, FR", "FactoryC": "Turin, IT"}; bases = {"FactoryA": 67, "FactoryB": 73, "FactoryC": 62}
    for i, factory_id in enumerate(("FactoryA", "FactoryB", "FactoryC")):
        timestamps = [now - timedelta(minutes=29 - n) for n in range(30)]; temp = bases[factory_id] + np.sin(np.linspace(0, 4, 30)) * 3 + rng.normal(0, 1.1, 30); vibration = .42 + np.sin(np.linspace(0, 6, 30)) * .08 + rng.normal(0, .035, 30)
        frame = pd.DataFrame({"timestamp": timestamps, "temperature": temp, "vibrations": vibration, "pressure": 14.5 + rng.normal(0, .22, 30), "humidity": 46 + rng.normal(0, 2, 30), "power_consumption": 160 + i * 22 + rng.normal(0, 7, 30)})
        readings[factory_id] = frame; factories.append({"factory_id": factory_id, "status": "connected", "sensor_count": 5, "last_reading": {"timestamp": timestamps[-1].isoformat(), "temperature": float(temp[-1]), "vibrations": float(vibration[-1]), "power_consumption": float(frame.power_consumption.iloc[-1])}, "location": locations[factory_id]})
    history = pd.DataFrame({"round": list(range(11, 21)), "accuracy": np.linspace(.89, .942, 10), "precision": np.linspace(.87, .934, 10), "recall": np.linspace(.86, .929, 10), "f1_score": np.linspace(.865, .931, 10)})
    alerts = [{"alert_id": "ALT-0241", "factory_id": "FactoryB", "sensor_name": "vibrations", "severity": "critical", "message": "Vibration anomaly detected on Compressor B2", "timestamp": (now - timedelta(minutes=4)).isoformat(), "value": 3.4, "threshold": 3.0}, {"alert_id": "ALT-0238", "factory_id": "FactoryA", "sensor_name": "temperature", "severity": "high", "message": "Temperature trending above operating threshold", "timestamp": (now - timedelta(minutes=18)).isoformat(), "value": 82.1, "threshold": 80.0}, {"alert_id": "ALT-0234", "factory_id": "FactoryC", "sensor_name": "power_consumption", "severity": "medium", "message": "Power draw 12% above local baseline", "timestamp": (now - timedelta(minutes=31)).isoformat(), "value": 214.0, "threshold": 200.0}]
    edc = [{"connector_name": "EDC · Factory A", "endpoint": "edc-factory-a:8080", "status": "healthy", "assets": 12, "contract_definitions": 4}, {"connector_name": "EDC · Factory B", "endpoint": "edc-factory-b:8080", "status": "healthy", "assets": 9, "contract_definitions": 3}, {"connector_name": "EDC · Factory C", "endpoint": "edc-factory-c:8080", "status": "degraded", "assets": 7, "contract_definitions": 2}]
    return factories, readings, edc, alerts, history

def fmt_time(value):
    try: return pd.to_datetime(value).strftime("%H:%M:%S")
    except (ValueError, TypeError): return "—"

def status_html(label, kind="good"):
    return f'<span class="status {kind}"><i class="status-dot"></i>{label}</span>'

def plot_layout(fig, height=270):
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=15, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Manrope", color="#8da1b2", size=10), legend=dict(orientation="h", y=1.08, x=0, font=dict(size=10)), hovermode="x unified")
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="rgba(148,163,184,.12)"); fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,.08)", zeroline=False)
    return fig

factories, demo_readings, edc_demo, alerts_demo, history_demo = demo_data()
factory_payload, api_live = api_get("/api/factories"); edc_payload, edc_live = api_get("/api/edc/status"); alerts_payload, alerts_live = api_get("/api/alerts?limit=6"); performance_payload, model_live = api_get("/api/model/performance?rounds=10")
if api_live and factory_payload: factories = factory_payload
if edc_live and edc_payload: edc_demo = edc_payload
if alerts_live and alerts_payload: alerts_demo = alerts_payload
if model_live and performance_payload: current_model = performance_payload["current_model"]; history_demo = pd.DataFrame(performance_payload["history"])
else: current_model = {"accuracy": .942, "precision": .934, "recall": .929, "f1_score": .931, "round": 20}

with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-mark">IDS</div><div><div class="brand-name">Industrial Data Space</div><div class="brand-sub">Operations console · v1.4</div></div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True); st.markdown('<div class="eyebrow">Workspace</div>', unsafe_allow_html=True)
    view = st.radio("Navigation", ["Overview", "Telemetry", "Model & alerts"], label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True); st.markdown('<div class="eyebrow">Data source</div>', unsafe_allow_html=True); st.markdown(status_html("API connected" if api_live else "Demo data active", "good" if api_live else "warn"), unsafe_allow_html=True); st.caption(f"Endpoint\n{API}")
    st.markdown("<br>", unsafe_allow_html=True); st.markdown('<div class="eyebrow">Simulation</div>', unsafe_allow_html=True); sim_col1, sim_col2 = st.columns(2)
    if sim_col1.button("Start", use_container_width=True): api_post("/api/simulation/start", {"factory_ids": ["FactoryA", "FactoryB", "FactoryC"], "interval_seconds": 5}); st.rerun()
    if sim_col2.button("Stop", use_container_width=True): api_post("/api/simulation/stop"); st.rerun()
    if st.button("Refresh data", use_container_width=True): st.rerun()
    st.markdown("<br>", unsafe_allow_html=True); st.caption("Read-only operational view\nTelemetry refreshes on demand.")

st.markdown(f'<div class="topbar"><div><div class="eyebrow">Plant network / live overview</div></div><div class="system-pill"><i class="pulse"></i> {"SYSTEM NOMINAL" if api_live else "DEMO MODE"}</div></div>', unsafe_allow_html=True)

if view == "Overview":
    st.markdown('<div class="hero"><div class="hero-grid"><div><div class="eyebrow">Predictive maintenance command center</div><h1>Network health at a glance</h1><div class="hero-copy">Surveillez les usines connectées, la santé des connecteurs EDC et les signaux IoT qui alimentent le modèle fédéré.</div></div><div class="hero-meta"><div><strong>3 / 3</strong><span>factories online</span></div><div><strong>28</strong><span>data assets shared</span></div><div><strong>20</strong><span>latest FL round</span></div></div></div></div>', unsafe_allow_html=True)
    critical_count = sum(1 for a in alerts_demo if a.get("severity") in ("critical", "high")); healthy_edc = sum(1 for c in edc_demo if c.get("status") in ("healthy", "connected", "ok")); k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="kpi"><div class="kpi-label">Connected factories</div><div class="kpi-value">{len(factories)}<span style="color:var(--muted);font-size:1rem"> / 3</span></div><div class="kpi-note good">+12% telemetry coverage</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="kpi"><div class="kpi-label">EDC connectors</div><div class="kpi-value">{healthy_edc}<span style="color:var(--muted);font-size:1rem"> / {len(edc_demo)}</span></div><div class="kpi-note {"good" if healthy_edc == len(edc_demo) else "warn"}">{"All systems nominal" if healthy_edc == len(edc_demo) else "1 connector needs attention"}</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi"><div class="kpi-label">Open maintenance alerts</div><div class="kpi-value">{len(alerts_demo)}</div><div class="kpi-note {"bad" if critical_count else "good"}">{critical_count} high-priority signal(s)</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="kpi"><div class="kpi-label">Model F1 score</div><div class="kpi-value">{current_model["f1_score"]:.1%}</div><div class="kpi-note good">+2.4 pts vs round 10</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-head"><h2>Infrastructure status</h2><span class="section-note">Last sync · just now</span></div>', unsafe_allow_html=True); left, right = st.columns([1.35, 1])
    with left:
        st.markdown('<div class="panel"><div class="panel-title"><strong>Connected factories</strong><span>STATUS / TELEMETRY</span></div>', unsafe_allow_html=True)
        for factory in factories:
            fid = factory.get("factory_id", "Factory"); reading = factory.get("last_reading") or {}; location = {"FactoryA":"Sfax, TN", "FactoryB":"Lyon, FR", "FactoryC":"Turin, IT"}.get(fid, "Industrial site"); fstatus = factory.get("status", "connected"); kind = "good" if fstatus == "connected" else "warn"
            st.markdown(f'<div class="factory-row"><div class="row-top"><div><span class="factory-name">{fid.replace("Factory", "Factory ")}</span><span class="factory-location">{location}</span></div>{status_html("Connected" if kind == "good" else fstatus.title(), kind)}</div><div class="factory-stats"><span>{factory.get("sensor_count", 5)} sensors</span><span>{float(reading.get("temperature", 0)):.1f} °C</span><span>last {fmt_time(reading.get("timestamp"))}</span></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div class="panel-title"><strong>EDC connector health</strong><span>SECURE DATA PLANE</span></div>', unsafe_allow_html=True)
        for connector in edc_demo:
            healthy = connector.get("status") in ("healthy", "connected", "ok"); label = connector.get("connector_name") or connector.get("connector_id") or connector.get("endpoint", "EDC connector").split(":")[0]
            st.markdown(f'<div class="connector"><div><div class="connector-name">{label.replace("EDC · ", "")}</div><div class="connector-url">{connector.get("endpoint", "local")}</div></div><div class="connector-right">{status_html("Healthy" if healthy else "Degraded", "good" if healthy else "warn")}<div class="connector-assets">{connector.get("assets", 0)} assets · {connector.get("contract_definitions", 0)} contracts</div></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-head"><h2>Live telemetry</h2><span class="section-note">Temperature · rolling 30 min</span></div>', unsafe_allow_html=True); selected = st.selectbox("Factory", [f.get("factory_id", "FactoryA") for f in factories], label_visibility="collapsed")
    if api_live: sensor_payload, sensor_live = api_get(f"/api/factories/{selected}/sensors?limit=60"); telemetry = pd.DataFrame(sensor_payload.get("recent_readings", [])) if sensor_live and sensor_payload else demo_readings[selected]
    else: telemetry = demo_readings[selected]
    if not telemetry.empty:
        telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"]); fig = go.Figure(); fig.add_trace(go.Scatter(x=telemetry["timestamp"], y=telemetry["temperature"], name="Temperature", mode="lines", line=dict(color=COLORS["blue"], width=2), fill="tozeroy", fillcolor="rgba(102,182,255,.08)")); fig.add_trace(go.Scatter(x=telemetry["timestamp"], y=telemetry["vibrations"] * 40, name="Vibration ×40", mode="lines", line=dict(color=COLORS["purple"], width=1.5, dash="dot"))); fig.add_hline(y=80, line_dash="dot", line_color=COLORS["amber"], annotation_text="warning threshold", annotation_font_color=COLORS["amber"]); st.plotly_chart(plot_layout(fig, 275), use_container_width=True, config={"displayModeBar": False})

elif view == "Telemetry":
    st.markdown('<div class="eyebrow">Sensor network</div><h1>Telemetry explorer</h1><p class="hero-copy">Lecture des signaux IoT par usine, avec tendances et seuils de maintenance.</p>', unsafe_allow_html=True); selected = st.selectbox("Factory", [f.get("factory_id", "FactoryA") for f in factories]); telemetry = demo_readings[selected]
    if api_live: sensor_payload, sensor_live = api_get(f"/api/factories/{selected}/sensors?limit=60"); telemetry = pd.DataFrame(sensor_payload.get("recent_readings", [])) if sensor_live and sensor_payload else telemetry
    telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"])
    for metric, label, color in [("temperature", "Temperature (°C)", COLORS["blue"]), ("vibrations", "Vibrations (mm/s)", COLORS["purple"]), ("power_consumption", "Power consumption (kW)", COLORS["green"])]:
        st.markdown(f'<div class="panel" style="margin-top:.9rem"><div class="panel-title"><strong>{label}</strong><span>LIVE SERIES</span></div>', unsafe_allow_html=True); fig = go.Figure(go.Scatter(x=telemetry["timestamp"], y=telemetry[metric], mode="lines", line=dict(color=color, width=2), fill="tozeroy", fillcolor="rgba(102,182,255,.06)")); st.plotly_chart(plot_layout(fig, 220), use_container_width=True, config={"displayModeBar": False}); st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown('<div class="eyebrow">Federated learning / predictive maintenance</div><h1>Model & alerts</h1><p class="hero-copy">Performance du modèle partagé et signaux d’intervention priorisés pour les équipes maintenance.</p>', unsafe_allow_html=True); m1, m2, m3, m4 = st.columns(4)
    for col, label, key in [(m1, "Accuracy", "accuracy"), (m2, "Precision", "precision"), (m3, "Recall", "recall"), (m4, "F1 score", "f1_score")]: col.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{current_model[key]:.1%}</div><div class="kpi-note good">Round {current_model.get("round", 20)} · stable</div></div>', unsafe_allow_html=True)
    chart_col, alert_col = st.columns([1.25, .9])
    with chart_col:
        st.markdown('<div class="panel" style="margin-top:1.1rem"><div class="panel-title"><strong>Federated model progress</strong><span>LAST 10 ROUNDS</span></div>', unsafe_allow_html=True); fig = go.Figure()
        for metric, color in [("accuracy", COLORS["blue"]), ("f1_score", COLORS["green"]), ("precision", COLORS["amber"]), ("recall", COLORS["purple"])]: fig.add_trace(go.Scatter(x=history_demo["round"], y=history_demo[metric], name=metric.replace("_", " ").title(), mode="lines+markers", line=dict(color=color, width=2)))
        st.plotly_chart(plot_layout(fig, 310), use_container_width=True, config={"displayModeBar": False}); st.markdown('</div>', unsafe_allow_html=True)
    with alert_col:
        st.markdown('<div class="panel" style="margin-top:1.1rem"><div class="panel-title"><strong>Maintenance alerts</strong><span>OPEN SIGNALS</span></div>', unsafe_allow_html=True)
        for alert in alerts_demo:
            severity = alert.get("severity", "medium"); kind = "warning" if severity in ("medium", "low") else ""; st.markdown(f'<div class="alert {kind}"><div class="alert-head"><span class="alert-title">{alert.get("message", "Maintenance signal")}</span><span class="alert-badge">{severity}</span></div><div class="alert-meta">{alert.get("factory_id", "Factory")} · {alert.get("sensor_name", "sensor")} · {fmt_time(alert.get("timestamp"))}</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
