import numpy as np
import pandas as pd


def build_realistic_seller_dataset(
    retail_df: pd.DataFrame, target_n_rows: int = 10058
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Synthesizes SKU-level baseline financials from Online Retail II data
    and generates mapped search-term ad performance records using snake_case.
    """
    np.random.seed(42)

    # -------------------------------------------------------------------------
    # STEP 1: SKU FINANCIAL PROFILING (Pre-Ad Baseline from Online Retail II)
    # -------------------------------------------------------------------------
    clean_retail = retail_df[(retail_df['Quantity'] > 0) & (retail_df['Price'] > 0)].copy()
    clean_retail['line_total'] = clean_retail['Quantity'] * clean_retail['Price']

    sku_summary = (
        clean_retail.groupby('StockCode')
        .agg(
            total_units=('Quantity', 'sum'),
            organic_revenue=('line_total', 'sum'),
            implied_price=('Price', 'mean'),
        )
        .reset_index()
    )

    # Filter low-volume SKUs
    sku_summary = sku_summary[sku_summary['total_units'] >= 10].copy()

    # Amazon Cost Structure: COGS (20-35%) + FBA Fees (18-25%) + Referral Fee (15%)
    cogs_rate = np.random.uniform(0.20, 0.35, size=len(sku_summary))
    fba_rate = np.random.uniform(0.18, 0.25, size=len(sku_summary))
    referral_rate = 0.15

    sku_summary['cogs_fba_rate'] = cogs_rate + fba_rate + referral_rate
    sku_summary['unit_cost'] = (sku_summary['implied_price'] * sku_summary['cogs_fba_rate']).round(
        2
    )
    sku_summary['pre_ad_profit'] = (
        sku_summary['organic_revenue'] * (1 - sku_summary['cogs_fba_rate'])
    ).round(2)

    # Latent ad responsiveness profile
    profiles = np.random.choice(
        ['Bleeder', 'Starved_Winner', 'Normal'], size=len(sku_summary), p=[0.25, 0.20, 0.55]
    )
    sku_summary['action_tag'] = profiles

    alphas = []
    for p in profiles:
        if p == 'Bleeder':
            alphas.append(np.random.uniform(10, 35))
        elif p == 'Starved_Winner':
            alphas.append(np.random.uniform(140, 250))
        else:
            alphas.append(np.random.uniform(45, 85))

    sku_summary['ad_alpha'] = np.round(alphas, 2)

    # -------------------------------------------------------------------------
    # STEP 2: SYNTHESIZE AD DATA LAYER
    # -------------------------------------------------------------------------
    sampled_skus = sku_summary.sample(n=target_n_rows, replace=True).reset_index(drop=True)
    dates = pd.date_range(start='2026-08-01', periods=30)
    sampled_dates = np.random.choice(dates, target_n_rows)

    ad_report = pd.DataFrame(
        {
            'month': [d.month for d in sampled_dates],
            'week': [d.isocalendar().week for d in sampled_dates],
            'date': [int(d.strftime('%Y%m%d')) for d in sampled_dates],
            'stock_code': sampled_skus['StockCode'],
            'portfolio_name': np.random.choice(
                ['Core Products', 'Seasonal Campaign', 'Clearance', 'Not assigned'], target_n_rows
            ),
            'currency': 'GBP',
            'campaign_name': sampled_skus['StockCode'].apply(lambda x: f'sp_{x}_manual'),
            'ad_group_name': 'exact_targeting',
            'targeting': 'manual',
            'match_type': np.random.choice(
                ['EXACT', 'PHRASE', 'BROAD'], target_n_rows, p=[0.5, 0.3, 0.2]
            ),
            'customer_search_term': sampled_skus['StockCode'].apply(
                lambda x: f'buy item {x} online'
            ),
        }
    )

    # Impressions & Clicks
    ad_report['impressions'] = np.random.lognormal(mean=4.0, sigma=1.2, size=target_n_rows).astype(
        int
    )
    ad_report['impressions'] = np.clip(ad_report['impressions'], 1, None)

    base_ctr = np.random.beta(a=2, b=40, size=target_n_rows)
    base_cvr = np.random.beta(a=2, b=25, size=target_n_rows)

    ad_report['clicks'] = np.random.binomial(n=ad_report['impressions'], p=base_ctr)
    ad_report['orders'] = np.random.binomial(n=ad_report['clicks'], p=base_cvr)
    ad_report['units'] = ad_report['orders'] + np.random.binomial(ad_report['orders'], 0.1)

    # Split units (Advertised SKU vs Halo Effect)
    ad_report['advertised_sku_units'] = np.random.binomial(n=ad_report['units'], p=0.85)
    ad_report['other_sku_units'] = ad_report['units'] - ad_report['advertised_sku_units']

    # Financials
    actual_cpc = np.random.lognormal(mean=np.log(0.45), sigma=0.25, size=target_n_rows)
    ad_report['ad_spend'] = (ad_report['clicks'] * actual_cpc).round(2)

    unit_prices = sampled_skus['implied_price'].values
    ad_report['total_revenue'] = (ad_report['units'] * unit_prices).round(2)
    ad_report['advertised_sku_sales'] = (ad_report['advertised_sku_units'] * unit_prices).round(2)
    ad_report['other_sku_sales'] = (ad_report['other_sku_units'] * unit_prices).round(2)

    # -------------------------------------------------------------------------
    # STEP 3: CALCULATE RATIOS (Zero-safe with .fillna(0.0))
    # -------------------------------------------------------------------------
    epsilon = 1e-8
    ad_report['ctr'] = (
        (ad_report['clicks'] / (ad_report['impressions'] + epsilon)).fillna(0.0).round(4)
    )
    ad_report['cpc'] = (
        (ad_report['ad_spend'] / (ad_report['clicks'] + epsilon)).fillna(0.0).round(2)
    )
    ad_report['cvr'] = (ad_report['orders'] / (ad_report['clicks'] + epsilon)).fillna(0.0).round(4)
    ad_report['acos'] = np.where(
        ad_report['total_revenue'] > 0,
        (ad_report['ad_spend'] / ad_report['total_revenue']),
        1,
    )
    ad_report['roas'] = (
        (ad_report['total_revenue'] / (ad_report['ad_spend'] + epsilon)).fillna(0.0).round(2)
    )

    return sku_summary, ad_report


def extract_financial_state(
    df: pd.DataFrame, group_cols: list[str], lag_days: int = 7, cvr_half_life: int = 30
) -> pd.DataFrame:
    """
    Calculates the financial state with Bayesian smoothing for low-traffic anomalies.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])

    # 1. Split Mature vs Full Data
    cutoff_date = df['date'].max() - pd.Timedelta(days=lag_days)
    is_mature = df['date'] <= cutoff_date

    mature_agg = {'col_7_day_total_sales': 'sum', 'col_7_day_total_orders': 'sum', 'clicks': 'sum'}
    df_mature = df[is_mature].groupby(group_cols, as_index=False).agg(mature_agg)
    df_mature = df_mature.rename(columns={'clicks': 'mature_clicks'})

    # 2. Calculate Global Priors (The "Gravity")
    # We use sum over sum to avoid average-of-averages skew
    total_mature_clicks = df_mature['mature_clicks'].sum()
    total_mature_sales = df_mature['col_7_day_total_sales'].sum()
    total_mature_orders = df_mature['col_7_day_total_orders'].sum()

    global_rpc = total_mature_sales / total_mature_clicks if total_mature_clicks > 0 else 0
    global_cvr = total_mature_orders / total_mature_clicks if total_mature_clicks > 0 else 0

    # 3. Calculate Local Naive Metrics
    df_mature['naive_rpc'] = np.where(
        df_mature['mature_clicks'] > 0,
        df_mature['col_7_day_total_sales'] / df_mature['mature_clicks'],
        0,
    )
    df_mature['naive_cvr'] = np.where(
        df_mature['mature_clicks'] > 0,
        df_mature['col_7_day_total_orders'] / df_mature['mature_clicks'],
        0,
    )

    # 4. Apply Bayesian Smoothing
    df_mature['confidence_weight'] = df_mature['mature_clicks'] / (
        df_mature['mature_clicks'] + cvr_half_life
    )

    df_mature['true_rpc'] = (df_mature['confidence_weight'] * df_mature['naive_rpc']) + (
        (1 - df_mature['confidence_weight']) * global_rpc
    )

    df_mature['true_cvr'] = (df_mature['confidence_weight'] * df_mature['naive_cvr']) + (
        (1 - df_mature['confidence_weight']) * global_cvr
    )

    # 5. Full Data for Traffic & Costs
    full_agg = {'spend': 'sum', 'clicks': 'sum', 'impressions': 'sum'}
    df_full = df.groupby(group_cols, as_index=False).agg(full_agg)
    df_full['current_cpc'] = np.where(
        df_full['clicks'] > 0, df_full['spend'] / df_full['clicks'], 0
    )

    # 6. Assemble
    df_financials = pd.merge(df_full, df_mature, on=group_cols, how='left')

    # Fill brand new targets with the global prior
    df_financials['true_rpc'] = df_financials['true_rpc'].fillna(global_rpc)
    df_financials['true_cvr'] = df_financials['true_cvr'].fillna(global_cvr)

    return df_financials


