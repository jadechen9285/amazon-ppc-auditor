import os
import sys

# This adds the parent directory (or project root) to Python's path
# Adjust the '../' if your notebook is deeper in the folder tree
sys.path.insert(0, os.path.abspath('../'))

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.optimize import minimize

load_dotenv()  # Load environment variables from a .env file if present
env = os.environ
syntheticdata_path = env.get('SYNTHETIC_DATA_PATH')
real_data_path = env.get('REAL_DATA_PATH')

real_filename = 'Bliss-IT-广告投放数据_4月1.xlsx'
filename = 'online_retail_II.xlsx'


df = pd.read_excel(os.path.join(syntheticdata_path, filename), sheet_name='Year 2009-2010')
df_real = pd.read_excel(os.path.join(real_data_path, real_filename))


## -- Data Preproc
df_clean = df_real.copy()

df_clean.columns = (
    df_clean.columns.str.lower()
    .str.replace(
        r'[^\w\s]', '', regex=True
    )  # Remove punctuation/symbols (keeps letters, numbers, underscores, spaces)
    .str.strip()
    .str.replace(r'\s+', '_', regex=True)  # Replace spaces (and multiple spaces) with underscores
    .str.replace(r'^(\d)', r'col_\1', regex=True)  # Prepend 'col_' if it starts with a number
)

##
df_clean = df_clean[df_clean['clicks'] > 0]

# 3. Fill missing financial metrics with 0 where appropriate
fill_zero_cols = [
    'spend',
    'col_7_day_total_sales',
    'col_7_day_total_orders',
    'col_7_day_total_units',
    'col_7_day_advertised_sku_sales',
    'col_7_day_other_sku_sales',
    'impressions',
]
for col in fill_zero_cols:
    if col in df_clean.columns:
        df_clean[col] = df_clean[col].fillna(0)

## re-calculate CPC to double check
df_clean['cost_per_click_cpc'] = np.where(
    df_clean['clicks'] > 0, df_clean['spend'] / df_clean['clicks'], df_clean['cost_per_click_cpc']
)

# 5. Aggregate to the Targeting (Keyword/ASIN) Level
# This combines historical performance across different dates into a single optimization entity per keyword
agg_dict = {
    'impressions': 'sum',
    'clicks': 'sum',
    'spend': 'sum',
    'col_7_day_total_sales': 'sum',
    'col_7_day_total_orders': 'sum',
    'col_7_day_advertised_sku_sales': 'sum',
}

# Keep campaign and ad group names if they exist
group_cols = ['campaign_name', 'ad_group_name', 'targeting', 'match_type']
existing_group_cols = [c for c in group_cols if c in df_clean.columns]

# Assumption: A 'date' column exists to track period-over-period changes
if 'date' in df_clean.columns:
    df_clean = df_clean.sort_values(by=existing_group_cols + ['date'])
else:
    # If using a pre-aggregated dataset without dates, we must gracefully bypass
    # the time-series calculation and rely on the global prior later.
    pass

if 'date' in df_clean.columns:
    # Shift metrics by 1 row within each exact targeting group to get t-1
    df_clean['prev_cpc'] = df_clean.groupby(existing_group_cols)['cost_per_click_cpc'].shift(1)
    df_clean['prev_clicks'] = df_clean.groupby(existing_group_cols)['clicks'].shift(1)

    # Calculate Logarithmic Differences
    # Suppress divide-by-zero or invalid log warnings using numpy
    with np.errstate(divide='ignore', invalid='ignore'):
        delta_log_clicks = np.log(df_clean['clicks']) - np.log(df_clean['prev_clicks'])
        delta_log_cpc = np.log(df_clean['cost_per_click_cpc']) - np.log(df_clean['prev_cpc'])

        # Calculate local Beta. If delta_log_cpc is 0 (bid didn't change), results in NaN
        df_clean['beta_local'] = np.where(
            delta_log_cpc != 0, delta_log_clicks / delta_log_cpc, np.nan
        )

    # Clip Beta to enforce the Law of Diminishing Returns (0.01 to 1.0)
    # Negative betas (higher price = lower clicks) are usually data artifacts or seasonality noise
    df_clean['beta_local'] = df_clean['beta_local'].clip(lower=0.01, upper=1.0)

    # Extract the median valid beta for each ad target
    beta_priors = (
        df_clean.dropna(subset=['beta_local'])
        .groupby(existing_group_cols)['beta_local']
        .median()
        .reset_index()
    )
else:
    # Create empty dataframe if no temporal data exists
    beta_priors = pd.DataFrame(columns=existing_group_cols + ['beta_local'])

