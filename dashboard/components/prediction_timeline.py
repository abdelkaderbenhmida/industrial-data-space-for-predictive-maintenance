import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _generate_predictions():
    rng = np.random.default_rng()
    now = datetime.now()
    assets = [
        {"name": "CNC Mill #3", "factory": "Factory A", "type": "Bearing"},
        {"name": "Conveyor Belt Motor", "factory": "Factory B", "type": "Motor"},
        {"name": "Hydraulic Press", "factory": "Factory A", "type": "Pump"},
        {"name": "Assembly Robot Arm", "factory": "Factory C", "type": "Servo"},
        {"name": "Cooling System", "factory": "Factory B", "type": "Compressor"},
        {"name": "Packaging Line", "factory": "Factory C", "type": "Gearbox"},
        {"name": "Welding Station", "factory": "Factory A", "type": "Transformer"},
        {"name": "Material Handler", "factory": "Factory B", "type": "Hydraulic"},
    ]

    predictions = []
    for asset in assets:
        days_to_fail = int(rng.integers(1, 120))
        failure_prob = round(rng.uniform(0.15, 0.95), 2)
        health = round(rng.uniform(0.2, 0.95), 2)
        days_to_maint = max(1, days_to_fail - int(rng.integers(5, 20)))

        if failure_prob >= 0.8:
            severity = "critical"
        elif failure_prob >= 0.5:
            severity = "warning"
        else:
            severity = "normal"

        predictions.append({
            **asset,
            "failure_probability": failure_prob,
            "health_score": health,
            "predicted_failure": now + timedelta(days=days_to_fail),
            "recommended_maintenance": now + timedelta(days=days_to_maint),
            "days_to_failure": days_to_fail,
            "days_to_maintenance": days_to_maint,
            "severity": severity,
            "confidence": round(rng.uniform(0.75, 0.98), 2),
            "cost_impact": round(rng.uniform(500, 15000), 0),
        })

    predictions.sort(key=lambda x: x["days_to_failure"])
    return predictions


def _severity_color(severity):
    return {"critical": "#ff5252", "warning": "#ffc107", "normal": "#00e676"}.get(severity, "#9e9e9e")


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


