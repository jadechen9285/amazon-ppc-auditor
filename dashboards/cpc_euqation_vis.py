import numpy as np
import plotly.graph_objects as go
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Traffic Elasticity Demo", layout="wide")

st.title("📈 The Law of Diminishing Returns in Ad Bidding")
st.markdown("Adjust the current state below to see how different elasticity scenarios (β) dictate the traffic plateau.")

# --- INTERACTIVE CONTROLS ---
col1, col2 = st.columns(2)
with col1:
    current_cpc = st.number_input("Current CPC Bid (€)", min_value=0.10, value=1.00, step=0.10)
with col2:
    current_clicks = st.number_input("Current Traffic (Clicks)", min_value=1, value=100, step=10)

st.divider()

# --- DATA GENERATION ---
# Generate proposed bids up to 5x the current CPC to clearly show the plateau
cpc_new = np.linspace(0.10, current_cpc * 5, 200)
cpc_ratio = cpc_new / current_cpc

# Calculate predicted clicks for different Beta (elasticity) values
clicks_high = current_clicks * np.power(cpc_ratio, 0.8)  # Beta = 0.8
clicks_med = current_clicks * np.power(cpc_ratio, 0.4)   # Beta = 0.4
clicks_low = current_clicks * np.power(cpc_ratio, 0.15)  # Beta = 0.15

# --- BUILD THE CHART ---
fig = go.Figure()

# High Elasticity Curve
fig.add_trace(go.Scatter(
    x=cpc_new, y=clicks_high, mode='lines', 
    name='High Growth Potential (β = 0.8)',
    line=dict(color='#00CC96', width=3)
))

# Medium Elasticity Curve
fig.add_trace(go.Scatter(
    x=cpc_new, y=clicks_med, mode='lines', 
    name='Standard Diminishing Returns (β = 0.4)',
    line=dict(color='#636EFA', width=3)
))

# Low Elasticity Curve
fig.add_trace(go.Scatter(
    x=cpc_new, y=clicks_low, mode='lines', 
    name='Saturated Market (β = 0.15)',
    line=dict(color='#EF553B', width=3)
))

# Current State Marker
fig.add_trace(go.Scatter(
    x=[current_cpc], y=[current_clicks], mode='markers+text',
    name='Current Position',
    marker=dict(color='white', size=12, line=dict(color='black', width=2)),
    text=[f'Current State (€{current_cpc:.2f})'], textposition='bottom right'
))

# Formatting for presentation
fig.update_layout(
    xaxis_title="Proposed CPC Bid (€)",
    yaxis_title="Predicted Traffic (Clicks)",
    hovermode="x unified",
    legend=dict(yanchor="bottom", y=0.05, xanchor="right", x=0.95),
    height=600,
    margin=dict(l=0, r=0, t=30, b=0)
)

# Render in Streamlit
st.plotly_chart(fig, use_container_width=True)

# --- EXPLANATION TEXT ---
st.info("**How to read this chart:** The curves show what happens as we increase our bids. Notice how the red line (Saturated Market) flattens out very quickly. If a keyword is saturated, doubling our bid from €1.00 to €2.00 gets us almost zero new clicks—it just eats into our profit margin.")