import json
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Day 13 Observability Dashboard", layout="wide")
st.title("Day 13 Observability Dashboard")

@st.cache_data(ttl=30)
def load_data():
    try:
        with open("data/logs.jsonl", "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f]
        df = pd.DataFrame(data)
        df["ts"] = pd.to_datetime(df["ts"])
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No data found in data/logs.jsonl")
    st.stop()

# Helpers
responses = df[df["event"] == "response_sent"]
requests = df[df["event"] == "request_received"]
failures = df[df["event"] == "request_failed"]

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Latency Percentiles (ms)")
    st.write("Threshold: P95 <= 3000ms")
    if not responses.empty and "latency_ms" in responses.columns:
        latency = responses["latency_ms"].dropna()
        p50, p95, p99 = latency.quantile([0.5, 0.95, 0.99])
        st.metric("P50", f"{p50:.0f} ms")
        st.metric("P95", f"{p95:.0f} ms", delta=f"{3000 - p95:.0f} ms left", delta_color="normal" if p95 <= 3000 else "inverse")
        st.metric("P99", f"{p99:.0f} ms")
        fig = px.histogram(latency, nbins=20, title="Latency Distribution")
        fig.add_vline(x=3000, line_dash="dash", line_color="red", annotation_text="P95 Threshold (3000ms)")
        st.plotly_chart(fig)

with col2:
    st.subheader("2. Request Traffic")
    st.write("Threshold: >= 1 req/min")
    if not requests.empty:
        total_reqs = len(requests)
        time_span = (requests["ts"].max() - requests["ts"].min()).total_seconds() / 60
        rpm = total_reqs / time_span if time_span > 0 else total_reqs
        st.metric("Total Requests", total_reqs)
        st.metric("Requests/Minute", f"{rpm:.2f}", delta=f"{rpm - 1:.2f} above threshold" if rpm >= 1 else "Below threshold", delta_color="normal" if rpm >= 1 else "inverse")

col3, col4 = st.columns(2)

with col3:
    st.subheader("3. Error Rate & Breakdown")
    st.write("Threshold: Error Rate <= 2%")
    total = len(requests)
    errs = len(failures)
    rate = (errs / total * 100) if total > 0 else 0
    st.metric("Error Rate", f"{rate:.2f}%", delta=f"{2 - rate:.2f}% left", delta_color="normal" if rate <= 2 else "inverse")
    if errs > 0 and "error_type" in failures.columns:
        breakdown = failures["error_type"].value_counts().reset_index()
        breakdown.columns = ["Error Type", "Count"]
        st.table(breakdown)

with col4:
    st.subheader("4. Cost Over Time (USD)")
    st.write("Threshold: Total <= 2.5 USD")
    if not responses.empty and "cost_usd" in responses.columns:
        total_cost = responses["cost_usd"].sum()
        st.metric("Total Cost", f"${total_cost:.4f}", delta=f"${2.5 - total_cost:.4f} left", delta_color="normal" if total_cost <= 2.5 else "inverse")
        responses_min = responses.set_index("ts").resample("1Min")["cost_usd"].sum().reset_index()
        fig2 = px.line(responses_min, x="ts", y="cost_usd", title="Cost per Minute")
        st.plotly_chart(fig2)

col5, col6 = st.columns(2)

with col5:
    st.subheader("5. Input & Output Tokens")
    st.write("Threshold: Total Tokens <= 50,000")
    if not responses.empty and "tokens_in" in responses.columns and "tokens_out" in responses.columns:
        t_in = responses["tokens_in"].sum()
        t_out = responses["tokens_out"].sum()
        t_total = t_in + t_out
        st.metric("Total Tokens", f"{t_total:,.0f}", delta=f"{50000 - t_total:,.0f} left", delta_color="normal" if t_total <= 50000 else "inverse")
        st.metric("Tokens In", f"{t_in:,.0f}")
        st.metric("Tokens Out", f"{t_out:,.0f}")

with col6:
    st.subheader("6. Quality Proxy")
    st.write("Threshold: Mean Score >= 0.75")
    if not responses.empty and "quality_score" in responses.columns:
        mean_quality = responses["quality_score"].mean()
        st.metric("Mean Quality Score", f"{mean_quality:.2f}", delta=f"{mean_quality - 0.75:.2f} diff", delta_color="normal" if mean_quality >= 0.75 else "inverse")
        fig3 = px.box(responses, y="quality_score", title="Quality Score Spread")
        st.plotly_chart(fig3)
