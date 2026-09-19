import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _generate_sensor_timeseries(n_points=60):
    rng = np.random.default_rng()
    now = datetime.now()
    timestamps = [now - timedelta(seconds=5 * (n_points - i)) for i in range(n_points)]

    base_temp = 65 + 10 * np.sin(np.linspace(0, 3 * np.pi, n_points))
    base_vib = 0.5 + 0.3 * np.sin(np.linspace(0, 2 * np.pi, n_points))

    df = pd.DataFrame({
        "timestamp": timestamps,
        "temperature": base_temp + rng.normal(0, 2, n_points),
        "vibrations": np.clip(base_vib + rng.normal(0, 0.1, n_points), 0, 2),
        "pressure": 101.3 + rng.normal(0, 0.5, n_points),
        "humidity": 45 + rng.normal(0, 3, n_points),
        "power_consumption": 320 + rng.normal(0, 15, n_points),
    })
    return df


def _plotly_layout(title, height=300):
    return dict(
        title=dict(text=title, font=dict(size=14, color="#e0e0e0")),
        height=height,
        margin=dict(l=50, r=20, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,17,23,1)",
        xaxis=dict(gridcolor="#262730", color="#a0a0a0", showgrid=True),
        yaxis=dict(gridcolor="#262730", color="#a0a0a0", showgrid=True),
        font=dict(color="#a0a0a0"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10),
        ),
    )


def render_sensor_charts(container):
    with container:
        st.subheader("Sensor Data")
        df = _generate_sensor_timeseries()

        tab_temp, tab_vib, tab_multi, tab_radar = st.tabs(
            ["🌡️ Temperature", "📳 Vibrations", "📊 All Sensors", "🎯 Factory Radar"]
        )

        with tab_temp:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["timestamp"], y=df["temperature"],
                mode="lines", name="Temperature",
                line=dict(color="#ff7043", width=2),
                fill="tozeroy", fillcolor="rgba(255,112,67,0.1)",
            ))
            fig.add_hline(y=75, line_dash="dash", line_color="#ff5252", annotation_text="Warning Threshold")
            fig.update_layout(**_plotly_layout("Temperature (°C)"))
            st.plotly_chart(fig, use_container_width=True)

        with tab_vib:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["timestamp"], y=df["vibrations"],
                mode="lines", name="Vibrations",
                line=dict(color="#42a5f5", width=2),
                fill="tozeroy", fillcolor="rgba(66,165,245,0.1)",
            ))
            fig.add_hline(y=1.0, line_dash="dash", line_color="#ff5252", annotation_text="Critical Threshold")
            fig.update_layout(**_plotly_layout("Vibrations (mm/s)"))
            st.plotly_chart(fig, use_container_width=True)

        with tab_multi:
            metrics = ["temperature", "vibrations", "pressure", "humidity", "power_consumption"]
            colors = ["#ff7043", "#42a5f5", "#66bb6a", "#ab47bc", "#ffa726"]
            fig = go.Figure()
            for metric, color in zip(metrics, colors):
                normalized = (df[metric] - df[metric].min()) / (df[metric].max() - df[metric].min() + 1e-9)
                fig.add_trace(go.Scatter(
                    x=df["timestamp"], y=normalized,
                    mode="lines", name=metric.replace("_", " ").title(),
                    line=dict(color=color, width=1.5),
                ))
            fig.update_layout(**_plotly_layout("Normalized Sensor Readings"))
            st.plotly_chart(fig, use_container_width=True)

        with tab_radar:
            latest = df.iloc[-1]
            categories = ["Temperature", "Vibrations", "Pressure", "Humidity", "Power"]
            values = [
                latest["temperature"] / 100,
                latest["vibrations"] / 2,
                latest["pressure"] / 110,
                latest["humidity"] / 100,
                latest["power_consumption"] / 400,
            ]
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor="rgba(66,165,245,0.2)",
                line=dict(color="#42a5f5"),
                name="Current",
            ))
            fig.update_layout(
                **_plotly_layout("Sensor Profile", height=350),
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0, 1], gridcolor="#262730"),
                    angularaxis=dict(gridcolor="#262730", color="#a0a0a0"),
                ),
            )
            st.plotly_chart(fig, use_container_width=True)
