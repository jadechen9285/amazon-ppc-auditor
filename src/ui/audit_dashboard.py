import io

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from backend.telemetry import insert_telemetry_row
from ui.contract import UIContract
from ui.i18n import t


def render_audit_dashboard(auditor, global_margin: float):
    """Main entry point for rendering the audit UI."""
    st.title(t('dashboard_title'))
    st.caption(t('dashboard_caption'))

    # 1. Compute all results
    df_bleeders = auditor.extract_zero_sale_terms(global_margin_float=global_margin)
    cannibal_data = auditor.detect_match_type_cannibalization()
    fragility_data = auditor.assess_portfolio_fragility()
    breakeven_data = auditor.evaluate_campaign_breakeven_health(break_even_acos=global_margin)
    df_winners = auditor.extract_top_performing_terms(break_even_acos=global_margin)

    # 2. Render Hero Metrics Layer
    _render_hero_metrics(df_bleeders, cannibal_data, breakeven_data, fragility_data, global_margin)

    st.divider()

    # 3. Render Tabbed Views
    tab1, tab2, tab3 = st.tabs([t('tab_bleeders'), t('tab_loss'), t('tab_winners')])

    with tab1:
        _render_tab_bleeders(df_bleeders, cannibal_data)
    with tab2:
        _render_tab_structural_loss(breakeven_data, global_margin)
    with tab3:
        _render_tab_winners(df_winners, global_margin)

    # 4. Render Feedback Engine at the bottom of the page
    _render_feedback_section()


# -------------------------------------------------------------
# 🧩 MODULAR RENDER FUNCTIONS
# -------------------------------------------------------------


def _render_hero_metrics(df_bleeders, cannibal_data, breakeven_data, fragility_data, global_margin):
    total_waste = df_bleeders['spend'].sum() if not df_bleeders.empty else 0.0
    total_waste += cannibal_data.get('total_cannibalized_spend', 0.0)

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label=t('hero_waste_label'),
        value=f'${total_waste:,.2f}',
        delta=t('hero_waste_delta'),
        delta_color='inverse',
        help=t('hero_waste_help'),
    )

    col2.metric(
        label=t('hero_loss_label'),
        value=f'{breakeven_data.get("unprofitable_campaign_count", 0)}',
        delta=t('hero_loss_delta'),
        delta_color='inverse',
        help=t('hero_loss_help', margin=global_margin * 100),
    )

    is_fragile = fragility_data.get('is_fragile')
    risk_status = t('hero_risk_status_high') if is_fragile else t('hero_risk_status_ok')

    col3.metric(
        label=t('hero_risk_label'),
        value=f'{fragility_data.get("concentration_ratio", 0) * 100:.1f}%',
        delta=risk_status,
        delta_color='off',
        help=t('hero_risk_help'),
    )