def render_prediction_timeline(container):
    with container:
        st.subheader("Predictive Maintenance Timeline")

        preds = _generate_predictions()
        now = datetime.now()

        crit_count = sum(1 for p in preds if p["severity"] == "critical")
        warn_count = sum(1 for p in preds if p["severity"] == "warning")
        norm_count = sum(1 for p in preds if p["severity"] == "normal")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🔴 Critical", crit_count)
        m2.metric("🟡 Warning", warn_count)
        m3.metric("🟢 Normal", norm_count)
        m4.metric("Total Assets", len(preds))

        tab_timeline, tab_gantt, tab_health, tab_cost = st.tabs(
            ["📅 Maintenance Timeline", "📊 Failure Gantt", "💓 Health Scores", "💰 Cost Impact"]
        )

        with tab_timeline:
            for p in preds:
                color = _severity_color(p["severity"])
                maint_marker = "🔧" if p["days_to_maintenance"] <= 14 else "📆"
                fail_marker = "⚠️" if p["severity"] == "critical" else "📅"

                st.markdown(
                    f"""
                    <div style="
                        background:#0e1117;
                        border:1px solid #262730;
                        border-left:4px solid {color};
                        border-radius:8px;
                        padding:12px 16px;
                        margin-bottom:8px;
                    ">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <strong style="color:{color};">{p['name']}</strong>
                                <span style="color:#666;margin-left:8px;font-size:0.8rem;">
                                    {p['factory']} · {p['type']}
                                </span>
                            </div>
                            <span style="
                                background:{color}22;color:{color};
                                padding:2px 10px;border-radius:12px;
                                font-size:0.75rem;font-weight:600;
                            ">{p['failure_probability']:.0%} risk</span>
                        </div>
                        <div style="display:flex;gap:20px;margin-top:6px;font-size:0.82rem;color:#a0a0a0;">
                            <span>{fail_marker} Failure: {p['predicted_failure'].strftime('%b %d')} ({p['days_to_failure']}d)</span>
                            <span>{maint_marker} Maintenance: {p['recommended_maintenance'].strftime('%b %d')} ({p['days_to_maintenance']}d)</span>
                            <span>Confidence: {p['confidence']:.0%}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with tab_gantt:
            fig = go.Figure()
            for i, p in enumerate(preds):
                color = _severity_color(p["severity"])
                fig.add_trace(go.Bar(
                    y=[p["name"]],
                    x=[p["days_to_maintenance"]],
                    orientation="h",
                    name="Maintenance Window",
                    marker_color=color,
                    base=0,
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{p['name']}</b><br>"
                        f"Maintenance in {p['days_to_maintenance']} days<br>"
                        f"Failure in {p['days_to_failure']} days<br>"
                        f"Risk: {p['failure_probability']:.0%}<extra></extra>"
                    ),
                ))
                fig.add_trace(go.Scatter(
                    x=[p["days_to_failure"]],
                    y=[p["name"]],
                    mode="markers",
                    name="Predicted Failure" if i == 0 else "",
                    marker=dict(color="#ff5252", size=10, symbol="diamond"),
                    showlegend=(i == 0),
                    hovertemplate=(
                        f"<b>{p['name']}</b><br>"
                        f"Predicted failure in {p['days_to_failure']} days<extra></extra>"
                    ),
                ))
            fig.update_layout(**_plotly_base("Maintenance vs Failure Timeline (days)", height=350))
            fig.update_layout(
                xaxis=dict(title="Days from Now", gridcolor="#262730", color="#a0a0a0"),
                barmode="overlay",
            )
            fig.add_vline(x=14, line_dash="dash", line_color="#ffc107", annotation_text="2-week window")
            st.plotly_chart(fig, use_container_width=True, key="pred_gantt")

        with tab_health:
            fig = go.Figure()
            names = [p["name"] for p in preds]
            healths = [p["health_score"] * 100 for p in preds]
            health_colors = [
                "#ff5252" if h < 40 else "#ffc107" if h < 70 else "#00e676"
                for h in healths
            ]

            fig.add_trace(go.Bar(
                y=names, x=healths,
                orientation="h",
                marker_color=health_colors,
                text=[f"{h:.0f}%" for h in healths],
                textposition="auto",
                hovertemplate="<b>%{y}</b><br>Health: %{x:.0f}%<extra></extra>",
            ))
            fig.add_vline(x=40, line_dash="dash", line_color="#ff5252", annotation_text="Critical")
            fig.add_vline(x=70, line_dash="dash", line_color="#ffc107", annotation_text="Warning")
            fig.update_layout(**_plotly_base("Asset Health Scores", height=350))
            fig.update_layout(xaxis=dict(title="Health (%)", range=[0, 105], gridcolor="#262730", color="#a0a0a0"))
            st.plotly_chart(fig, use_container_width=True, key="pred_health")

        with tab_cost:
            total_cost = sum(p["cost_impact"] for p in preds)
            crit_cost = sum(p["cost_impact"] for p in preds if p["severity"] == "critical")

            st.metric("Total Estimated Impact", f"${total_cost:,.0f}")
            st.metric("Critical Assets Impact", f"${crit_cost:,.0f}")

            fig = go.Figure()
            fig.add_trace(go.Pie(
                labels=[p["name"] for p in preds],
                values=[p["cost_impact"] for p in preds],
                hole=0.5,
                marker=dict(colors=[_severity_color(p["severity"]) for p in preds]),
                textinfo="label+percent",
                textfont=dict(size=10, color="white"),
                hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
            ))
            fig.update_layout(
                **_plotly_base("Cost Impact by Asset", height=350),
                showlegend=True,
                legend=dict(font=dict(size=10)),
            )
            st.plotly_chart(fig, use_container_width=True, key="pred_cost")
