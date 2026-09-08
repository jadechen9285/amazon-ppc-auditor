import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.optimize import minimize

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Ad Margin Rescuer | Executive Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Ad Budget Reallocation Copilot")
st.caption("Maximize True Incremental Sales (增量销售) by reallocating wasted ad budget from 'Bleeders' to 'Starved Winners'.")

# --- SIDEBAR: CONTROLS & CSV UPLOAD ---
st.sidebar.header("🕹️ Demo Controls")
uploaded_file = st.sidebar.file_uploader("Upload Seller Financial CSV", type=["csv"])

# --- SIMULATED DATA GENERATOR (Matches Pre-Optimization Schema) ---
@st.cache_data
def generate_aligned_demo_data():
    np.random.seed(42)
    n_skus = 50
    # Generating numeric-looking SKUs to simulate the user's actual data
    skus = [str(20000 + i) for i in range(n_skus)] 
    
    profiles = np.random.choice(['Bleeder', 'Starved_Winner', 'Normal'], size=n_skus, p=[0.25, 0.20, 0.55])
    organic_rev = np.random.uniform(500, 5000, size=n_skus)
    
    alphas = np.where(profiles == 'Bleeder', np.random.uniform(10, 25, size=n_skus),
             np.where(profiles == 'Starved_Winner', np.random.uniform(70, 120, size=n_skus),
                      np.random.uniform(30, 60, size=n_skus)))
    
    current_spend = np.where(profiles == 'Bleeder', organic_rev * 0.4,
                    np.where(profiles == 'Starved_Winner', organic_rev * 0.02,
                             organic_rev * 0.15))
    
    cogs_fba = np.random.uniform(0.4, 0.6, size=n_skus)
    ad_rev = alphas * np.log1p(current_spend)
    
    # Simulating somewhat realistic clicks for the CPC calculation ($0.50 to $3.50 CPC)
    simulated_clicks = np.maximum(1, current_spend / np.random.uniform(0.5, 3.5, size=n_skus)).astype(int)
    
    return pd.DataFrame({
        'StockCode': skus,
        'total_units': np.random.randint(20, 500, size=n_skus),
        'organic_revenue': organic_rev,
        'implied_price': np.random.uniform(15, 80, size=n_skus),
        'cogs_fba_rate': cogs_fba,
        'unit_cost': np.random.uniform(3, 15, size=n_skus),
        'pre_ad_profit': organic_rev * (1 - cogs_fba),
        'profile': profiles,
        'ad_alpha': alphas,
        'stock_code': skus,
        'total_ad_spend': current_spend,
        'total_ad_revenue': ad_rev,
        'total_impressions': np.random.randint(1000, 50000, size=n_skus),
        'total_clicks': simulated_clicks,
        'total_ad_orders': np.random.randint(5, 200, size=n_skus),
        'current_ad_spend': current_spend
    })

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    df = generate_aligned_demo_data()

# Data Cleaning & Formatting
def clean_action_tag(profile_str):
    p = str(profile_str).lower()
    if 'bleeder' in p: return "Bleeder (RED)"
    elif 'starved' in p: return "Starved Winner (GREEN)"
    return "Maintain (BLUE)"

df['ui_profile'] = df['profile'].apply(clean_action_tag)
df['total_gross_revenue'] = df['organic_revenue'] + df['total_ad_revenue']

# Calculate Avg CPC
df['cpc'] = np.where(df['total_clicks'] > 0, df['total_ad_spend'] / df['total_clicks'], 0)

# --- INEQUALITY OPTIMIZATION ENGINE ---
total_budget = df['current_ad_spend'].sum()
alphas = df['ad_alpha'].values
cogs_fba_rates = df['cogs_fba_rate'].values
organic_revs = df['organic_revenue'].values

def objective_profit(spends):
    revenues = organic_revs + alphas * np.log1p(spends)
    profits = revenues * (1 - cogs_fba_rates) - spends
    return -np.sum(profits)

constraints = [{'type': 'ineq', 'fun': lambda spends: total_budget - np.sum(spends)}]
bounds = [(0, None) for _ in range(len(df))]

