from ui.i18n import t


class UIContract:
    @staticmethod
    def get_label(column_key: str) -> str:
        """
        Routes the backend dataframe column keys through the i18n translation engine.
        Uses a 'col_' prefix to keep translation keys organized.
        """
        return t(f'col_{column_key}')

    @staticmethod
    def get_excel_map() -> dict:
        """
        Generates the dynamic renaming dictionary for the Pandas to_excel export,
        ensuring the downloaded file matches the user's selected language.
        """
        keys = [
            'audit_action',
            'bleeding_reason',
            'campaign_name',
            'ad_group_name',
            'match_type',
            'targeting',
            'customer_search_term',
            'clicks',
            'dynamic_click_threshold',
            'spend',
            'status',
            'total_spend',
            'total_sales',
            'total_orders',
            'realized_acos',
            'allowable_spend',
            'capital_lost',
            'orders_7d',
            'acos',
            'gross_profit',
            'consultative_action',
        ]
        return {k: t(f'col_{k}') for k in keys}
