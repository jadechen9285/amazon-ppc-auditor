import pandas as pd


class SchemaValidationError(Exception):
    """Custom exception to trigger friendly UI error messages."""

    pass


class AmazonSPSchema:
    """
    Robust Multi-Lingual Gatekeeper.
    Absorbs both legacy (2021) and modern (2024-2026) Amazon SP report schemas.
    """

    # The Global Resolution Set
    ALIAS_MAP = {
        # 🚀 FIX: Added '日期' to absorb Chinese Daily reports
        'start_date': {'开始日期', 'start date', 'date', '日期'},
        'end_date': {'结束日期', 'end date'},
        'campaign_name': {'广告活动名称', 'campaign name'},
        # 🚀 FIX: Added '广告组名称' (Ad Group). '广告组合' is actually Portfolio in Amazon PPC.
        'ad_group_name': {'广告组名称', '广告组合名称', 'ad group name'},
        'targeting': {'投放', 'targeting'},
        'match_type': {'匹配类型', 'match type'},
        'customer_search_term': {'客户搜索词', 'customer search term'},
        'impressions': {'展示量', 'impressions'},
        'clicks': {'点击量', 'clicks'},
        'spend': {'花费', 'spend'},
        'orders_7d': {
            '7天总订单数(#)',
            '7 day total orders (#)',
            '7 day total orders',
            '7天总订单数',
        },
        'total_sales_7d': {
            '7天总销售额',
            '7 day total sales ()',
            '7 day total sales',
            '七天总销售额',
        },
    }

    # Strict Internal Keys Required by AmazonPPCAuditor
    REQUIRED_INTERNAL_KEYS = {
        'start_date',
        'end_date',
        'campaign_name',
        'ad_group_name',
        'targeting',
        'match_type',
        'customer_search_term',
        'impressions',
        'clicks',
        'spend',
        'orders_7d',
        'total_sales_7d',
    }

    DATETIME_COLS = ['start_date', 'end_date']

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Strips whitespace, lowers case, and standardizes brackets."""
        if not isinstance(text, str):
            return str(text)
        return text.strip().replace(' ', '').replace('（', '(').replace('）', ')').lower()

    @classmethod
    def _build_resolution_matrix(cls) -> dict[str, str]:
        """Flattens the ALIAS_MAP into a 1:1 lookup dictionary."""
        resolution_matrix = {}
        for core_key, aliases in cls.ALIAS_MAP.items():
            for alias in aliases:
                clean_alias = cls._normalize_text(alias)
                resolution_matrix[clean_alias] = core_key
        return resolution_matrix

    @classmethod
    def validate_and_normalize(cls, df: pd.DataFrame) -> pd.DataFrame:
        df_clean = df.copy()

        # 1. Normalize uploaded headers
        df_clean.columns = [cls._normalize_text(col) for col in df_clean.columns]

        # 2. Build and apply the Resolution Matrix
        resolution_matrix = cls._build_resolution_matrix()
        df_clean = df_clean.rename(columns=resolution_matrix)

        # --- THE LEGACY SCHEMA FIX ---
        # If the user uploaded a legacy/daily report with only 'Date' (start_date),
        # we dynamically duplicate it to 'end_date' so the backend math doesn't crash.
        if 'start_date' in df_clean.columns and 'end_date' not in df_clean.columns:
            df_clean['end_date'] = df_clean['start_date']

        # 3. Schema Validation
        uploaded_cols = set(df_clean.columns)
        missing_cols = cls.REQUIRED_INTERNAL_KEYS - uploaded_cols

        if missing_cols:
            # Map missing keys back to primary Chinese aliases for a friendly error
            error_labels = [list(cls.ALIAS_MAP[col])[0] for col in missing_cols]
            missing_str = ', '.join([f'「{label}」' for label in error_labels])
            raise SchemaValidationError(
                f'您的报表缺少核心列: {missing_str} (Missing required columns)'
            )

        # 4. Type Enforcement
        df_clean['impressions'] = pd.to_numeric(df_clean['impressions'], errors='coerce').fillna(0)
        df_clean['clicks'] = pd.to_numeric(df_clean['clicks'], errors='coerce').fillna(0)
        df_clean['spend'] = pd.to_numeric(df_clean['spend'], errors='coerce').fillna(0.0)
        df_clean['orders_7d'] = pd.to_numeric(df_clean['orders_7d'], errors='coerce').fillna(0)
        df_clean['total_sales_7d'] = pd.to_numeric(
            df_clean['total_sales_7d'], errors='coerce'
        ).fillna(0.0)

        # 5. Sanitize Auto Campaigns
        df_clean['targeting'] = df_clean['targeting'].fillna('AUTO_TARGET')

        # 6. Datetime enforcement
        for col in cls.DATETIME_COLS:
            df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

        return df_clean
