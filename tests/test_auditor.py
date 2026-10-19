import numpy as np
import pandas as pd
import pytest
from conftest import make_clean_df, make_row

from backend.auditor.amazon_ppc_auditor import AmazonPPCAuditor

CHRONIC = '⏳ 长期不转化 (Chronic Non-Converter)'
HIGH_VELOCITY = '🚨 极速消耗 (High Velocity Spend)'
STRATEGIC_HOLD = '战略保留 (Strategic Hold)'


def actions_by_term(df):
    return dict(zip(df['customer_search_term'], df['audit_action'], strict=True))


# ---------------------------------------------------------------------------
# Initialization / maturity window
# ---------------------------------------------------------------------------
class TestInit:
    def test_rows_inside_attribution_lag_are_excluded(self):
        df = make_clean_df([make_row('mature'), make_row('fresh', start='2026-08-28')])

        auditor = AmazonPPCAuditor(df)

        assert set(auditor.df_mature['customer_search_term']) == {'mature'}
        # cutoff (08-31 minus 7 days) minus the earliest mature start date
        assert auditor.observation_days == 23

    def test_lag_days_zero_keeps_every_row(self):
        df = make_clean_df([make_row('mature'), make_row('fresh', start='2026-08-28')])

        auditor = AmazonPPCAuditor(df, lag_days=0)

        assert len(auditor.df_mature) == 3

    def test_micro_aggregation_uses_five_dimensional_key(self):
        df = make_clean_df(
            [
                make_row('t', clicks=3, spend=1.0, start='2026-08-01'),
                make_row('t', clicks=4, spend=2.0, start='2026-08-02'),
                make_row('t', ad_group='AG 2', clicks=5, spend=3.0),
            ]
        )

        micro = AmazonPPCAuditor(df).df_micro

        same_key = micro[
            (micro['customer_search_term'] == 't') & (micro['ad_group_name'] == 'AG 1')
        ]
        assert len(same_key) == 1
        assert same_key['clicks'].item() == 7
        assert same_key['spend'].item() == pytest.approx(3.0)
        # Mean age: (30 + 29) / 2 days relative to the report's max end date
        assert same_key['ad_duration_day'].item() == pytest.approx(29.5)

    def test_observation_days_is_at_least_one(self):
        df = make_clean_df([make_row(start='2026-08-24')])

        assert AmazonPPCAuditor(df).observation_days == 1

    @pytest.mark.parametrize(
        'df',
        [
            pd.DataFrame(),
            pd.DataFrame({'spend': [1.0]}),
            # Everything is still inside the attribution window
            make_clean_df([make_row(start='2026-08-30')]),
        ],
        ids=['empty', 'no-end-date', 'all-immature'],
    )
    def test_degenerate_inputs_return_safe_defaults(self, df):
        auditor = AmazonPPCAuditor(df)

        assert auditor.df_mature.empty
        assert auditor.extract_zero_sale_terms(global_margin_float=0.3).empty
        assert auditor.extract_top_performing_terms().empty
        assert auditor.evaluate_campaign_breakeven_health()['total_capital_lost'] == 0.0
        assert auditor.detect_match_type_cannibalization()['total_cannibalized_spend'] == 0.0


