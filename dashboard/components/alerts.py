import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _generate_alerts():
    rng = np.random.default_rng()
    now = datetime.now()

    alert_templates = [
        {"severity": "critical", "icon": "🔴", "type": "Temperature Exceeded",
         "message": "Temperature exceeds 80°C threshold on CNC Mill #3"},
        {"severity": "warning", "icon": "🟡", "type": "Vibration Anomaly",
         "message": "Vibration levels elevated on Conveyor Belt Motor"},
        {"severity": "warning", "icon": "🟡", "type": "Power Spike",
         "message": "Power consumption 15% above baseline on Press Machine"},
        {"severity": "info", "icon": "🔵", "type": "Scheduled Maintenance",
         "message": "Hydraulic press scheduled for maintenance in 48 hours"},
        {"severity": "critical", "icon": "🔴", "type": "Predicted Failure",
         "message": "ML model predicts 87% failure probability for Bearing Unit B2 within 24h"},
        {"severity": "warning", "icon": "🟡", "type": "Humidity Drift",
         "message": "Humidity readings drifting outside normal range in Assembly Hall"},
        {"severity": "info", "icon": "🔵", "type": "Model Update",
         "message": "Federated model round 20 completed — accuracy improved to 94.2%"},
        {"severity": "info", "icon": "🔵", "type": "EDC Contract",
         "message": "Data sharing contract renewed between Factory A and Factory B"},
    ]

    n = rng.integers(3, len(alert_templates) + 1)
    selected = rng.choice(alert_templates, size=n, replace=False)
    alerts = []
    for i, a in enumerate(selected):
        alerts.append({
            **a,
            "id": f"ALT-{1000 + i}",
            "factory": rng.choice(["Factory A", "Factory B", "Factory C"]),
            "timestamp": now - timedelta(minutes=int(rng.integers(1, 180))),
            "acknowledged": bool(rng.choice([True, False], p=[0.3, 0.7])),
        })
    alerts.sort(key=lambda x: x["timestamp"], reverse=True)
    return alerts


_severity_style = {
    "critical": {"bg": "#1a0000", "border": "#ff5252", "text": "#ff5252"},
    "warning": {"bg": "#1a1500", "border": "#ffc107", "text": "#ffc107"},
    "info": {"bg": "#001a1a", "border": "#42a5f5", "text": "#42a5f5"},
}


def render_alerts(container):
    with container:
        st.subheader("Maintenance Alerts")
        alerts = _generate_alerts()

        critical = sum(1 for a in alerts if a["severity"] == "critical")
        warning = sum(1 for a in alerts if a["severity"] == "warning")
        info = sum(1 for a in alerts if a["severity"] == "info")

        c1, c2, c3 = st.columns(3)
        c1.metric("🔴 Critical", critical)
        c2.metric("🟡 Warning", warning)
        c3.metric("🔵 Info", info)

        for alert in alerts:
            style = _severity_style[alert["severity"]]
            ack_badge = (
                "<span style='background:#00e67622;color:#00e676;padding:2px 8px;"
                "border-radius:8px;font-size:0.7rem;'>ACK</span>"
                if alert["acknowledged"]
                else "<span style='background:#ff525222;color:#ff5252;padding:2px 8px;"
                "border-radius:8px;font-size:0.7rem;'>OPEN</span>"
            )
            st.markdown(
                f"""
                <div style="
                    background:{style['bg']};
                    border:1px solid {style['border']}33;
                    border-left:3px solid {style['border']};
                    border-radius:8px;
                    padding:12px 16px;
                    margin-bottom:8px;
                ">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            {alert['icon']}
                            <strong style="color:{style['text']};">{alert['type']}</strong>
                            <span style="color:#666;margin-left:8px;font-size:0.8rem;">{alert['id']}</span>
                        </div>
                        <div>{ack_badge}</div>
                    </div>
                    <div style="color:#ccc;margin-top:4px;font-size:0.9rem;">{alert['message']}</div>
                    <div style="color:#666;margin-top:4px;font-size:0.75rem;">
                        {alert['factory']} · {alert['timestamp'].strftime('%Y-%m-%d %H:%M')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
