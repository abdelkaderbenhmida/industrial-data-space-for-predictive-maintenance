import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _generate_factory_data():
    factories = [
        {"id": "factory-a", "name": "Factory A", "location": "Stuttgart, DE"},
        {"id": "factory-b", "name": "Factory B", "location": "Lyon, FR"},
        {"id": "factory-c", "name": "Factory C", "location": "Turin, IT"},
    ]
    rng = np.random.default_rng()
    for f in factories:
        f["status"] = rng.choice(["Online", "Online", "Online", "Degraded"], p=[0.7, 0.1, 0.1, 0.1])
        f["sensors_active"] = int(rng.integers(18, 25))
        f["sensors_total"] = 24
        f["temperature"] = round(rng.normal(65, 8), 1)
        f["power_kw"] = round(rng.normal(320, 40), 1)
        f["last_reading"] = datetime.now() - timedelta(seconds=int(rng.integers(1, 12)))
    return factories


def _status_color(status):
    return {"Online": "#00e676", "Degraded": "#ffc107", "Offline": "#ff5252"}.get(status, "#9e9e9e")


def render_factory_status(container):
    with container:
        st.subheader("Factory Status")
        factories = _generate_factory_data()
        for f in factories:
            color = _status_color(f["status"])
            st.markdown(
                f"""
                <div style="
                    background:#0e1117;
                    border:1px solid #262730;
                    border-left:4px solid {color};
                    border-radius:8px;
                    padding:14px 18px;
                    margin-bottom:10px;
                ">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <strong style="font-size:1.05rem;">{f['name']}</strong>
                            <span style="color:#666;margin-left:8px;font-size:0.85rem;">{f['location']}</span>
                        </div>
                        <span style="
                            background:{color}22;
                            color:{color};
                            padding:3px 10px;
                            border-radius:12px;
                            font-size:0.8rem;
                            font-weight:600;
                        ">{f['status']}</span>
                    </div>
                    <div style="margin-top:8px;display:flex;gap:24px;font-size:0.85rem;color:#a0a0a0;">
                        <span>Sensors: {f['sensors_active']}/{f['sensors_total']}</span>
                        <span>Temp: {f['temperature']}°C</span>
                        <span>Power: {f['power_kw']} kW</span>
                        <span>Last: {f['last_reading'].strftime('%H:%M:%S')}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