# ---------------------------------------------------------------------------
# Zero-sale bleeders
# ---------------------------------------------------------------------------
class TestExtractZeroSaleTerms:
    def test_flags_slow_and_fast_bleeders(self, sample_report):
        result = AmazonPPCAuditor(sample_report).extract_zero_sale_terms(global_margin_float=0.3)

        assert actions_by_term(result) == {
            'chronic term': CHRONIC,
            'fast term': HIGH_VELOCITY,
        }

    def test_dynamic_click_threshold_follows_campaign_cvr(self, sample_report):
        result = AmazonPPCAuditor(sample_report).extract_zero_sale_terms(global_margin_float=0.3)

        chronic = result.set_index('customer_search_term').loc['chronic term']
        # Camp A CVR = 5 / 160 -> ceil(32 * 1.5)
        assert chronic['dynamic_click_threshold'] == 48
        # Break-even CPA = AOV (50) * margin (0.3); flagged at 2x
        assert chronic['catastrophic_limit'] == pytest.approx(30.0)

    def test_campaign_without_orders_falls_back_to_global_aov(self, sample_report):
        result = AmazonPPCAuditor(sample_report).extract_zero_sale_terms(global_margin_float=0.3)

        fast = result.set_index('customer_search_term').loc['fast term']
        global_aov = 400.0 / 9  # all mature sales / all mature orders
        assert fast['catastrophic_limit'] == pytest.approx(global_aov * 0.3 * 2)

    def test_click_floor_applies_to_high_cvr_campaigns(self):
        df = make_clean_df(
            [
                make_row('converter', clicks=10, spend=2.0, orders=5, sales=500.0),
                make_row('zero sale', clicks=5, spend=1.0),
            ]
        )

        result = AmazonPPCAuditor(df).extract_zero_sale_terms(
            global_margin_float=0.3, absolute_click_floor=5
        )

        # CVR 5/15 would give ceil(3 * 1.5) = 5; the floor keeps it at 5
        assert result['dynamic_click_threshold'].tolist() == [5]

    def test_whitelist_is_case_and_whitespace_insensitive(self, sample_report):
        result = AmazonPPCAuditor(sample_report).extract_zero_sale_terms(
            global_margin_float=0.3, strategic_whitelist=['  CHRONIC Term ']
        )

        assert actions_by_term(result)['chronic term'] == STRATEGIC_HOLD

    def test_young_terms_are_not_chronic(self):
        df = make_clean_df(
            [
                make_row('winner', clicks=100, spend=10.0, orders=5, sales=250.0),
                # Same click profile as a chronic bleeder, but only 11 days old
                make_row('young term', clicks=60, spend=10.0, start='2026-08-20'),
            ]
        )

        result = AmazonPPCAuditor(df).extract_zero_sale_terms(global_margin_float=0.3)

        assert result.empty

    def test_no_bleeders_returns_frame_without_helper_columns(self):
        df = make_clean_df([make_row('winner', clicks=20, spend=5.0, orders=4, sales=100.0)])

        result = AmazonPPCAuditor(df).extract_zero_sale_terms(global_margin_float=0.3)

        assert result.empty
        assert 'dynamic_click_threshold' not in result.columns
        assert 'catastrophic_limit' not in result.columns

    def test_converting_terms_are_never_flagged(self, sample_report):
        result = AmazonPPCAuditor(sample_report).extract_zero_sale_terms(global_margin_float=0.3)

        assert (result['orders_7d'] == 0).all()


# ---------------------------------------------------------------------------
# Top performers
# ---------------------------------------------------------------------------
class TestExtractTopPerformingTerms:
    @pytest.fixture
    def auditor(self):
        return AmazonPPCAuditor(
            make_clean_df(
                [
                    make_row('exact winner', orders=5, sales=250.0, spend=40.0),
                    make_row(
                        'broad winner', match_type='broad ', orders=4, sales=400.0, spend=20.0
                    ),
                    make_row('other winner', match_type='OTHER', orders=3, sales=100.0, spend=10.0),
                    make_row('too few orders', orders=2, sales=100.0, spend=5.0),
                    make_row('above breakeven', orders=3, sales=100.0, spend=50.0),
                ]
            )
        )

    def test_filters_and_sorts_by_gross_profit(self, auditor):
        result = auditor.extract_top_performing_terms(break_even_acos=0.30, min_orders=3)

        assert result['customer_search_term'].tolist() == [
            'broad winner',
            'exact winner',
            'other winner',
        ]
        assert result['gross_profit'].tolist() == pytest.approx([100.0, 35.0, 20.0])
        assert result['acos'].tolist() == pytest.approx([0.05, 0.16, 0.10])

    def test_action_depends_on_match_type(self, auditor):
        result = auditor.extract_top_performing_terms()

        assert actions_by_term(result) == {
            'exact winner': '建议逐步提价/放宽预算 (Evaluate Bid/Budget Increase)',
            'broad winner': '建议提取至精准组测试 (Consider Exact Extraction)',
            'other winner': '建议关注并放大流量 (Consider Scaling Traffic)',
        }

    def test_min_orders_threshold(self, auditor):
        result = auditor.extract_top_performing_terms(min_orders=5)

        assert result['customer_search_term'].tolist() == ['exact winner']


# ---------------------------------------------------------------------------
# Portfolio fragility
# ---------------------------------------------------------------------------
class TestAssessPortfolioFragility:
    def test_concentration_ratio(self):
        df = make_clean_df(
            [
                make_row('a', spend=50.0),
                make_row('b', spend=30.0),
                make_row('c', spend=10.0),
                # Immature spend still counts: fragility uses the full report
                make_row('d', spend=10.0, start='2026-08-30'),
            ]
        )

        result = AmazonPPCAuditor(df).assess_portfolio_fragility(top_n=2, risk_threshold=0.4)

        assert result['concentration_ratio'] == pytest.approx(0.8)
        assert result['top_n_spend'] == pytest.approx(80.0)
        assert result['total_spend'] == pytest.approx(100.0)
        assert result['is_fragile'] is True
        assert result['top_terms_df']['customer_search_term'].tolist() == ['a', 'b']

    def test_diversified_portfolio_is_not_fragile(self):
        df = make_clean_df([make_row(f't{i}', spend=10.0) for i in range(10)])

        result = AmazonPPCAuditor(df).assess_portfolio_fragility(top_n=2, risk_threshold=0.4)

        assert result['concentration_ratio'] == pytest.approx(0.2)
        assert result['is_fragile'] is False

    def test_zero_spend(self):
        df = make_clean_df([make_row(spend=0.0)])

        result = AmazonPPCAuditor(df).assess_portfolio_fragility()

        assert result == {'concentration_ratio': 0.0, 'is_fragile': False}


