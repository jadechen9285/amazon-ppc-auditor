import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit_authenticator as stauth
from scipy.optimize import minimize

# ==========================================
# 0. CONFIG & SAAS STYLING
# ==========================================
st.set_page_config(page_title='Ad Margin Rescuer | CPC Optimizer', page_icon='🎯', layout='wide')


def inject_saas_styling():
    """Strips away Streamlit branding and tightens the UI to feel like a production SaaS."""
    hide_st_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                header {visibility: hidden;}
                .block-container {
                    padding-top: 2rem;
                    padding-bottom: 0rem;
                }
                [data-testid="stMetricValue"] {
                    font-size: 1.8rem;
                    font-weight: 600;
                }
                </style>
                """
    st.markdown(hide_st_style, unsafe_allow_html=True)


inject_saas_styling()

# ==========================================
# 1. AUTHENTICATION GATE
# ==========================================
# Define your MVP beta clients here
credentials = {
    'usernames': {
        'beta_client_1': {
            'email': 'client@shenzhen-smb.com',
            'name': 'Beta Client A',
            'password': '$2b$12$9zxGyOlLz5PU7mye5EDmQ.dNXWY9CoG6SvG.blMuNhDMSBrVhSRhG',  # Paste the hashed password generated earlier
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    'cpc_optimizer_dashboard',  # Cookie name
    'auth_signature_key',  # Secret key for cookie encryption (change this!)
    cookie_expiry_days=30,  # Keeps them logged in for 30 days
)

# Renders the login widget
authenticator.login()

# ==========================================
# 2. APPLICATION ROUTING
# ==========================================
if st.session_state['authentication_status'] is False:
    st.error('用户名或密码错误，请重试。')

elif st.session_state['authentication_status'] is None:
    st.warning('请输入您的用户名和密码以访问竞价优化引擎。')

elif st.session_state['authentication_status']:
    # --- SUCCESSFUL LOGIN ---

    # Render the logout button in Chinese
    authenticator.logout('退出登录', 'sidebar')
    st.sidebar.write(f'欢迎回来, *{st.session_state["name"]}*')
    st.sidebar.divider()

    # ==========================================
    # 3. CORE APPLICATION (INDENT EVERYTHING BELOW HERE)
    # ==========================================
    CURRENCY = '€'

    # ==========================================
    # 1. i18n TRANSLATION DICTIONARY
    # ==========================================
    t = {
        'en': {
            'title': '🎯 Keyword CPC Bid Optimization Copilot',
            'subtitle': 'Maximize Net Profit using Bayesian-smoothed elasticity (β) loaded from backend.',
            'sidebar_title': '🕹️ Parameters',
            'upload_prompt': 'Upload Preprocessed CSV (16 Columns)',
            'margin_override': 'Override Margin (%)',
            # Financial Section
            'financial_header': '### 📊 Financial Projections',
            'kpi_profit': 'Projected Net Profit',
            'kpi_sales': 'Projected Ad Sales',
            'kpi_spend': 'Projected Ad Spend',
            'kpi_iroas': 'Marginal iROAS',
            'kpi_efficiency': 'Spend Reduced',
            # Efficiency Section
            'efficiency_header': '### ⚖️ Efficiency Metrics (Current vs. Optimized)',
            'kpi_acos_curr': 'Current ACoS',
            'kpi_acos_opt': 'Optimized ACoS',
            'kpi_roas_curr': 'Current ROAS',
            'kpi_roas_opt': 'Optimized ROAS',
            # UI Elements
            'timeline_title': '⏳ When will I see the profit lift? (Click to expand)',
            'timeline_1': '**Days 1-2 (Traffic Shift):** New bids take effect. Spend and impressions will change immediately. ACoS may look temporarily high.',
            'timeline_2': '**Days 3-7 (Attribution Lag):** Sales are rolling in but still attributing to the clicks. Do not evaluate profit yet.',
            'timeline_3': '**Days 14-30 (True Lift):** The data has matured and weekly seasonality is smoothed. This is when you measure the final profit lift.',
            # Chart & Table Elements
            'chart_title': '🔬 The Profit Engine Simulator',
            'chart_caption': 'Select a keyword to visualize its Bayesian-smoothed curve (β) and optimal target bid.',
            'chart_x': f'CPC Bid Input ({CURRENCY})',
            'chart_y': f'Predicted Net Profit ({CURRENCY})',
            'legend_curve': 'Profit Curve',
            'legend_curr': 'Current',
            'legend_opt': 'Optimal',
            'top_groups_title': '🏆 Top Ad Groups by Profit Lift',
            'bar_x': f'Profit Lift ({CURRENCY})',
            'ledger_title': '📋 Actionable Bid Ledger',
            'curr_cpc_label': 'Current CPC',
            'opt_cpc_label': 'Optimized Target',
            # Selection Box Elements
            'select_target': 'Select Target:',
            'sim_group': 'Group',
            'sim_beta': 'β Smoothed',
            'sim_rpc': 'True RPC',
            # Dataframe Columns & Plotly Labels
            'col_group': 'Ad Group',
            'col_target': 'Targeting',
            'col_beta': 'β',
            'col_curr_cpc': 'Curr CPC',
            'col_opt_cpc': 'Opt CPC',
            'col_delta': 'Δ CPC',
            'col_lift': 'Lift',
        },
        'cn': {
            'title': '🎯 亚马逊竞价优化引擎 (CPC Optimizer)',
            'subtitle': '基于后端导入的贝叶斯平滑弹性 (β) 的纯利润最大化算法。',
            'sidebar_title': '🕹️ 参数设置',
            'upload_prompt': '上传已预处理的数据 (CSV, 16列)',
            'margin_override': '毛利率预设 (%)',
            # Financial Section
            'financial_header': '### 📊 财务预测总览',
            'kpi_profit': '预期净利润',
            'kpi_sales': '预期广告销售额',
            'kpi_spend': '预期广告花费',
            'kpi_iroas': '边际投入产出比 (iROAS)',
            'kpi_efficiency': '预算节省比例',
            # Efficiency Section
            'efficiency_header': '### ⚖️ 投放效率指标 (当前 vs 优化后)',
            'kpi_acos_curr': '当前 ACoS',
            'kpi_acos_opt': '优化后 ACoS',
            'kpi_roas_curr': '当前 ROAS',
            'kpi_roas_opt': '优化后 ROAS',
            # UI Elements
            'timeline_title': '⏳ 我需要多久才能看到利润增长？(点击展开说明)',
            'timeline_1': '**第 1-2 天 (流量波动期):** 新竞价生效，花费和曝光会立即改变。注意：此时 ACoS 可能会暂时升高，请勿恐慌。',
            'timeline_2': '**第 3-7 天 (归因延迟期):** 订单开始产生，但亚马逊需要 7 天时间将销量归因到点击上。此时评估利润仍不准确。',
            'timeline_3': '**第 14-30 天 (利润显现期):** 数据已完全成熟并平滑了周末波动。此时可以准确评估最终的净利润提升。',
            # Chart & Table Elements
            'chart_title': '🔬 利润曲线模拟器',
            'chart_caption': '选择一个关键词以可视化其贝叶斯平滑弹性曲线 (β) 及最佳目标出价。',
            'chart_x': f'CPC 出价 ({CURRENCY})',
            'chart_y': f'预期净利润 ({CURRENCY})',
            'legend_curve': '利润曲线',
            'legend_curr': '当前',
            'legend_opt': '最优',
            'top_groups_title': '🏆 顶级广告组 (按利润提升排序)',
            'bar_x': f'净利提升 ({CURRENCY})',
            'ledger_title': '📋 竞价执行清单',
            'curr_cpc_label': '当前出价',
            'opt_cpc_label': '优化出价',
            # Selection Box Elements
            'select_target': '选择目标关键词:',
            'sim_group': '所属广告组',
            'sim_beta': '平滑后 β',
            'sim_rpc': '真实 RPC',
            # Dataframe Columns & Plotly Labels
            'col_group': '广告组',
            'col_target': '投放目标',
            'col_beta': 'β (弹性)',
            'col_curr_cpc': '当前出价',
            'col_opt_cpc': '优化出价',
            'col_delta': '出价差额',
            'col_lift': '净利提升',
        },
    }

    # ==========================================
    # 2. STATE INJECTION
    # ==========================================
    lang = st.sidebar.radio('Language / 语言', ['cn', 'en'], index=0)
    c = t[lang]

    st.title(c['title'])
    st.caption(c['subtitle'])

    with st.expander(c['timeline_title']):
        st.info(f'1. {c["timeline_1"]}\n2. {c["timeline_2"]}\n3. {c["timeline_3"]}')

    # ==========================================
    # 3. SIDEBAR CONTROLS
    # ==========================================
    st.sidebar.header(c['sidebar_title'])
    uploaded_file = st.sidebar.file_uploader(c['upload_prompt'], type=['csv'])
    ASSUMED_MARGIN_OVERRIDE = (
        st.sidebar.slider(c['margin_override'], min_value=10, max_value=80, value=30, step=5) / 100
    )

    # ==========================================
    # 4. DATA PIPELINE (Mock / Upload)
    # ==========================================
    @st.cache_data
    def load_demo_schema_data():
        np.random.seed(42)
        n_rows = 270
        ad_groups = [f'Ad Group {i}' for i in ['Alpha', 'Beta', 'Gamma', 'Delta']]
        return pd.DataFrame(
            {
                'campaign_name': ['Core Products'] * n_rows,
                'ad_group_name': np.random.choice(ad_groups, n_rows),
                'targeting': [f'keyword exact {i}' for i in range(n_rows)],
                'match_type': ['EXACT'] * n_rows,
                'spend': np.random.uniform(5.0, 100.0, n_rows),
                'clicks': np.random.randint(5, 50, n_rows),
                'impressions': np.random.randint(100, 5000, n_rows),
                'current_cpc': np.random.uniform(0.5, 3.0, n_rows),
                'mature_sales': np.random.uniform(10.0, 300.0, n_rows),
                'mature_orders': np.random.randint(1, 10, n_rows),
                'mature_clicks': np.random.randint(5, 40, n_rows),
                'true_rpc': np.random.uniform(3.0, 12.0, n_rows),
                'true_cvr': np.random.uniform(0.05, 0.25, n_rows),
                'beta_smoothed': np.random.uniform(0.3, 0.6, n_rows),
                'beta_local': np.random.uniform(0.1, 0.9, n_rows),
                'assumed_margin': [0.30] * n_rows,
            }
        )

    if uploaded_file is not None:
        df_agg = pd.read_csv(uploaded_file)
    else:
        df_agg = load_demo_schema_data()

    df_agg['assumed_margin'] = ASSUMED_MARGIN_OVERRIDE
    df_agg = (
        df_agg[df_agg['current_cpc'] > 0]
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=['current_cpc', 'true_rpc', 'beta_smoothed'])
    )

    # ==========================================
    # 5. CORE OPTIMIZATION SOLVER
    # ==========================================
    @st.cache_data
    def run_slsqp_solver(df: pd.DataFrame, margin: float):
        curr_cpcs = np.maximum(df['current_cpc'].values, 0.01)
        curr_clicks = df['clicks'].values
        rpcs = df['true_rpc'].values
        margins = np.full(len(df), margin)
        betas = df['beta_smoothed'].values
        tot_budget = df['spend'].sum()

        def simulate(new_cpcs):
            cpc_ratio = new_cpcs / curr_cpcs
            p_clicks = curr_clicks * np.power(cpc_ratio, betas)
            p_spend = p_clicks * new_cpcs
            p_profit = (p_clicks * rpcs * margins) - p_spend
            return p_clicks, p_spend, p_profit

        def objective(new_cpcs):
            return -np.sum(simulate(new_cpcs)[2])

        bounds = [(0.02, 15.0) for _ in range(len(df))]
        res = minimize(
            objective,
            x0=curr_cpcs,
            method='SLSQP',
            bounds=bounds,
            constraints=[{'type': 'ineq', 'fun': lambda x: tot_budget - np.sum(simulate(x)[1])}],
            options={'maxiter': 250, 'ftol': 1e-6},
        )

        df_res = df.copy()
        df_res['optimized_cpc'] = res.x
        df_res['cpc_delta'] = df_res['optimized_cpc'] - df_res['current_cpc']
        _, df_res['current_spend'], df_res['current_profit'] = simulate(curr_cpcs)
        df_res['pred_clicks'], df_res['pred_spend'], df_res['pred_profit'] = simulate(res.x)
        df_res['profit_lift'] = df_res['pred_profit'] - df_res['current_profit']
        return df_res

    df_opt = run_slsqp_solver(df_agg, ASSUMED_MARGIN_OVERRIDE)

    # ==========================================
    # 6. BUSINESS METRICS CALCULATION
    # ==========================================
    base_sales = np.sum(df_opt['clicks'] * df_opt['true_rpc'])
    pred_sales = np.sum(df_opt['pred_clicks'] * df_opt['true_rpc'])
    delta_rev = pred_sales - base_sales

    base_spend, pred_spend = df_opt['current_spend'].sum(), df_opt['pred_spend'].sum()
    spend_delta = pred_spend - base_spend

    base_profit, pred_profit = df_opt['current_profit'].sum(), df_opt['pred_profit'].sum()
    profit_lift = pred_profit - base_profit

    base_acos = (base_spend / base_sales) * 100 if base_sales > 0 else 0
    pred_acos = (pred_spend / pred_sales) * 100 if pred_sales > 0 else 0
    acos_delta = pred_acos - base_acos

    base_roas = base_sales / base_spend if base_spend > 0 else 0
    pred_roas = pred_sales / pred_spend if pred_spend > 0 else 0
    roas_delta = pred_roas - base_roas

    if abs(spend_delta) > 0.01 and spend_delta > 0:
        iroas_str = f'{delta_rev / spend_delta:.2f}x'
        iroas_label = c['kpi_iroas']
    else:
        efficiency_pct = (abs(spend_delta) / base_spend) * 100 if base_spend > 0 else 0
        iroas_str = f'{efficiency_pct:.1f}%'
        iroas_label = c['kpi_efficiency']

    if base_profit > 0:
        pct_lift = f'+{(profit_lift / base_profit) * 100:.1f}%'
    elif base_profit <= 0 and pred_profit > 0:
        pct_lift = 'Turnaround'
    else:
        pct_lift = f'+{(profit_lift / abs(base_profit)) * 100:.1f}%'

    # ==========================================
    # 7. UI DASHBOARD RENDER
    # ==========================================
    # --- Row 1: Absolute Financials ---
    st.markdown(c['financial_header'])
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(
        c['kpi_profit'],
        f'{CURRENCY}{pred_profit:,.2f}',
        f'{CURRENCY}{profit_lift:,.2f} ({pct_lift})',
    )
    kpi2.metric(c['kpi_sales'], f'{CURRENCY}{pred_sales:,.2f}', f'{CURRENCY}{delta_rev:,.2f} Delta')
    kpi3.metric(
        c['kpi_spend'],
        f'{CURRENCY}{pred_spend:,.2f}',
        f'{CURRENCY}{spend_delta:,.2f}',
        delta_color='inverse',
    )
    kpi4.metric(iroas_label, iroas_str, delta_color='off')

    st.divider()

    # --- Row 2: Efficiency Ratios ---
    st.markdown(c['efficiency_header'])
    e1, e2, e3, e4 = st.columns(4)
    e1.metric(c['kpi_acos_curr'], f'{base_acos:.1f}%')
    e2.metric(c['kpi_acos_opt'], f'{pred_acos:.1f}%', f'{acos_delta:.1f}%', delta_color='inverse')
    e3.metric(c['kpi_roas_curr'], f'{base_roas:.2f}x')
    e4.metric(c['kpi_roas_opt'], f'{pred_roas:.2f}x', f'{roas_delta:.2f}x')

    st.divider()

    # --- Row 3: The Simulator ---
    st.subheader(c['chart_title'])
    st.caption(c['chart_caption'])

    col_sel, col_chart = st.columns([1, 3])

    with col_sel:
        with st.container(border=True):
            selected_kw = st.selectbox(
                c['select_target'],
                df_opt.sort_values(by='profit_lift', ascending=False)['targeting'],
            )
            kw_data = df_opt[df_opt['targeting'] == selected_kw].iloc[0]

            st.markdown(f'**{c["sim_group"]}:** `{kw_data["ad_group_name"]}`')
            # st.markdown(f"**{c['sim_beta']}:** `{kw_data['beta_smoothed']:.2f}`")
            st.markdown(f'**{c["sim_rpc"]}:** `{CURRENCY}{kw_data["true_rpc"]:,.2f}`')
            st.divider()
            st.metric(c['curr_cpc_label'], f'{CURRENCY}{kw_data["current_cpc"]:,.2f}')
            st.metric(
                c['opt_cpc_label'],
                f'{CURRENCY}{kw_data["optimized_cpc"]:,.2f}',
                f'{CURRENCY}{kw_data["cpc_delta"]:,.2f}',
            )

    with col_chart:
        max_plot_cpc = max(kw_data['current_cpc'], kw_data['optimized_cpc']) * 1.5
        x_vals = np.linspace(0.05, max_plot_cpc, 200)
        cpc_ratio = x_vals / max(kw_data['current_cpc'], 0.01)
        sim_clicks = kw_data['clicks'] * np.power(cpc_ratio, kw_data['beta_smoothed'])
        sim_profit = (sim_clicks * kw_data['true_rpc'] * kw_data['assumed_margin']) - (
            sim_clicks * x_vals
        )

        fig_curve = go.Figure()
        fig_curve.add_trace(
            go.Scatter(
                x=x_vals,
                y=sim_profit,
                mode='lines',
                name=c['legend_curve'],
                line=dict(color='rgba(255, 255, 255, 0.4)', width=3),
            )
        )

        fig_curve.add_trace(
            go.Scatter(
                x=[kw_data['current_cpc']],
                y=[kw_data['current_profit']],
                mode='markers+text',
                name=c['legend_curr'],
                marker=dict(color='#FFA15A', size=12, symbol='x'),
                text=[c['legend_curr']],
                textposition='bottom right',
            )
        )

        fig_curve.add_trace(
            go.Scatter(
                x=[kw_data['optimized_cpc']],
                y=[kw_data['pred_profit']],
                mode='markers+text',
                name=c['legend_opt'],
                marker=dict(color='#00CC96', size=16),
                text=[c['legend_opt']],
                textposition='top left',
                textfont=dict(color='#00CC96'),
            )
        )

        fig_curve.update_layout(
            xaxis_title=c['chart_x'],
            yaxis_title=c['chart_y'],
            height=400,
            margin=dict(l=0, r=0, t=20, b=0),
            hovermode='x unified',
        )
        st.plotly_chart(fig_curve, use_container_width=True)

    st.divider()

    # --- Row 4: Execution Ledger ---
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader(c['top_groups_title'])
        top_ad_groups = (
            df_opt.groupby('ad_group_name', as_index=False)['profit_lift']
            .sum()
            .nlargest(10, 'profit_lift')
        )

        # FIX: Overwrite the inherited pandas column name using the `labels` dictionary
        fig_bar = px.bar(
            top_ad_groups,
            x='profit_lift',
            y='ad_group_name',
            orientation='h',
            color='profit_lift',
            color_continuous_scale='Greens',
            labels={'profit_lift': c['col_lift'], 'ad_group_name': c['col_group']},
        )
        fig_bar.update_layout(
            xaxis_title=c['bar_x'],
            yaxis_title='',
            height=400,
            yaxis={'categoryorder': 'total ascending'},
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.subheader(c['ledger_title'])
        # output_cols = ['ad_group_name', 'targeting', 'beta_smoothed', 'current_cpc', 'optimized_cpc', 'cpc_delta', 'profit_lift']
        output_cols = [
            'ad_group_name',
            'targeting',
            'current_cpc',
            'optimized_cpc',
            'cpc_delta',
            'profit_lift',
        ]
        actionable_df = df_opt[output_cols].copy()

        st.dataframe(
            actionable_df.sort_values(by='profit_lift', ascending=False),
            column_config={
                'ad_group_name': c['col_group'],
                'targeting': c['col_target'],
                # "beta_smoothed": st.column_config.NumberColumn(c['col_beta'], format="%.2f"),
                'current_cpc': st.column_config.NumberColumn(
                    c['col_curr_cpc'], format=f'{CURRENCY}%.2f'
                ),
                'optimized_cpc': st.column_config.NumberColumn(
                    c['col_opt_cpc'], format=f'{CURRENCY}%.2f'
                ),
                'cpc_delta': st.column_config.NumberColumn(
                    c['col_delta'], format=f'{CURRENCY}%.2f'
                ),
                'profit_lift': st.column_config.NumberColumn(
                    c['col_lift'], format=f'{CURRENCY}%.2f'
                ),
            },
            use_container_width=True,
            hide_index=True,
            height=400,
        )
