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
        group_ids = ['campaign_name', 'ad_group_name', 'match_type', 'customer_search_term']
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
            click_multiplier: float = 1.5, 
            absolute_click_floor: int = 5,
            ad_duration_day_threshold: int = 14, 
            strategic_whitelist: List[str] = None
        ) -> pd.DataFrame:
            
        """
        Filters for zero-sale search terms utilizing a dynamic expected-value click threshold 
        based on the parent campaign's historical conversion rate.
        """
        if self.df_micro.empty or self.df_mature.empty:
            return pd.DataFrame()
            
        # 1. Establish the statistical baseline from mature data
        camp_stats = self.df_mature.groupby('campaign_name').agg(
            total_clicks=('clicks', 'sum'), 
            total_orders=('orders_7d', 'sum')
        )
        
        camp_stats['cvr'] = np.where(
            camp_stats['total_clicks'] > 0, 
            camp_stats['total_orders'] / camp_stats['total_clicks'], 
            0.05  # Fallback assumption for cold-start campaigns
        )

        # 2. Slice a working copy to avoid mutating the class state
        df_working = self.df_micro.copy()

        # 3. Map CVR and compute the dynamic threshold parameter
        mapped_cvr = df_working['campaign_name'].map(camp_stats['cvr']).fillna(0.05)
        
        df_working['dynamic_click_threshold'] = np.maximum(
            np.ceil((1.0 / mapped_cvr) * click_multiplier),
            absolute_click_floor
        )

        # 4. Clean the whitelist for robust matching
        whitelist = [str(term).strip().lower() for term in (strategic_whitelist or [])]
        df_working['clean_term'] = df_working['customer_search_term'].str.strip().str.lower()

        # 5. Apply the multi-condition mathematical mask
        mask = (
            (df_working['orders_7d'] == 0) & 
            (df_working['clicks'] >= df_working['dynamic_click_threshold']) & 
            (df_working['ad_duration_day'] >= ad_duration_day_threshold)
        )
        
        bleeding_df = df_working[mask].copy()

        if bleeding_df.empty:
            return bleeding_df.drop(columns=['clean_term', 'dynamic_click_threshold'], errors='ignore')

        # 6. Tag strategic keywords vs actionable bleeders
        bleeding_df['audit_action'] = np.where(
            bleeding_df['clean_term'].isin(whitelist),
            '战略保留 (Strategic Hold)',
            '精准否定 (Negative Exact)'
        )

        return (
            bleeding_df
            .sort_values(by=['audit_action', 'spend'], ascending=[True, False])
            .drop(columns=['clean_term']) # Keep dynamic_click_threshold for UI transparency
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
        
        # --- Context-Aware, Liability-Safe Tags ---
        # Normalize the match_type column for safe string comparison
        match_type_normalized = winners_df['match_type'].str.strip().str.upper()
        
        conditions = [
            match_type_normalized == 'EXACT',
            match_type_normalized.isin(['BROAD', 'PHRASE', 'AUTO']) # or simply the inverse
        ]
        
        choices = [
            '建议逐步提价/放宽预算 (Evaluate Bid/Budget Increase)',
            '建议提取至精准组测试 (Consider Exact Extraction)'
        ]
        
        # Default handles any edge cases like missing match types
        winners_df['audit_action'] = np.select(
            conditions, 
            choices, 
            default='建议关注并放大流量 (Consider Scaling Traffic)'
        )

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

        # --- Injecting Liability-Safe Recommendations ---
        conditions = [
            (active['total_sales'] == 0) & (active['total_spend'] >= min_spend_threshold),
            (active['realized_acos'] > (break_even_acos * 2.0)),
            (active['realized_acos'] > break_even_acos)
        ]
        
        choices = [
            "需排查 (Investigate): 零转化，建议审查搜索词报告注入否定词",
            "建议降价 (Deflate): ACoS 严重超标，考虑整体下调基础竞价 15-20%",
            "建议限额 (Cap Budget): 轻微亏损，考虑降低单日预算以提升流量效率"
        ]
        
        active['consultative_action'] = np.select(conditions, choices, default="健康 (Healthy)")
        
        # Filter for unprofitable bleeders
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
        grouped = self.df_micro.rename(columns={
            'total_sales_7d' :'sales',
        } )

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

        overlap_df['status'] = np.where(
            overlap_df['efficiency_rank'] == 1, 
            '优势词 (Winner)', 
            '劣势词，建议暂停 (Loser - Consider Pausing)'
        )

        return {
            "total_cannibalized_spend": float(losers_df['spend'].sum()),
            "impacted_search_terms": len(overlapping_terms),
            "overlap_df": overlap_df
        }
    