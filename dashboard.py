import streamlit as st
import pandas as pd
import sqlite3

# =========================
# Page config
# =========================
st.set_page_config(
    page_title="Customer Segmentation",
    layout="wide"
)

# =========================
# Custom CSS (Neon Effects)
# =========================
st.markdown("""
<style>
h1 {
    color: #E50914;
    text-shadow: 0 0 8px #E50914;
}
h2, h3 {
    color: #B5179E;
}
[data-testid="metric-container"] {
    background-color: #1C1C1C;
    border: 1px solid #E50914;
    border-radius: 10px;
    padding: 15px;
}
</style>
""", unsafe_allow_html=True)

st.title(" Customer Segmentation Dashboard")

# =========================
# Load data from DB
# =========================
conn = sqlite3.connect("customer_segments.db")
df = pd.read_sql("SELECT * FROM predictions", conn)
conn.close()

# =========================
# Persona mapping
# =========================
PERSONA_MAP = {
    0: "Budget Active Shoppers",
    1: "Premium Loyalists",
    2: "At-Risk Customers",
    3: "Loyal Seniors"
}
df["Persona"] = df["cluster"].map(PERSONA_MAP)

# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.header("🧭 Upside Down Filters")

persona_filter = st.sidebar.multiselect(
    "Select Personas",
    df["Persona"].unique(),
    default=df["Persona"].unique()
)

filtered_df = df[df["Persona"].isin(persona_filter)]

# =========================
# KPI METRICS
# =========================
st.subheader("📌 Key Metrics")

c1, c2, c3, c4 = st.columns(4)

c1.metric("👥 Customers", len(filtered_df))
c2.metric("💰 Avg Income", int(filtered_df["income"].mean()))
c3.metric("🛒 Avg Spending", int(filtered_df["total_spending"].mean()))
c4.metric("⚠️ At-Risk %",
          f"{(filtered_df['Persona']=='At-Risk Customers').mean()*100:.1f}%")

st.divider()

# =========================
# PERSONA DISTRIBUTION (BAR)
# =========================
st.subheader("👥 Persona Distribution")

persona_counts = filtered_df["Persona"].value_counts()

st.bar_chart(
    persona_counts,
    color="#E50914"
)

# =========================
# SPENDING BY PERSONA (BAR)
# =========================
st.subheader("💸 Average Spending by Persona")

avg_spending = (
    filtered_df
    .groupby("Persona")["total_spending"]
    .mean()
    .sort_values()
)

st.bar_chart(
    avg_spending,
    color="#B5079E"
)


# CHURN ZONE (TABLE)

st.subheader("🧟 Churn Zone (At-Risk Customers)")

at_risk = filtered_df[filtered_df["Persona"] == "At-Risk Customers"]

st.dataframe(
    at_risk[["income", "age", "total_spending", "recency"]],
    use_container_width=True
)


# FOOTER

st.markdown(
    "<center><small>⚡ Built with ML in the Upside Down</small></center>",
    unsafe_allow_html=True
)
