import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


def _generate_model_data():
    rng = np.random.default_rng()
    rounds = list(range(1, 21))
    accuracy = np.clip(0.6 + 0.35 * (1 - np.exp(-np.array(rounds) / 5)) + rng.normal(0, 0.02, 20), 0, 1)
    precision = np.clip(accuracy + rng.normal(0, 0.015, 20), 0, 1)
    recall = np.clip(accuracy - 0.03 + rng.normal(0, 0.02, 20), 0, 1)
    f1 = 2 * precision * recall / (precision + recall + 1e-9)
    return pd.DataFrame({
        "round": rounds,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
    })


def _generate_factory_contribution():
    return pd.DataFrame({
        "factory": ["Factory A", "Factory B", "Factory C"],
        "data_points": [12500, 11800, 13200],
        "uptime_pct": [98.5, 96.2, 99.1],
        "model_updates": [20, 20, 20],
    })


def render_model_metrics(container):
    with container:
        st.subheader("Model Performance")
        df = _generate_model_data()
        latest = df.iloc[-1]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Accuracy", f"{latest['accuracy']:.1%}", delta=f"+{latest['accuracy'] - df.iloc[-2]['accuracy']:.1%}")
        m2.metric("Precision", f"{latest['precision']:.1%}", delta=f"+{latest['precision'] - df.iloc[-2]['precision']:.1%}")
        m3.metric("Recall", f"{latest['recall']:.1%}", delta=f"+{latest['recall'] - df.iloc[-2]['recall']:.1%}")
        m4.metric("F1 Score", f"{latest['f1_score']:.1%}", delta=f"+{latest['f1_score'] - df.iloc[-2]['f1_score']:.1%}")

        chart_col, table_col = st.columns([2, 1])

        with chart_col:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["round"], y=df["accuracy"],
                mode="lines+markers", name="Accuracy",
                line=dict(color="#42a5f5", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=df["round"], y=df["f1_score"],
                mode="lines+markers", name="F1 Score",
                line=dict(color="#66bb6a", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=df["round"], y=df["precision"],
                mode="lines", name="Precision",
                line=dict(color="#ffa726", width=1.5, dash="dot"),
            ))
            fig.add_trace(go.Scatter(
                x=df["round"], y=df["recall"],
                mode="lines", name="Recall",
                line=dict(color="#ab47bc", width=1.5, dash="dot"),
            ))
            fig.update_layout(
                title=dict(text="Federated Learning Progress", font=dict(size=14, color="#e0e0e0")),
                height=320,
                margin=dict(l=50, r=20, t=40, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(14,17,23,1)",
                xaxis=dict(title="Round", gridcolor="#262730", color="#a0a0a0"),
                yaxis=dict(title="Score", gridcolor="#262730", color="#a0a0a0", range=[0.4, 1]),
                font=dict(color="#a0a0a0"),
                legend=dict(orientation="h", y=1.12, font=dict(size=10)),
            )
            st.plotly_chart(fig, use_container_width=True)

        with table_col:
            st.markdown("**Participating Factories**")
            contrib = _generate_factory_contribution()
            st.dataframe(
                contrib,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "factory": st.column_config.TextColumn("Factory"),
                    "data_points": st.column_config.NumberColumn("Data Points"),
                    "uptime_pct": st.column_config.ProgressColumn("Uptime %", min_value=0, max_value=100),
                    "model_updates": st.column_config.NumberColumn("Updates"),
                },
            )
            st.caption(f"Latest model: round {int(latest['round'])} | 3 participating factories")
