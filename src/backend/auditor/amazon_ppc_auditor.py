from typing import Any, Dict, List  # noqa: UP035

import numpy as np
import pandas as pd


class AmazonPPCAuditor:
    """
    Unified diagnostic engine for Amazon PPC structural audits.
    Computes baseline mature data and aggregations once upon initialization
    to ensure O(N) performance across multiple downstream audit methods.
    """
    
    def __init__(self, df_clean: pd.DataFrame, lag_days: int = 7):
        self.df_clean = df_clean
        self.lag_days = lag_days
        
        # State placeholders
        self.df_mature = pd.DataFrame()
        self.df_micro = pd.DataFrame()
        self.observation_days = 0
        
        self._prepare_base_data()

    def _prepare_base_data(self):
        """Internal method to compute truncated and aggregated dataframes once."""
        if self.df_clean.empty or 'end_date' not in self.df_clean.columns:
            return

        datetime_col = ['start_date', 'end_date']
        for col in datetime_col:
            self.df_clean[col] = pd.to_datetime(self.df_clean[col], errors='coerce')

        max_date = self.df_clean['end_date'].max()
        cutoff_date = max_date - pd.Timedelta(days=self.lag_days)

        # 1. Compute Mature Data (Truncated)
        self.df_mature = self.df_clean[self.df_clean['end_date'] <= cutoff_date].copy()
        
        if self.df_mature.empty:
            return
            
        self.df_mature['ad_duration_day'] = (max_date - self.df_mature['start_date']).dt.days
        self.observation_days = max(1, (cutoff_date - self.df_mature['start_date'].min()).days)

        # 2. Compute Standard Micro-Aggregation
        group_ids = ['campaign_name', 'ad_group_name', 'customer_search_term']
        agg_func = {
            'impressions': 'sum',
            'clicks': 'sum',
            'spend': 'sum',
            'orders_7d': 'sum',
            'total_sales_7d': 'sum',
            'ad_duration_day': 'mean'
        }
        self.df_micro = self.df_mature.groupby(group_ids, as_index=False).agg(agg_func)

    def extract_zero_sale_terms(
        self, 
        click_threshold: int = 20, 
        ad_duration_day_threshold: int = 14, 
        strategic_whitelist: List[str] = None
    ) -> pd.DataFrame:
        if self.df_micro.empty:
            return pd.DataFrame()
            
        whitelist = [str(term).strip().lower() for term in (strategic_whitelist or [])]

        mask = (
            (self.df_micro['orders_7d'] == 0) & 
            (self.df_micro['clicks'] >= click_threshold) & 
            (self.df_micro['ad_duration_day'] >= ad_duration_day_threshold)
        )
        bleeding_df = self.df_micro[mask].copy()

        if bleeding_df.empty:
            return bleeding_df

        bleeding_df['clean_term'] = bleeding_df['customer_search_term'].str.strip().str.lower()
        bleeding_df['audit_action'] = np.where(
            bleeding_df['clean_term'].isin(whitelist),
            'Strategic (Hold)',
            'Negative Exact'
        )

        return (
            bleeding_df
            .sort_values(by=['audit_action', 'spend'], ascending=[True, False])
            .drop(columns=['clean_term'])
        )

    def extract_top_performing_terms(
        self, 
        break_even_acos: float = 0.30, 
        min_orders: int = 3
    ) -> pd.DataFrame:
        if self.df_micro.empty:
            return pd.DataFrame()

        winners_df = self.df_micro[self.df_micro['orders_7d'] >= min_orders].copy()
        
        if winners_df.empty:
            return winners_df

        winners_df['acos'] = np.where(
            winners_df['total_sales_7d'] > 0,
            winners_df['spend'] / winners_df['total_sales_7d'],
            np.inf
        )

        winners_df = winners_df[winners_df['acos'] < break_even_acos].copy()
        winners_df['gross_profit'] = (winners_df['total_sales_7d'] * break_even_acos) - winners_df['spend']
        winners_df['audit_action'] = 'Scale'

        return winners_df.sort_values(by='gross_profit', ascending=False)

    def assess_portfolio_fragility(
        self, 
        top_n: int = 10, 
        risk_threshold: float = 0.40
    ) -> Dict[str, Any]:
        if self.df_clean.empty or 'spend' not in self.df_clean.columns:
            return {"concentration_ratio": 0.0, "is_fragile": False}

        # Uses raw df_clean to capture total account spend regardless of maturity
        term_spend_df = self.df_clean.groupby('customer_search_term', as_index=False)['spend'].sum()
        term_spend_df = term_spend_df.sort_values(by='spend', ascending=False)
        
        total_spend = term_spend_df['spend'].sum()
        if total_spend == 0:
            return {"concentration_ratio": 0.0, "is_fragile": False}

        top_n_df = term_spend_df.head(top_n)
        top_n_spend = top_n_df['spend'].sum()
        concentration_ratio = top_n_spend / total_spend
        
        return {
            "concentration_ratio": concentration_ratio,
            "top_n_spend": top_n_spend,
            "total_spend": total_spend,
            "is_fragile": bool(concentration_ratio > risk_threshold),
            "top_terms_df": top_n_df
        }

    def evaluate_campaign_breakeven_health(
        self, 
        break_even_acos: float = 0.30, 
        min_spend_threshold: float = 20.0
    ) -> Dict[str, Any]:
        if self.df_mature.empty:
            return {"total_capital_lost": 0.0, "unprofitable_campaigns_df": pd.DataFrame()}

        campaign_metrics = self.df_mature.groupby('campaign_name', as_index=False).agg(
            total_spend=('spend', 'sum'),
            total_sales=('total_sales_7d', 'sum'),
            total_orders=('orders_7d', 'sum')
        )

        active = campaign_metrics[campaign_metrics['total_spend'] >= min_spend_threshold].copy()
        if active.empty:
            return {"total_capital_lost": 0.0, "unprofitable_campaigns_df": pd.DataFrame()}

        active['realized_acos'] = np.where(
            active['total_sales'] > 0,
            active['total_spend'] / active['total_sales'],
            np.inf
        )

        active['allowable_spend'] = active['total_sales'] * break_even_acos
        active['capital_lost'] = active['total_spend'] - active['allowable_spend']

        unprofitable = active[active['realized_acos'] > break_even_acos].sort_values(
            by='capital_lost', ascending=False
        ).reset_index(drop=True)

        unprofitable['capital_lost'] = unprofitable['capital_lost'].clip(lower=0.0)

        return {
            "total_capital_lost": float(unprofitable['capital_lost'].sum()),
            "unprofitable_campaign_count": len(unprofitable),
            "observation_window_days": self.observation_days,
            "unprofitable_campaigns_df": unprofitable
        }

    def detect_match_type_cannibalization(self, min_spend_filter: float = 5.0) -> Dict[str, Any]:
        if self.df_mature.empty:
            return {"total_cannibalized_spend": 0.0, "overlap_df": pd.DataFrame()}

        # Requires match_type, so we must run a specific group-by distinct from self.df_micro
        grouped = self.df_mature.groupby(
            ['customer_search_term', 'campaign_name', 'ad_group_name', 'match_type'], 
            as_index=False
        ).agg(
            spend=('spend', 'sum'),
            sales=('total_sales_7d', 'sum'),
            clicks=('clicks', 'sum')
        )

        grouped = grouped[grouped['spend'] >= min_spend_filter].copy()
        if grouped.empty:
            return {"total_cannibalized_spend": 0.0, "overlap_df": pd.DataFrame()}

        term_counts = grouped['customer_search_term'].value_counts()
        overlapping_terms = term_counts[term_counts > 1].index
        
        if len(overlapping_terms) == 0:
            return {"total_cannibalized_spend": 0.0, "overlap_df": pd.DataFrame()}

        overlap_df = grouped[grouped['customer_search_term'].isin(overlapping_terms)].copy()
        overlap_df['acos'] = np.where(overlap_df['sales'] > 0, overlap_df['spend'] / overlap_df['sales'], np.inf)
        overlap_df['cpc'] = np.where(overlap_df['clicks'] > 0, overlap_df['spend'] / overlap_df['clicks'], 0.0)

        overlap_df = overlap_df.sort_values(
            by=['customer_search_term', 'acos', 'cpc'], 
            ascending=[True, True, True]
        )
        
        overlap_df['efficiency_rank'] = overlap_df.groupby('customer_search_term').cumcount() + 1
        losers_df = overlap_df[overlap_df['efficiency_rank'] > 1]

        overlap_df['status'] = np.where(overlap_df['efficiency_rank'] == 1, 'Winner', 'Loser (Pause)')

        return {
            "total_cannibalized_spend": float(losers_df['spend'].sum()),
            "impacted_search_terms": len(overlapping_terms),
            "overlap_df": overlap_df
        }
    