opt_result = minimize(
    objective_profit,
    x0=df['current_ad_spend'].values,
    method='SLSQP',
    bounds=bounds,
    constraints=constraints
)

df['optimized_ad_spend'] = opt_result.x
df['spend_delta'] = df['optimized_ad_spend'] - df['current_ad_spend']

# Calculate Core Metrics
df['current_inc_rev'] = alphas * np.log1p(df['current_ad_spend'])
df['optimized_inc_rev'] = alphas * np.log1p(df['optimized_ad_spend'])
df['current_true_iroas'] = np.where(df['current_ad_spend'] > 0.01, df['current_inc_rev'] / df['current_ad_spend'], 0)
df['current_projected_profit'] = (organic_revs + df['current_inc_rev']) * (1 - cogs_fba_rates) - df['current_ad_spend']
df['optimized_projected_profit'] = (organic_revs + df['optimized_inc_rev']) * (1 - cogs_fba_rates) - df['optimized_ad_spend']

# Aggregations for KPI Cards
spend_cut_bleeders = df[df["spend_delta"] < 0]["spend_delta"].sum()
curr_total_profit = df['current_projected_profit'].sum()
opt_total_profit = df['optimized_projected_profit'].sum()
profit_lift = opt_total_profit - curr_total_profit
lift_pct = (profit_lift / curr_total_profit) * 100 if curr_total_profit > 0 else 0
optimized_total_spend = df['optimized_ad_spend'].sum()
unspent_savings = total_budget - optimized_total_spend

# --- EXECUTIVE SUMMARY CARDS ---
st.markdown("### 📊 Executive Summary (30-Day Projection)")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Current Projected Profit", f"${curr_total_profit:,.2f}")
m2.metric("Optimized Projected Profit", f"${opt_total_profit:,.2f}", f"+${profit_lift:,.2f}")
m3.metric("Net Profit Increase", f"+{lift_pct:.1f}%")
m4.metric("Capital Preserved", f"${unspent_savings:,.2f}")

st.divider()

# --- THE "WHY" VISUALIZATION (Non-Technical Explanation) ---
st.subheader("🎯 The Ad Efficiency Simulator")
st.caption("Select a SKU below to see its exact ad-spend curve. This visualization explains **why** the AI recommends increasing or decreasing budget based on diminishing returns.")

col_sel, col_chart = st.columns([1, 3])

with col_sel:
    selected_sku = st.selectbox("Select a SKU ID:", df.sort_values(by='spend_delta', ascending=False)['StockCode'].unique())
    sku_data = df[df['StockCode'] == selected_sku].iloc[0]
    
    st.markdown(f"**Status:** {sku_data['ui_profile']}")
    st.markdown(f"**Current Spend:** ${sku_data['current_ad_spend']:,.2f}")
    st.markdown(f"**Target Spend:** ${sku_data['optimized_ad_spend']:,.2f}")
    
    if sku_data['spend_delta'] > 0:
        st.success(f"Action: Invest ${sku_data['spend_delta']:,.2f} more here.")
    else:
        st.error(f"Action: Cut ${abs(sku_data['spend_delta']):,.2f} from this SKU.")

