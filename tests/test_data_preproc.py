import numpy as np
import pandas as pd
import pytest

from backend.data_prepoc import (
    build_realistic_seller_dataset,
    extract_financial_state,
    extract_price_elasticity,
)

GROUP_COLS = ['targeting']


class TestExtractFinancialState:
    @pytest.fixture
    def result(self):
        df = pd.DataFrame(
            {
                'date': ['2026-08-01', '2026-08-01', '2026-08-31', '2026-08-31'],
                'targeting': ['A', 'B', 'A', 'C'],
                'clicks': [30, 10, 10, 5],
                'spend': [15.0, 5.0, 5.0, 10.0],
                'impressions': [300, 100, 100, 50],
                'col_7_day_total_sales': [300.0, 0.0, 999.0, 999.0],
                'col_7_day_total_orders': [6, 0, 9, 9],
            }
        )
        return extract_financial_state(df, GROUP_COLS, lag_days=7, cvr_half_life=30).set_index(
            'targeting'
        )

    def test_bayesian_smoothing_toward_global_prior(self, result):
        # Global priors from mature data: RPC = 300 / 40, CVR = 6 / 40
        # A: weight = 30 / (30 + 30) = 0.5
        assert result.loc['A', 'confidence_weight'] == pytest.approx(0.5)
        assert result.loc['A', 'true_rpc'] == pytest.approx(0.5 * 10.0 + 0.5 * 7.5)
        assert result.loc['A', 'true_cvr'] == pytest.approx(0.5 * 0.2 + 0.5 * 0.15)

    def test_immature_sales_are_ignored(self, result):
        # The 999.0 sales on 08-31 sit inside the lag window
        assert result.loc['A', 'col_7_day_total_sales'] == pytest.approx(300.0)

    def test_new_target_inherits_global_prior(self, result):
        assert result.loc['C', 'true_rpc'] == pytest.approx(7.5)
        assert result.loc['C', 'true_cvr'] == pytest.approx(0.15)

    def test_costs_use_full_window(self, result):
        assert result.loc['A', 'clicks'] == 40
        assert result.loc['A', 'current_cpc'] == pytest.approx(0.5)
        assert result.loc['C', 'current_cpc'] == pytest.approx(2.0)


def test_extract_price_elasticity_clips_and_smooths():
    df_clean = pd.DataFrame(
        {
            'date': pd.to_datetime(['2026-08-01', '2026-08-02', '2026-08-03'] * 3),
            'targeting': ['K'] * 3 + ['M'] * 3 + ['N'] * 3,
            # K: clicks scale faster than CPC (beta 2 -> clipped to 1)
            # M: clicks fall as CPC rises (beta -1 -> clipped to 0.01)
            # N: CPC never changes, so no beta can be observed
            'cost_per_click_cpc': [1.0, 2.0, 2.0, 1.0, 2.0, 2.0, 1.0, 1.0, 1.0],
            'clicks': [100, 400, 300, 100, 50, 60, 10, 20, 30],
        }
    )
    df_financials = pd.DataFrame({'targeting': ['K', 'M', 'N'], 'clicks': [50, 50, 0]})

    result = extract_price_elasticity(
        df_clean, df_financials, GROUP_COLS, prior=0.5, half_life=50
    ).set_index('targeting')

    assert result['beta_local'].tolist() == pytest.approx([1.0, 0.01, 0.5])
    # weight = clicks / (clicks + half_life)
    assert result.loc['K', 'beta_smoothed'] == pytest.approx(0.75)
    assert result.loc['M', 'beta_smoothed'] == pytest.approx(0.255)
    assert result.loc['N', 'beta_smoothed'] == pytest.approx(0.5)


class TestBuildRealisticSellerDataset:
    @pytest.fixture
    def retail_df(self):
        return pd.DataFrame(
            {
                'StockCode': ['A', 'A', 'B', 'C', 'D', 'E'],
                'Quantity': [8, 4, 20, 15, 3, -50],
                'Price': [2.0, 2.0, 5.0, 0.0, 1.0, 9.0],
            }
        )

    def test_low_volume_and_invalid_rows_are_filtered(self, retail_df):
        sku_summary, _ = build_realistic_seller_dataset(retail_df, target_n_rows=50)

        # C has zero price, D has < 10 units, E only has returns
        assert set(sku_summary['StockCode']) == {'A', 'B'}
        a = sku_summary.set_index('StockCode').loc['A']
        assert a['total_units'] == 12
        assert a['organic_revenue'] == pytest.approx(24.0)

    def test_ad_report_is_deterministic(self, retail_df):
        first = build_realistic_seller_dataset(retail_df, target_n_rows=50)
        second = build_realistic_seller_dataset(retail_df, target_n_rows=50)

        pd.testing.assert_frame_equal(first[0], second[0])
        pd.testing.assert_frame_equal(first[1], second[1])

    def test_ad_report_funnel_is_consistent(self, retail_df):
        _, ad_report = build_realistic_seller_dataset(retail_df, target_n_rows=200)

        assert len(ad_report) == 200
        assert (ad_report['impressions'] >= 1).all()
        assert (ad_report['clicks'] <= ad_report['impressions']).all()
        assert (ad_report['orders'] <= ad_report['clicks']).all()
        assert (ad_report['units'] >= ad_report['orders']).all()
        assert (
            ad_report['advertised_sku_units'] + ad_report['other_sku_units'] == ad_report['units']
        ).all()
        assert set(ad_report['match_type']) <= {'EXACT', 'PHRASE', 'BROAD'}
        assert np.isfinite(ad_report[['ctr', 'cpc', 'cvr', 'acos', 'roas']].to_numpy()).all()
