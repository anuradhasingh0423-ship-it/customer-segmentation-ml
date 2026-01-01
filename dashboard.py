import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# =============== APP CONFIG ===============
st.set_page_config(
    page_title="Customer Segmentation Dashboard",
    page_icon="📊",
    layout="wide"
)

# =============== THEME / STYLE ===============
st.markdown("""
<style>

.main {background-color:#0b0b0c;}

h1, h2, h3, p {color:white;}

.glow {
  color: #ff1c1c;
  text-shadow: 0px 0px 20px #e60000;
}

.circle-card {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  border: 2px solid #ff1c1c;
  background: radial-gradient(circle at top, #3b0000, #000);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  box-shadow: 0px 0px 25px #ff0000;
  color:white;
}

</style>
""", unsafe_allow_html=True)

# =============== DATABASE ===============
DB_PATH = "customer_segments.db"

if not os.path.exists(DB_PATH):
    st.error("⚠️ Database not found. Add records using your Flask app first.")
    st.stop()

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM predictions", conn)

# Normalize column names (prevents KeyError)
df.columns = [c.lower() for c in df.columns]

# Rename if needed
df = df.rename(columns={
    "total_spending": "spending"
})

# =============== HEADER ===============
st.markdown("<h1 class='glow'>Customer Segmentation Dashboard</h1>", unsafe_allow_html=True)
st.write("Powered by Machine Learning — Stranger Things Edition 👻")

st.divider()

# =============== KPI CIRCLES ===============
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"<div class='circle-card'><h4>Total Records</h4><h2>{len(df)}</h2></div>",
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"<div class='circle-card'><h4>Avg Income</h4><h2>${df['income'].mean():,.0f}</h2></div>",
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"<div class='circle-card'><h4>Avg Spending</h4><h2>${df['spending'].mean():,.0f}</h2></div>",
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f"<div class='circle-card'><h4>Clusters</h4><h2>{df['cluster'].nunique()}</h2></div>",
        unsafe_allow_html=True
    )

st.divider()

# =============== CHARTS ===============
left, right = st.columns(2)

with left:
    st.subheader("Cluster Distribution")
    fig = px.histogram(df, x="cluster", color="cluster")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Recency vs Spending")
    fig2 = px.scatter(
        df,
        x="recency",
        y="spending",
        color="cluster",
        hover_data=["age"]
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# =============== PERSONA IMAGES ===============
st.subheader("Customer Personas")

image_map = {
    0: "static/personas/budgetactiveshoppers.png",
    1: "static/personas/premiumloyalists.png",
    2: "static/personas/atriskcustomers.png",
    3: "static/personas/loyalseniors.png"
}

cols = st.columns(4)

for i, col in enumerate(cols):
    if os.path.exists(image_map[i]):
        col.image(image_map[i])
        col.caption(f"Cluster {i}")
    else:
        col.info(f"Image missing for cluster {i}")

st.divider()

# =============== RECENT DATA ===============
st.subheader("Recent Predictions")
st.dataframe(df.tail(25), use_container_width=True)
