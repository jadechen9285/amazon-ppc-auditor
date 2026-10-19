import pandas as pd
import pytest

from backend.schema import AmazonSPSchema, SchemaValidationError


def test_english_headers_resolve_to_internal_keys(raw_english_report):
    df = AmazonSPSchema.validate_and_normalize(raw_english_report)

    assert AmazonSPSchema.REQUIRED_INTERNAL_KEYS <= set(df.columns)


def test_chinese_headers_with_full_width_brackets_and_spaces():
    raw = pd.DataFrame(
        {
            '开始日期': ['2026-08-01'],
            '结束日期': ['2026-08-07'],
            '广告活动名称': ['活动A'],
            '广告组名称': ['组1'],
            '投放': ['关键词'],
            '匹配类型': ['EXACT'],
            '客户搜索词': ['红色鞋子'],
            '展示量': [100],
            '点击量': [5],
            '花费': [2.5],
            ' 7天总订单数（#） ': [1],
            '7天 总销售额': [20.0],
        }
    )

    df = AmazonSPSchema.validate_and_normalize(raw)

    assert AmazonSPSchema.REQUIRED_INTERNAL_KEYS <= set(df.columns)
    assert df.loc[0, 'orders_7d'] == 1
    assert df.loc[0, 'total_sales_7d'] == 20.0


def test_daily_report_without_end_date_reuses_start_date(raw_english_report):
    raw = raw_english_report.drop(columns=['Start Date', 'End Date'])
    raw.insert(0, 'Date', ['2026-08-01', '2026-08-02', '2026-08-03'])

    df = AmazonSPSchema.validate_and_normalize(raw)

    pd.testing.assert_series_equal(df['start_date'], df['end_date'], check_names=False)


def test_missing_required_column_raises_friendly_error(raw_english_report):
    raw = raw_english_report.drop(columns=['Clicks'])

    with pytest.raises(SchemaValidationError) as exc_info:
        AmazonSPSchema.validate_and_normalize(raw)

    message = str(exc_info.value)
    assert 'Missing required columns' in message
    # The label is drawn from an unordered alias set, so either language may appear
    assert '点击量' in message or 'clicks' in message


def test_type_enforcement(raw_english_report):
    df = AmazonSPSchema.validate_and_normalize(raw_english_report)

    # Non-numeric and missing values are coerced to zero
    assert df['clicks'].tolist() == [10, 0, 3]
    assert df['spend'].tolist() == [5.5, 2.0, 0.0]
    # Auto campaigns have no targeting expression
    assert df.loc[1, 'targeting'] == 'AUTO_TARGET'
    for col in AmazonSPSchema.DATETIME_COLS:
        assert pd.api.types.is_datetime64_any_dtype(df[col])


def test_unparseable_dates_become_nat(raw_english_report):
    raw = raw_english_report.copy()
    raw.loc[0, 'Start Date'] = 'not a date'

    df = AmazonSPSchema.validate_and_normalize(raw)

    assert pd.isna(df.loc[0, 'start_date'])


def test_input_dataframe_is_not_mutated(raw_english_report):
    original_columns = list(raw_english_report.columns)

    AmazonSPSchema.validate_and_normalize(raw_english_report)

    assert list(raw_english_report.columns) == original_columns


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('  Campaign Name ', 'campaignname'),
        ('7天总订单数（#）', '7天总订单数(#)'),
        (123, '123'),
    ],
)
def test_normalize_text(raw, expected):
    assert AmazonSPSchema._normalize_text(raw) == expected