def extract_price_elasticity(df_clean, df_financials, group_cols, prior=0.5, half_life=50):
    ## -- extract price elasticity
    df = df_clean.copy()
    df = df.sort_values(by=group_cols + ['date'])

    # 1. Calculate Local Beta via log differences
    df['prev_cpc'] = df.groupby(group_cols)['cost_per_click_cpc'].shift(1)
    df['prev_clicks'] = df.groupby(group_cols)['clicks'].shift(1)

    with np.errstate(divide='ignore', invalid='ignore'):
        delta_log_clicks = np.log(df['clicks']) - np.log(df['prev_clicks'])
        delta_log_cpc = np.log(df['cost_per_click_cpc']) - np.log(df['prev_cpc'])
        df['beta_local'] = np.where(delta_log_cpc != 0, delta_log_clicks / delta_log_cpc, np.nan)

    df['beta_local'] = df['beta_local'].clip(lower=0.01, upper=1.0)

    # 2. Extract median beta per keyword
    df_beta = (
        df.dropna(subset=['beta_local']).groupby(group_cols)['beta_local'].median().reset_index()
    )

    # 3. Apply Bayesian Smoothing
    # We need total clicks from the financial module to calculate weight
    df_beta = pd.merge(df_financials[group_cols + ['clicks']], df_beta, on=group_cols, how='left')

    df_beta['beta_local'] = df_beta['beta_local'].fillna(prior)
    df_beta['beta_weight'] = df_beta['clicks'] / (df_beta['clicks'] + half_life)
    df_beta['beta_smoothed'] = (df_beta['beta_weight'] * df_beta['beta_local']) + (
        (1 - df_beta['beta_weight']) * prior
    )

    return df_beta[group_cols + ['beta_smoothed', 'beta_local']]
