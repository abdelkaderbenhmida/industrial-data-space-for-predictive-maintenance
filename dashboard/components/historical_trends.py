import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _generate_historical_data(days=30):
    rng = np.random.default_rng()
    now = datetime.now()
    dates = [now - timedelta(days=days - i) for i in range(days)]

    temp_cycle = 65 + 8 * np.sin(np.linspace(0, 6 * np.pi, days))
    vib_cycle = 0.5 + 0.2 * np.sin(np.linspace(0, 4 * np.pi, days))

    df = pd.DataFrame({
        "date": dates,
        "temperature_avg": temp_cycle + rng.normal(0, 3, days),
        "temperature_max": temp_cycle + 8 + rng.normal(0, 2, days),
        "temperature_min": temp_cycle - 5 + rng.normal(0, 2, days),
        "vibrations_avg": np.clip(vib_cycle + rng.normal(0, 0.08, days), 0, 2),
        "vibrations_max": np.clip(vib_cycle + 0.3 + rng.normal(0, 0.1, days), 0, 2),
        "power_consumption": 320 + 20 * np.sin(np.linspace(0, 8 * np.pi, days)) + rng.normal(0, 10, days),
        "failure_events": rng.poisson(0.3, days),
        "efficiency": np.clip(
            0.88 + 0.05 * np.sin(np.linspace(0, 5 * np.pi, days)) + rng.normal(0, 0.02, days),
            0.7, 1.0,
        ),
    })
    return df


def _plotly_base(title, height=320):
    return dict(
        title=dict(text=title, font=dict(size=13, color="#e0e0e0")),
        height=height,
        margin=dict(l=55, r=20, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,17,23,1)",
        xaxis=dict(gridcolor="#262730", color="#a0a0a0"),
        yaxis=dict(gridcolor="#262730", color="#a0a0a0"),
        font=dict(color="#a0a0a0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
    )


def render_historical_trends(container):
    with container:
        st.subheader("Historical Data Trends")

        df = _generate_historical_data(30)

        col_range, col_factory = st.columns(2)
        with col_range:
            period = st.selectbox("Time Range", ["7 Days", "14 Days", "30 Days"], index=2, key="hist_period")
        with col_factory:
            factory = st.selectbox("Factory", ["All Factories", "Factory A", "Factory B", "Factory C"], key="hist_factory")

        n_days = {"7 Days": 7, "14 Days": 14, "30 Days": 30}[period]
        df = df.tail(n_days)

        summary1, summary2, summary3, summary4 = st.columns(4)
        with summary1:
            st.metric("Avg Temperature", f"{df['temperature_avg'].mean():.1f}°C",
                       delta=f"{df['temperature_avg'].iloc[-1] - df['temperature_avg'].iloc[-2]:.1f}°C")
        with summary2:
            st.metric("Total Failures", int(df["failure_events"].sum()),
                       delta=f"{df['failure_events'].iloc[-1] - df['failure_events'].iloc[-2]:+d}")
        with summary3:
            st.metric("Avg Efficiency", f"{df['efficiency'].mean():.1%}",
                       delta=f"{df['efficiency'].iloc[-1] - df['efficiency'].iloc[-2]:.1%}")
        with summary4:
            st.metric("Avg Power", f"{df['power_consumption'].mean():.0f} kW",
                       delta=f"{df['power_consumption'].iloc[-1] - df['power_consumption'].iloc[-2]:.0f} kW")

        tab_temp, tab_vib, tab_eff, tab_events = st.tabs(
            ["🌡️ Temperature History", "📳 Vibration History", "⚡ Efficiency Trend", "🔴 Failure Events"]
        )

        with tab_temp:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["temperature_max"],
                mode="lines", name="Max",
                line=dict(color="#ff5252", width=1, dash="dot"),
                hovertemplate="%{x|%b %d}: %{y:.1f}°C<extra>Max</extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["temperature_avg"],
                mode="lines+markers", name="Average",
                line=dict(color="#ff7043", width=2),
                marker=dict(size=4),
                hovertemplate="%{x|%b %d}: %{y:.1f}°C<extra>Avg</extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["temperature_min"],
                mode="lines", name="Min",
                line=dict(color="#42a5f5", width=1, dash="dot"),
                hovertemplate="%{x|%b %d}: %{y:.1f}°C<extra>Min</extra>",
            ))
            fig.add_vrect(
                x0=df["date"].min(), x1=df["date"].max(),
                y0=75, y1=85,
                fillcolor="rgba(255,193,7,0.05)", layer="below",
                line_width=0, annotation_text="Warning Zone",
                annotation_position="top left",
            )
            fig.update_layout(**_plotly_base(f"Temperature Range — {period}", height=340))
            st.plotly_chart(fig, use_container_width=True, key="hist_temp")

        with tab_vib:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["vibrations_max"],
                mode="lines", name="Max",
                line=dict(color="#ff5252", width=1, dash="dot"),
                hovertemplate="%{x|%b %d}: %{y:.2f} mm/s<extra>Max</extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["vibrations_avg"],
                mode="lines+markers", name="Average",
                line=dict(color="#42a5f5", width=2),
                marker=dict(size=4),
                hovertemplate="%{x|%b %d}: %{y:.2f} mm/s<extra>Avg</extra>",
            ))
            fig.add_hline(y=0.9, line_dash="dash", line_color="#ffc107", annotation_text="Warning")
            fig.add_hline(y=1.2, line_dash="dash", line_color="#ff5252", annotation_text="Critical")
            fig.update_layout(**_plotly_base(f"Vibration Range — {period}", height=340))
            st.plotly_chart(fig, use_container_width=True, key="hist_vib")

        with tab_eff:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["efficiency"] * 100,
                mode="lines+markers", name="Efficiency",
                line=dict(color="#66bb6a", width=2),
                marker=dict(size=5),
                fill="tozeroy", fillcolor="rgba(102,187,106,0.08)",
                hovertemplate="%{x|%b %d}: %{y:.1f}%<extra>Efficiency</extra>",
            ))
            fig.add_hline(y=85, line_dash="dash", line_color="#ffc107", annotation_text="Target")
            fig.update_layout(**_plotly_base(f"Efficiency — {period}", height=340))
            fig.update_layout(yaxis=dict(title="Efficiency (%)", gridcolor="#262730", color="#a0a0a0"))
            st.plotly_chart(fig, use_container_width=True, key="hist_eff")

        with tab_events:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["date"], y=df["failure_events"],
                name="Failures",
                marker_color=[
                    "#ff5252" if v >= 2 else "#ffc107" if v == 1 else "#00e676"
                    for v in df["failure_events"]
                ],
                hovertemplate="%{x|%b %d}: %{y} events<extra></extra>",
            ))
            cumfail = df["failure_events"].cumsum()
            fig.add_trace(go.Scatter(
                x=df["date"], y=cumfail,
                mode="lines", name="Cumulative",
                line=dict(color="#ab47bc", width=2, dash="dot"),
                yaxis="y2",
                hovertemplate="%{x|%b %d}: %{y} total<extra>Cumulative</extra>",
            ))
            fig.update_layout(**_plotly_base(f"Failure Events — {period}", height=340))
            fig.update_layout(
                yaxis=dict(title="Events", gridcolor="#262730", color="#a0a0a0"),
                yaxis2=dict(title="Cumulative", overlaying="y", side="right", gridcolor="rgba(0,0,0,0)", color="#a0a0a0"),
            )
            st.plotly_chart(fig, use_container_width=True, key="hist_events")