def _render_tab_bleeders(df_bleeders, cannibal_data):
    st.subheader(t('tab1_subheader1'))

    with st.expander(t('tab1_expander_title')):
        st.markdown(t('tab1_expander_content'))

    st.write(t('tab1_advice'))

    if not df_bleeders.empty:
        df_bleeders_view = df_bleeders.copy()
        df_bleeders_view = df_bleeders_view.rename(columns={'audit_action': 'bleeding_reason'})

        st.dataframe(
            df_bleeders_view[
                [
                    'bleeding_reason',
                    'campaign_name',
                    'ad_group_name',
                    'match_type',
                    'targeting',
                    'customer_search_term',
                    'clicks',
                    'dynamic_click_threshold',
                    'spend',
                ]
            ],
            column_config={
                'bleeding_reason': UIContract.get_label('bleeding_reason'),
                'campaign_name': UIContract.get_label('campaign_name'),
                'ad_group_name': UIContract.get_label('ad_group_name'),
                'match_type': UIContract.get_label('match_type'),
                'targeting': UIContract.get_label('targeting'),
                'customer_search_term': UIContract.get_label('customer_search_term'),
                'clicks': st.column_config.NumberColumn(UIContract.get_label('clicks')),
                'dynamic_click_threshold': st.column_config.NumberColumn(
                    UIContract.get_label('dynamic_click_threshold')
                ),
                'spend': st.column_config.NumberColumn(
                    UIContract.get_label('spend'), format='$%.2f'
                ),
            },
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.success(t('tab1_success'))
        st.balloons()

    st.subheader(t('tab1_subheader2'))
    st.write(t('tab1_advice2'))

    if not cannibal_data['overlap_df'].empty:
        st.dataframe(
            cannibal_data['overlap_df'][
                [
                    'status',
                    'customer_search_term',
                    'campaign_name',
                    'match_type',
                    'targeting',
                    'spend',
                ]
            ],
            column_config={
                'status': UIContract.get_label('status'),
                'customer_search_term': UIContract.get_label('customer_search_term'),
                'campaign_name': UIContract.get_label('campaign_name'),
                'match_type': UIContract.get_label('match_type'),
                'targeting': UIContract.get_label('targeting'),
                'spend': st.column_config.NumberColumn(
                    UIContract.get_label('spend'), format='$%.2f'
                ),
            },
            use_container_width=True,
            hide_index=True,
        )


def _render_tab_structural_loss(breakeven_data, global_margin):
    st.subheader(t('tab2_subheader'))

    with st.expander(t('tab1_expander_title')):
        st.markdown(t('tab2_expander_content'))

    st.write(t('tab2_desc', days=breakeven_data.get('observation_window_days', 14)))

    df_loss = breakeven_data['unprofitable_campaigns_df']
    if not df_loss.empty:
        st.write(t('tab2_chart_title'))
        st.caption(t('tab2_chart_caption'))

        # ---------------------------------------------------------
        # 🚀 UPGRADED: Plotly Interactive Chart
        # ---------------------------------------------------------
        fig = px.scatter(
            df_loss,
            x='total_sales',
            y='total_spend',
            size='capital_lost',
            hover_name='campaign_name',  # Displays Campaign Name prominently on hover
            hover_data={
                'total_sales': ':$.2f',
                'total_spend': ':$.2f',
                'capital_lost': ':$.2f',
                'realized_acos': ':.2%',
            },
            labels={
                'total_sales': UIContract.get_label('total_sales'),
                'total_spend': UIContract.get_label('total_spend'),
                'capital_lost': UIContract.get_label('capital_lost'),
                'realized_acos': UIContract.get_label('realized_acos'),
            },
            color_discrete_sequence=['#ff4b4b'],
        )

        # Transparent background to match Streamlit's native light/dark mode
        fig.update_layout(
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=UIContract.get_label('total_sales'),
            yaxis_title=UIContract.get_label('total_spend'),
        )

        st.plotly_chart(fig, use_container_width=True)

        # ---------------------------------------------------------
        # DataFrame Rendering
        # ---------------------------------------------------------
        df_loss_view = df_loss.copy()
        df_loss_view['realized_acos'] = np.where(
            np.isinf(df_loss_view['realized_acos']), 0.0, df_loss_view['realized_acos'] * 100
        )

        st.dataframe(
            df_loss_view[
                [
                    'consultative_action',
                    'campaign_name',
                    'total_spend',
                    'total_sales',
                    'total_orders',
                    'realized_acos',
                    'allowable_spend',
                    'capital_lost',
                ]
            ],
            column_config={
                'consultative_action': UIContract.get_label('consultative_action'),
                'campaign_name': UIContract.get_label('campaign_name'),
                'total_spend': st.column_config.NumberColumn(
                    UIContract.get_label('total_spend'), format='$%.2f'
                ),
                'total_sales': st.column_config.NumberColumn(
                    UIContract.get_label('total_sales'), format='$%.2f'
                ),
                'total_orders': st.column_config.NumberColumn(UIContract.get_label('total_orders')),
                'realized_acos': st.column_config.NumberColumn(
                    UIContract.get_label('realized_acos'), format='%.2f%%'
                ),
                'allowable_spend': st.column_config.NumberColumn(
                    UIContract.get_label('allowable_spend'), format='$%.2f'
                ),
                'capital_lost': st.column_config.NumberColumn(
                    UIContract.get_label('capital_lost'), format='$%.2f'
                ),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success(t('tab2_success', margin=global_margin * 100))
        st.balloons()


def _render_tab_winners(df_winners, global_margin):
    st.subheader(t('tab3_subheader'))

    with st.expander(t('tab1_expander_title')):
        st.markdown(t('tab3_expander_content'))

    st.warning(t('tab3_warning'))
    st.write(t('tab3_desc'))

    if not df_winners.empty:
        df_winners_view = df_winners.copy()
        df_winners_view['acos'] = df_winners_view['acos'] * 100

        st.dataframe(
            df_winners_view[
                [
                    'audit_action',
                    'campaign_name',
                    'match_type',
                    'targeting',
                    'customer_search_term',
                    'orders_7d',
                    'acos',
                    'gross_profit',
                ]
            ],
            column_config={
                'audit_action': UIContract.get_label('audit_action'),
                'campaign_name': UIContract.get_label('campaign_name'),
                'match_type': UIContract.get_label('match_type'),
                'targeting': UIContract.get_label('targeting'),
                'customer_search_term': UIContract.get_label('customer_search_term'),
                'orders_7d': st.column_config.NumberColumn(UIContract.get_label('orders_7d')),
                'acos': st.column_config.NumberColumn(
                    UIContract.get_label('acos'), format='%.2f%%'
                ),
                'gross_profit': st.column_config.NumberColumn(
                    UIContract.get_label('gross_profit'), format='$%.2f'
                ),
            },
            use_container_width=True,
            hide_index=True,
        )


def _render_feedback_section():
    """Renders the product feedback form at the bottom of the main dashboard."""
    st.divider()
    st.subheader(t('feedback_expander'))

    sentiment = st.feedback('thumbs')

    with st.form(key='main_feedback_form'):
        user_thoughts = st.text_area(
            t('feedback_prompt'), placeholder=t('feedback_placeholder'), max_chars=500
        )
        submit_btn = st.form_submit_button(t('feedback_submit'), use_container_width=True)

        if submit_btn:
            if sentiment is None and not user_thoughts.strip():
                st.warning(t('feedback_warning'))
            else:
                insert_telemetry_row(
                    event_type='FEEDBACK', sentiment=sentiment, details=user_thoughts.strip()
                )
                st.success(t('feedback_success'))


# -------------------------------------------------------------
# 📄 EXCEL EXPORT ENGINE
# -------------------------------------------------------------
def generate_excel_report(auditor, global_margin: float) -> bytes:
    """Compiles the audit into a multi-sheet Excel binary buffer."""
    df_bleeders = auditor.extract_zero_sale_terms(global_margin_float=global_margin)
    cannibal_data = auditor.detect_match_type_cannibalization()
    breakeven_data = auditor.evaluate_campaign_breakeven_health(break_even_acos=global_margin)
    df_winners = auditor.extract_top_performing_terms(break_even_acos=global_margin)

    localization_map = UIContract.get_excel_map()
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        if not df_bleeders.empty:
            view = df_bleeders[
                [
                    'audit_action',
                    'campaign_name',
                    'ad_group_name',
                    'match_type',
                    'targeting',
                    'customer_search_term',
                    'clicks',
                    'dynamic_click_threshold',
                    'spend',
                ]
            ].copy()

            # 🚀 THE FIX: Rename the column before applying the global localization map
            view = view.rename(columns={'audit_action': 'bleeding_reason'})

            view.rename(columns=localization_map).to_excel(
                writer, sheet_name=t('sheet_bleeders', default='Bleeders'), index=False
            )

        if not cannibal_data['overlap_df'].empty:
            view = cannibal_data['overlap_df'][
                [
                    'status',
                    'customer_search_term',
                    'campaign_name',
                    'match_type',
                    'targeting',
                    'spend',
                ]
            ].copy()
            view.rename(columns=localization_map).to_excel(
                writer, sheet_name=t('sheet_cannibal', default='Cannibalization'), index=False
            )

        df_loss = breakeven_data.get('unprofitable_campaigns_df', pd.DataFrame())
        if not df_loss.empty:
            view = df_loss[
                [
                    'consultative_action',
                    'campaign_name',
                    'total_spend',
                    'total_sales',
                    'total_orders',
                    'realized_acos',
                    'allowable_spend',
                    'capital_lost',
                ]
            ].copy()
            view['realized_acos'] = np.where(
                np.isinf(view['realized_acos']), 0.0, view['realized_acos']
            )
            view.rename(columns=localization_map).to_excel(
                writer, sheet_name=t('sheet_loss', default='Structural Loss'), index=False
            )

        if not df_winners.empty:
            view = df_winners[
                [
                    'audit_action',
                    'campaign_name',
                    'match_type',
                    'targeting',
                    'customer_search_term',
                    'orders_7d',
                    'acos',
                    'gross_profit',
                ]
            ].copy()
            view.rename(columns=localization_map).to_excel(
                writer, sheet_name=t('sheet_winners', default='Winners'), index=False
            )

    return buffer.getvalue()
