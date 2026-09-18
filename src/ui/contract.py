class UIContract:
    """
    Single Source of Truth for frontend and export column naming.
    Ensures 100% parity between Streamlit visual components and Excel exports.
    """

    # Base Transformation Matrix
    COLUMN_MAP = {
        'audit_action': '系统建议操作',
        'consultative_action': '系统建议 (Action)',
        'status': '胜败状态',
        'campaign_name': '广告活动',
        'ad_group_name': '广告组',
        'match_type': '匹配类型',
        'targeting': '投放目标',
        'customer_search_term': '客户搜索词',
        'clicks': '实际点击数',
        'dynamic_click_threshold': '无单止损点击数',
        # Unified Financial & Metric Terms
        'spend': '总花费',
        'total_spend': '总花费',
        'total_sales': '总销售额',
        'total_orders': '总订单量',
        'orders_7d': '订单量',
        'realized_acos': '实际 ACoS',
        'acos': '实际 ACoS',
        'allowable_spend': '保本花费上限',
        'capital_lost': '实际亏损金额',
        'gross_profit': '预估广告净赚',
    }

    # Define strict sets for programmatic formatting
    CURRENCY_COLS = {
        'spend',
        'total_spend',
        'total_sales',
        'allowable_spend',
        'capital_lost',
        'gross_profit',
    }
    PERCENTAGE_COLS = {'acos', 'realized_acos'}

    @classmethod
    def get_excel_map(cls) -> dict[str, str]:
        """
        Dynamically injects currency markers for flat Excel exports
        where native UI formatting is unavailable.
        """
        return {k: f'{v} ($)' if k in cls.CURRENCY_COLS else v for k, v in cls.COLUMN_MAP.items()}

    @classmethod
    def get_label(cls, key: str) -> str:
        """Safely retrieves a UI label, falling back to the raw key if missing."""
        return cls.COLUMN_MAP.get(key, key)
