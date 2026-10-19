import pandas as pd
import pytest
import streamlit as st

# Every row in the shared builders is "mature" unless stated otherwise:
# the anchor row pushes the report's max end_date to ANCHOR_DATE, so with the
# default 7-day attribution lag the maturity cutoff is 2026-08-24.
MATURE_DATE = '2026-08-01'
ANCHOR_DATE = '2026-08-31'


class FakeSessionState(dict):
    """Dict that also supports attribute access, like st.session_state."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture(autouse=True)
def session_state(monkeypatch):
    """Isolate each test from Streamlit's global session state and secrets."""
    state = FakeSessionState()
    monkeypatch.setattr(st, 'session_state', state)
    monkeypatch.setattr(st, 'secrets', {})
    return state


def make_row(
    term='term',
    campaign='Camp A',
    ad_group='AG 1',
    match_type='EXACT',
    targeting='kw',
    impressions=1000,
    clicks=10,
    spend=5.0,
    orders=0,
    sales=0.0,
    start=MATURE_DATE,
    end=None,
):
    """One normalized (post-AmazonSPSchema) search term report row."""
    return {
        'start_date': pd.Timestamp(start),
        'end_date': pd.Timestamp(end or start),
        'campaign_name': campaign,
        'ad_group_name': ad_group,
        'match_type': match_type,
        'targeting': targeting,
        'customer_search_term': term,
        'impressions': impressions,
        'clicks': clicks,
        'spend': spend,
        'orders_7d': orders,
        'total_sales_7d': sales,
    }


def make_clean_df(rows, anchor=True):
    """Builds a normalized report; the zero-spend anchor row fixes the max date."""
    rows = list(rows)
    if anchor:
        rows.append(
            make_row(
                term='anchor term',
                campaign='Anchor',
                impressions=0,
                clicks=0,
                spend=0.0,
                start=ANCHOR_DATE,
            )
        )
    return pd.DataFrame(rows)


@pytest.fixture
def raw_english_report():
    """A raw Seller Central export with English headers (pre-normalization)."""
    return pd.DataFrame(
        {
            'Start Date': ['2026-08-01', '2026-08-01', '2026-08-31'],
            'End Date': ['2026-08-01', '2026-08-01', '2026-08-31'],
            'Campaign Name': ['Camp A', 'Camp A', 'Camp B'],
            'Ad Group Name': ['AG 1', 'AG 2', 'AG 3'],
            'Targeting': ['kw', None, 'kw'],
            'Match Type': ['EXACT', 'BROAD', 'PHRASE'],
            'Customer Search Term': ['red shoes', 'blue shoes', 'green shoes'],
            'Impressions': [1000, 500, 200],
            'Clicks': [10, 'abc', 3],
            'Spend': [5.5, 2.0, None],
            '7 Day Total Orders (#)': [1, 0, 0],
            '7 Day Total Sales ': [30.0, 0.0, 0.0],
        }
    )


@pytest.fixture
def sample_report():
    """A small account that exercises every audit module at once."""
    return make_clean_df(
        [
            # Camp A: one converting term and one chronic non-converter
            make_row('winner exact', clicks=100, spend=40.0, orders=5, sales=250.0),
            make_row('chronic term', clicks=60, spend=20.0),
            # Camp B: no orders at all -> high-velocity spend against global AOV
            make_row('fast term', campaign='Camp B', clicks=4, spend=40.0),
            # Same term in two ad groups -> cannibalization
            make_row(
                'shared term',
                campaign='Camp C',
                ad_group='AG Exact',
                clicks=10,
                spend=10.0,
                orders=3,
                sales=100.0,
            ),
            make_row(
                'shared term',
                campaign='Camp C',
                ad_group='AG Broad',
                match_type='BROAD',
                clicks=10,
                spend=20.0,
                orders=1,
                sales=50.0,
            ),
        ]
    )