df_agg = df_clean.groupby(existing_group_cols, as_index=False).agg(agg_dict)

df_agg = df_agg.rename(
    columns={
        'col_7_day_total_sales': 'total_sales',
        'col_7_day_total_orders': 'total_orders',
        'col_7_day_advertised_sku_sales': 'total_advertised_sku_sales',
    }
)

# ---------------------------------------------------------
# NEW BLOCK: Apply Bayesian Smoothing to Beta
# ---------------------------------------------------------
# Merge the empirical betas back into the aggregated dataframe
df_agg = pd.merge(df_agg, beta_priors, on=existing_group_cols, how='left')

GLOBAL_BETA_PRIOR = 0.5
CONFIDENCE_HALF_LIFE = 50  # Number of clicks needed to trust the local data exactly 50%

# Fill missing local betas with the global prior (handles Cold Start targets)
df_agg['beta_local'] = df_agg['beta_local'].fillna(GLOBAL_BETA_PRIOR)

# Calculate dynamic weight (w) based on traffic volume
df_agg['beta_weight'] = df_agg['clicks'] / (df_agg['clicks'] + CONFIDENCE_HALF_LIFE)

# Final Smoothed Beta Formula: w * local_beta + (1 - w) * global_beta
df_agg['beta_smoothed'] = (df_agg['beta_weight'] * df_agg['beta_local']) + (
    (1 - df_agg['beta_weight']) * GLOBAL_BETA_PRIOR
)

# 7. Compute foundational unit economics for the optimizer
df_agg['current_cpc'] = df_agg['spend'] / df_agg['clicks']
df_agg['rpc'] = df_agg['total_sales'] / df_agg['clicks']  # Revenue Per Click
df_agg['cvr'] = df_agg['total_orders'] / df_agg['clicks']
df_agg['assumed_margin'] = 0.30  # Standard gross margin assumption

# Filter out anomalies
df_agg = df_agg[df_agg['current_cpc'] > 0]
df_agg = df_agg.replace([np.inf, -np.inf], np.nan).dropna(subset=['current_cpc', 'rpc'])
#


## -- bid optimization engine
## inputs
# beta = 0.5
max_iter = 250


## --
current_cpcs = np.maximum(df_agg['current_cpc'].values, 0.01)  # Prevent division by zero
current_clicks = df_agg['clicks'].values
rpcs = df_agg['rpc'].values
margins = df_agg['assumed_margin'].values
betas = df_agg['beta_smoothed'].values
total_budget = df_agg['spend'].sum()


# 2. Define the Simulation Logic
def simulate_state(new_cpcs):
    """
    Calculates predicted traffic and financials based on proposed bids.
    Using a power curve to model ad-rank traffic ceilings.
    """
    cpc_ratio = new_cpcs / current_cpcs
    pred_clicks = current_clicks * np.power(cpc_ratio, betas)
    pred_spend = pred_clicks * new_cpcs
    pred_sales = pred_clicks * rpcs
    pred_profit = (pred_sales * margins) - pred_spend
    return pred_clicks, pred_spend, pred_profit


# 3. Objective & Constraints for the Solver
def objective(new_cpcs):
    # SLSQP minimizes, so we return negative profit to find the maximum
    _, _, pred_profit = simulate_state(new_cpcs)
    return -np.sum(pred_profit)


def budget_constraint(new_cpcs):
    # Must return a non-negative value to satisfy 'ineq' (Total Budget - New Spend >= 0)
    _, pred_spend, _ = simulate_state(new_cpcs)
    return total_budget - np.sum(pred_spend)


# 4. Bounding the Search Space (Amazon minimum bid is usually $0.02)
bounds = [(0.02, 15.0) for _ in range(len(df_agg))]


# 5. Execution
print('Initializing SLSQP solver...')
result = minimize(
    objective,
    x0=current_cpcs,  # Start searching from the current state
    method='SLSQP',
    bounds=bounds,
    constraints=[{'type': 'ineq', 'fun': budget_constraint}],
    options={'maxiter': max_iter, 'ftol': 1e-6},
)

if not result.success:
    print(f'Warning: Sub-optimal convergence. {result.message}')


# 6. Map results and calculate deltas
df_result = df_agg.copy()
df_result['optimized_cpc'] = result.x
df_result['cpc_delta'] = df_result['optimized_cpc'] - df_result['current_cpc']

_, df_result['current_spend'], df_result['current_profit'] = simulate_state(current_cpcs)
df_result['pred_clicks'], df_result['pred_spend'], df_result['pred_profit'] = simulate_state(
    result.x
)
df_result['profit_lift'] = df_result['pred_profit'] - df_result['current_profit']