with col_chart:
    # Generate points for the logarithmic curve
    max_x_val = max(sku_data['current_ad_spend'], sku_data['optimized_ad_spend']) * 1.5
    max_x_val = max(max_x_val, 50) # Ensure a minimum x-axis width
    
    x_vals = np.linspace(0, max_x_val, 200)
    y_vals = sku_data['ad_alpha'] * np.log1p(x_vals)
    
    fig_curve = go.Figure()
    
    # Plot the mathematical curve
    fig_curve.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode='lines', name='Revenue Potential Curve',
        line=dict(color='rgba(255, 255, 255, 0.2)', width=4, dash='dot')
    ))
    
    # Add Current Spend Point
    curr_y = sku_data['ad_alpha'] * np.log1p(sku_data['current_ad_spend'])
    fig_curve.add_trace(go.Scatter(
        x=[sku_data['current_ad_spend']], y=[curr_y],
        mode='markers+text', name='Current Status',
        marker=dict(color='#FFA15A', size=14, symbol='x'),
        text=['Current Spend'], textposition='top center',
        textfont=dict(color='#FFA15A')
    ))
    
    # Add Target Spend Point
    opt_y = sku_data['ad_alpha'] * np.log1p(sku_data['optimized_ad_spend'])
    fig_curve.add_trace(go.Scatter(
        x=[sku_data['optimized_ad_spend']], y=[opt_y],
        mode='markers+text', name='AI Target',
        marker=dict(color='#00CC96', size=16),
        text=['Optimized Target'], textposition='bottom center',
        textfont=dict(color='#00CC96')
    ))
    
    fig_curve.update_layout(
        xaxis_title="Ad Spend Input ($)", 
        yaxis_title="True Incremental Sales Out ($)", 
        height=350,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_curve, use_container_width=True)

st.divider()

# --- TRADITIONAL CHARTS ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🔬 True Incremental Sales vs Cannibalization")
    top_skus = df.sort_values('total_gross_revenue', ascending=False).head(10)
    
    fig_stacked = go.Figure(data=[
        go.Bar(name='Organic Baseline (No Ads)', x=top_skus['StockCode'], y=top_skus['organic_revenue'], marker_color='#1f77b4'),
        go.Bar(name='True Incremental Ad Sales', x=top_skus['StockCode'], y=top_skus['current_inc_rev'], marker_color='#00CC96')
    ])
    fig_stacked.update_layout(
        barmode='stack', 
        xaxis_type='category',  # FIX: Forces string SKU IDs to plot evenly without numeric gaps
        yaxis_title="Revenue ($)", 
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_stacked, use_container_width=True)

with col_right:
    st.subheader("🔄 Budget Shift Dynamics")
    fig_scatter = px.scatter(
        df,
        x='current_ad_spend', y='optimized_ad_spend',
        color='ui_profile', size='total_gross_revenue',
        hover_data=['StockCode', 'spend_delta'],
        labels={'current_ad_spend': 'Current Ad Spend ($)', 'optimized_ad_spend': 'Recommended Ad Spend ($)', 'ui_profile': 'Profile'},
        color_discrete_map={'Bleeder (RED)': '#EF553B', 'Starved Winner (GREEN)': '#00CC96', 'Maintain (BLUE)': '#636EFA'}
    )
    max_val = max(df['current_ad_spend'].max(), df['optimized_ad_spend'].max())
    fig_scatter.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="Gray", dash="dash"))
    fig_scatter.update_layout(height=400)
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# --- ACTIONABLE CHECKLIST TABLE (WITH CPC) ---
st.subheader("📋 Today's Actionable Checklist for Seller Central")

actionable_df = df[np.abs(df['spend_delta']) > 1.0].copy()
actionable_df['Action'] = np.where(actionable_df['spend_delta'] > 0, "📈 INCREASE", "📉 DECREASE")
actionable_df['Change ($)'] = actionable_df['spend_delta'].abs()

# Added the 'cpc' column into the table presentation
summary_table = actionable_df[['StockCode', 'ui_profile', 'Action', 'cpc', 'current_true_iroas', 'current_ad_spend', 'optimized_ad_spend', 'Change ($)']]
summary_table.columns = ['SKU ID', 'Profile Status', 'Action Required', 'Avg CPC ($)', 'True iROAS (x)', 'Current Budget ($)', 'Target Budget ($)', 'Delta ($)']

st.dataframe(
    summary_table.sort_values(by='Delta ($)', ascending=False).style.format({
        'Avg CPC ($)': '${:.2f}',
        'True iROAS (x)': '{:.2f}x',
        'Current Budget ($)': '${:,.2f}',
        'Target Budget ($)': '${:,.2f}',
        'Delta ($)': '${:,.2f}'
    }).background_gradient(subset=['True iROAS (x)'], cmap='RdYlGn'),
    use_container_width=True,
    hide_index=True
)