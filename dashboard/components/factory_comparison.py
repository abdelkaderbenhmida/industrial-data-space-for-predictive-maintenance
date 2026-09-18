import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _generate_factory_metrics():
    rng = np.random.default_rng()
    factories = ["Factory A", "Factory B", "Factory C"]
    locations = ["Stuttgart, DE", "Lyon, FR", "Turin, IT"]

    data = []
    for name, loc in zip(factories, locations):
        data.append({
            "factory": name,
            "location": loc,
            "temperature": round(rng.normal(65, 8), 1),
            "vibrations": round(rng.normal(0.5, 0.15), 2),
            "pressure": round(rng.normal(101.3, 0.5), 1),
            "humidity": round(rng.normal(45, 5), 1),
            "power_consumption": round(rng.normal(320, 30), 1),
            "uptime_pct": round(rng.uniform(95, 99.5), 1),
            "sensors_online": int(rng.integers(20, 25)),
            "sensors_total": 24,
            "failure_risk": round(rng.uniform(0.01, 0.15), 3),
            "efficiency": round(rng.uniform(0.82, 0.96), 2),
            "oee": round(rng.uniform(0.70, 0.92), 2),
        })
    return pd.DataFrame(data)


def _plotly_base(title, height=320):
    return dict(
        title=dict(text=title, font=dict(size=13, color="#e0e0e0")),
        height=height,
        margin=dict(l=50, r=20, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,17,23,1)",
        xaxis=dict(gridcolor="#262730", color="#a0a0a0"),
        yaxis=dict(gridcolor="#262730", color="#a0a0a0"),
        font=dict(color="#a0a0a0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
    )


def _status_color(value, warn, crit, invert=False):
    if invert:
        if value < crit:
            return "#ff5252"
        if value < warn:
            return "#ffc107"
        return "#00e676"
    if value >= crit:
        return "#ff5252"
    if value >= warn:
        return "#ffc107"
    return "#00e676"


def render_factory_comparison(container):
    with container:
        st.subheader("Factory Comparison")

        df = _generate_factory_metrics()
        colors = ["#42a5f5", "#66bb6a", "#ffa726"]

        tab_bar, tab_radar, tab_heat, tab_kpi = st.tabs(
            ["📊 Sensor Comparison", "🎯 Radar Profile", "🗺️ Status Matrix", "📈 KPI Dashboard"]
        )

        with tab_bar:
            metrics = ["temperature", "vibrations", "pressure", "humidity", "power_consumption"]
            labels = ["Temp (°C)", "Vib (mm/s)", "Pressure (hPa)", "Humidity (%)", "Power (kW)"]

            fig = go.Figure()
            for i, (_, row) in enumerate(df.iterrows()):
                fig.add_trace(go.Bar(
                    name=row["factory"],
                    x=labels,
                    y=[row[m] for m in metrics],
                    marker_color=colors[i],
                    text=[f"{row[m]:.1f}" for m in metrics],
                    textposition="auto",
                    hovertemplate=f"<b>{row['factory']}</b><br>%{{x}}: %{{y:.1f}}<extra></extra>",
                ))
            fig.update_layout(**_plotly_base("Sensor Readings by Factory", height=350))
            fig.update_layout(barmode="group")
            st.plotly_chart(fig, use_container_width=True, key="fc_bar")

        with tab_radar:
            categories = ["Temperature", "Vibrations", "Pressure", "Humidity", "Power"]
            fig = go.Figure()
            for i, (_, row) in enumerate(df.iterrows()):
                values = [
                    row["temperature"] / 100,
                    row["vibrations"] / 2,
                    row["pressure"] / 110,
                    row["humidity"] / 80,
                    row["power_consumption"] / 400,
                ]
                fig.add_trace(go.Scatterpolar(
                    r=values + [values[0]],
                    theta=categories + [categories[0]],
                    fill="toself",
                    fillcolor=f"rgba({int(colors[i][1:3],16)},{int(colors[i][3:5],16)},{int(colors[i][5:7],16)},0.1)",
                    line=dict(color=colors[i], width=2),
                    name=row["factory"],
                    hovertemplate="%{theta}: %{r:.2f}<extra>%{fullData.name}</extra>",
                ))
            fig.update_layout(
                **_plotly_base("Sensor Profile Comparison", height=380),
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, range=[0, 1], gridcolor="#262730"),
                    angularaxis=dict(gridcolor="#262730", color="#a0a0a0"),
                ),
            )
            st.plotly_chart(fig, use_container_width=True, key="fc_radar")

        with tab_heat:
            heat_metrics = ["temperature", "vibrations", "pressure", "humidity", "power_consumption", "efficiency", "oee"]
            heat_labels = ["Temp", "Vib", "Pressure", "Humidity", "Power", "Efficiency", "OEE"]
            z_data = []
            for _, row in df.iterrows():
                z_data.append([
                    row["temperature"] / 100,
                    row["vibrations"] / 2,
                    row["pressure"] / 110,
                    row["humidity"] / 80,
                    row["power_consumption"] / 400,
                    row["efficiency"],
                    row["oee"],
                ])

            fig = go.Figure(data=go.Heatmap(
                z=z_data,
                x=heat_labels,
                y=df["factory"].tolist(),
                colorscale=[
                    [0, "#0d47a1"],
                    [0.25, "#1565c0"],
                    [0.5, "#ffc107"],
                    [0.75, "#ff7043"],
                    [1, "#ff5252"],
                ],
                text=[[f"{v:.2f}" for v in row] for row in z_data],
                texttemplate="%{text}",
                textfont=dict(size=11, color="white"),
                hovertemplate="<b>%{y}</b><br>%{x}: %{z:.3f}<extra></extra>",
            ))
            fig.update_layout(**_plotly_base("Factory Status Matrix", height=250))
            st.plotly_chart(fig, use_container_width=True, key="fc_heat")

        with tab_kpi:
            for i, (_, row) in enumerate(df.iterrows()):
                risk_color = _status_color(row["failure_risk"], 0.08, 0.12)
                eff_color = _status_color(row["efficiency"], 0.85, 0.80, invert=True)
                oee_color = _status_color(row["oee"], 0.80, 0.70, invert=True)

                st.markdown(
                    f"""
                    <div style="
                        background:#0e1117;
                        border:1px solid #262730;
                        border-left:4px solid {colors[i]};
                        border-radius:8px;
                        padding:14px 18px;
                        margin-bottom:10px;
                    ">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <strong style="font-size:1.05rem;">{row['factory']}</strong>
                            <span style="color:#666;font-size:0.8rem;">{row['location']}</span>
                        </div>
                        <div style="display:flex;gap:24px;margin-top:8px;font-size:0.85rem;">
                            <span style="color:{risk_color};">Risk: {row['failure_risk']:.1%}</span>
                            <span style="color:{eff_color};">Efficiency: {row['efficiency']:.0%}</span>
                            <span style="color:{oee_color};">OEE: {row['oee']:.0%}</span>
                            <span style="color:#a0a0a0;">Sensors: {row['sensors_online']}/{row['sensors_total']}</span>
                            <span style="color:#a0a0a0;">Power: {row['power_consumption']:.0f} kW</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