# ---------------------------------------------------------------------------
# Campaign break-even health
# ---------------------------------------------------------------------------
class TestEvaluateCampaignBreakevenHealth:
    @pytest.fixture
    def result(self):
        df = make_clean_df(
            [
                make_row(campaign='Zero', spend=50.0, sales=0.0),
                make_row(campaign='Deflate', spend=70.0, sales=100.0, orders=2),
                make_row(campaign='Cap', spend=40.0, sales=100.0, orders=2),
                make_row(campaign='Healthy', spend=20.0, sales=100.0, orders=2),
                make_row(campaign='Tiny', spend=10.0, sales=0.0),
            ]
        )
        return AmazonPPCAuditor(df).evaluate_campaign_breakeven_health(
            break_even_acos=0.30, min_spend_threshold=20.0
        )

    def test_summary_metrics(self, result):
        assert result['total_capital_lost'] == pytest.approx(100.0)
        assert result['unprofitable_campaign_count'] == 3
        assert result['observation_window_days'] == 23

    def test_unprofitable_campaigns_sorted_by_capital_lost(self, result):
        df = result['unprofitable_campaigns_df']

        assert df['campaign_name'].tolist() == ['Zero', 'Deflate', 'Cap']
        assert df['capital_lost'].tolist() == pytest.approx([50.0, 40.0, 10.0])
        assert df['allowable_spend'].tolist() == pytest.approx([0.0, 30.0, 30.0])
        assert np.isinf(df.loc[0, 'realized_acos'])

    def test_consultative_actions(self, result):
        actions = result['unprofitable_campaigns_df'].set_index('campaign_name')[
            'consultative_action'
        ]

        assert actions['Zero'].startswith('需排查 (Investigate)')
        assert actions['Deflate'].startswith('建议降价 (Deflate)')
        assert actions['Cap'].startswith('建议限额 (Cap Budget)')

    def test_all_campaigns_below_min_spend(self):
        df = make_clean_df([make_row(campaign='Tiny', spend=10.0)])

        result = AmazonPPCAuditor(df).evaluate_campaign_breakeven_health(min_spend_threshold=20.0)

        assert result['total_capital_lost'] == 0.0
        assert result['unprofitable_campaigns_df'].empty


# ---------------------------------------------------------------------------
# Match-type cannibalization
# ---------------------------------------------------------------------------
class TestDetectMatchTypeCannibalization:
    def test_ranks_overlapping_terms_by_efficiency(self, sample_report):
        result = AmazonPPCAuditor(sample_report).detect_match_type_cannibalization()

        assert result['impacted_search_terms'] == 1
        assert result['total_cannibalized_spend'] == pytest.approx(20.0)

        overlap = result['overlap_df'].set_index('ad_group_name')
        assert overlap.loc['AG Exact', 'efficiency_rank'] == 1
        assert overlap.loc['AG Exact', 'status'] == '优势词 (Winner)'
        assert overlap.loc['AG Broad', 'efficiency_rank'] == 2
        assert overlap.loc['AG Broad', 'acos'] == pytest.approx(0.4)
        assert overlap.loc['AG Broad', 'cpc'] == pytest.approx(2.0)

    def test_low_spend_duplicates_are_ignored(self):
        df = make_clean_df(
            [
                make_row('shared', ad_group='AG 1', spend=10.0),
                make_row('shared', ad_group='AG 2', spend=3.0),
            ]
        )

        result = AmazonPPCAuditor(df).detect_match_type_cannibalization(min_spend_filter=5.0)

        assert result['total_cannibalized_spend'] == 0.0
        assert result['overlap_df'].empty

    def test_no_overlap(self):
        df = make_clean_df([make_row('a', spend=10.0), make_row('b', spend=10.0)])

        result = AmazonPPCAuditor(df).detect_match_type_cannibalization()

        assert result['total_cannibalized_spend'] == 0.0
