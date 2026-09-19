import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _generate_live_readings(n_points=50):
    rng = np.random.default_rng()
    now = datetime.now()
    timestamps = [now - timedelta(seconds=5 * (n_points - i)) for i in range(n_points)]

    temp_base = 65 + 10 * np.sin(np.linspace(0, 4 * np.pi, n_points))
    vib_base = 0.5 + 0.3 * np.sin(np.linspace(0, 3 * np.pi, n_points))

    df = pd.DataFrame({
        "timestamp": timestamps,
        "temperature": temp_base + rng.normal(0, 2, n_points),
        "vibrations": np.clip(vib_base + rng.normal(0, 0.1, n_points), 0, 2),
        "pressure": 101.3 + rng.normal(0, 0.5, n_points),
        "humidity": 45 + rng.normal(0, 3, n_points),
        "power_consumption": 320 + rng.normal(0, 15, n_points),
    })
    return df


def _current_status(df):
    latest = df.iloc[-1]
    temp = latest["temperature"]
    vib = latest["vibrations"]
    if temp > 80 or vib > 1.2:
        return "critical", "#ff5252"
    if temp > 75 or vib > 0.9:
        return "warning", "#ffc107"
    return "normal", "#00e676"


def _plotly_base(title, height=280):
    return dict(
        title=dict(text=title, font=dict(size=13, color="#e0e0e0")),
        height=height,
        margin=dict(l=50, r=15, t=38, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,17,23,1)",
        xaxis=dict(gridcolor="#262730", color="#a0a0a0", showgrid=True),
        yaxis=dict(gridcolor="#262730", color="#a0a0a0", showgrid=True),
        font=dict(color="#a0a0a0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
    )


def _status_gauge(value, min_val, max_val, warn, crit, title, unit):
    if value >= crit:
        color = "#ff5252"
        status = "CRITICAL"
    elif value >= warn:
        color = "#ffc107"
        status = "WARNING"
    else:
        color = "#00e676"
        status = "NORMAL"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        number=dict(suffix=unit, font=dict(size=28, color="white")),
        title=dict(text=f"{title} [{status}]", font=dict(size=12, color=color)),
        delta=dict(reference=value * 0.97, font=dict(size=12)),
        gauge=dict(
            axis=dict(range=[min_val, max_val], tickfont=dict(color="#a0a0a0")),
            bar=dict(color=color),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[
                dict(range=[min_val, warn], color="rgba(0,230,118,0.08)"),
                dict(range=[warn, crit], color="rgba(255,193,7,0.08)"),
                dict(range=[crit, max_val], color="rgba(255,82,82,0.08)"),
            ],
            threshold=dict(line=dict(color="white", width=2), value=crit),
        ),
    ))
    fig.update_layout(
        height=170,
        margin=dict(l=25, r=25, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#a0a0a0"),
    )
    return fig


def render_live_charts(container):
    with container:
        st.subheader("Live Sensor Data")

        df = _generate_live_readings()
        status, status_color = _current_status(df)
        latest = df.iloc[-1]

        st.markdown(
            f"<div style='text-align:right;color:{status_color};font-size:0.85rem;font-weight:600;'>"
            f"● {status.upper()}</div>",
            unsafe_allow_html=True,
        )

        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.plotly_chart(
                _status_gauge(latest["temperature"], 0, 100, 75, 85, "Temperature", "°C"),
                use_container_width=True, key="live_gauge_temp",
            )
        with g2:
            st.plotly_chart(
                _status_gauge(latest["vibrations"], 0, 2, 0.9, 1.2, "Vibrations", " mm/s"),
                use_container_width=True, key="live_gauge_vib",
            )
        with g3:
            st.plotly_chart(
                _status_gauge(latest["pressure"], 95, 110, 105, 108, "Pressure", " hPa"),
                use_container_width=True, key="live_gauge_pres",
            )
        with g4:
            st.plotly_chart(
                _status_gauge(latest["humidity"], 20, 80, 60, 75, "Humidity", "%"),
                use_container_width=True, key="live_gauge_hum",
            )

        tab_temp, tab_vib, tab_pressure = st.tabs(
            ["🌡️ Temperature Trend", "📳 Vibration Trend", "📊 Pressure Trend"]
        )

        with tab_temp:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["timestamp"], y=df["temperature"],
                mode="lines", name="Temperature",
                line=dict(color="#ff7043", width=2),
                fill="tozeroy", fillcolor="rgba(255,112,67,0.08)",
                hovertemplate="Time: %{x|%H:%M:%S}<br>Temp: %{y:.1f}°C<extra></extra>",
            ))
            fig.add_hline(y=75, line_dash="dash", line_color="#ffc107", annotation_text="Warning")
            fig.add_hline(y=85, line_dash="dash", line_color="#ff5252", annotation_text="Critical")
            fig.update_layout(**_plotly_base("Temperature (°C)", height=300))
            st.plotly_chart(fig, use_container_width=True, key="live_temp_trend")

        with tab_vib:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["timestamp"], y=df["vibrations"],
                mode="lines", name="Vibrations",
                line=dict(color="#42a5f5", width=2),
                fill="tozeroy", fillcolor="rgba(66,165,245,0.08)",
                hovertemplate="Time: %{x|%H:%M:%S}<br>Vib: %{y:.2f} mm/s<extra></extra>",
            ))
            fig.add_hline(y=0.9, line_dash="dash", line_color="#ffc107", annotation_text="Warning")
            fig.add_hline(y=1.2, line_dash="dash", line_color="#ff5252", annotation_text="Critical")
            fig.update_layout(**_plotly_base("Vibrations (mm/s)", height=300))
            st.plotly_chart(fig, use_container_width=True, key="live_vib_trend")

        with tab_pressure:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["timestamp"], y=df["pressure"],
                mode="lines", name="Pressure",
                line=dict(color="#66bb6a", width=2),
                fill="tozeroy", fillcolor="rgba(102,187,106,0.08)",
                hovertemplate="Time: %{x|%H:%M:%S}<br>Press: %{y:.1f} hPa<extra></extra>",
            ))
            fig.add_hline(y=105, line_dash="dash", line_color="#ffc107", annotation_text="Warning")
            fig.add_hline(y=108, line_dash="dash", line_color="#ff5252", annotation_text="Critical")
            fig.update_layout(**_plotly_base("Pressure (hPa)", height=300))
            st.plotly_chart(fig, use_container_width=True, key="live_pres_trend")
