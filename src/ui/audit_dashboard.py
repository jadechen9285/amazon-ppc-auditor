import io

import numpy as np
import pandas as pd
import streamlit as st

from ui.contract import UIContract


def render_audit_dashboard(auditor, global_margin: float):
    st.title('📊 亚马逊 SP 广告深度审计 (Sponsored Products)')
    st.caption('基于微观广告组级别的数据聚合，为您精准定位利润泄漏点与扩张机会。')

    # Fetch Data
    df_bleeders = auditor.extract_zero_sale_terms()
    cannibal_data = auditor.detect_match_type_cannibalization()
    fragility_data = auditor.assess_portfolio_fragility()

    # Ingest global_margin here
    breakeven_data = auditor.evaluate_campaign_breakeven_health(break_even_acos=global_margin)
    df_winners = auditor.extract_top_performing_terms(break_even_acos=global_margin)

    # Hero Metrics
    total_waste = df_bleeders['spend'].sum() if not df_bleeders.empty else 0.0
    total_waste += cannibal_data.get('total_cannibalized_spend', 0.0)

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label='🚨 预估可挽回损失 (30天)',
        value=f'${total_waste:,.2f}',
        delta='- 立即操作',
        delta_color='inverse',
        help='计算逻辑：[无转化无效花费] + [流量互斥与内卷]。这部分预算完全未产生转化或属于自我消耗，可通过执行下方表格的操作立即止损。',
    )

    col2.metric(
        label='📉 长期亏损广告活动',
        value=f'{breakeven_data.get("unprofitable_campaign_count", 0)} 个',
        delta='- 结构性亏损',
        delta_color='inverse',
        help=f'计算逻辑：在归因周期内，实际 ACoS 持续高于您设定的全局盈亏平衡线（{global_margin * 100:.0f}%）的广告活动数量。这些活动正在吞噬其他优质活动的净利润。',
    )

    risk_status = '⚠️ 极高风险' if fragility_data.get('is_fragile') else '✅ 健康'
    col3.metric(
        label='🏗️ 核心词流量集中度',
        value=f'{fragility_data.get("concentration_ratio", 0) * 100:.1f}%',
        delta=risk_status,
        delta_color='off',
        help='计算逻辑：账户花费前 10 名的搜索词占总花费的比例。若比例过高（>40%），说明账户过度依赖极少数词，极易因竞争对手提价或 A9 算法波动导致整体单量崩盘。',
    )

    st.divider()

    tab1, tab2, tab3 = st.tabs(['🛑 紧急止损清单', '💸 账户架构风险', '🚀 核心扩展机会'])

    with tab1:
        st.subheader('🩸 无转化无效花费 (Zero-Sale Bleeders)')

        # --- White-Box UI: The Accordion ---
        with st.expander('💡 算法原理解析 (How We Calculate This)'):
            st.markdown("""
            **1. 智能点击止损 (该给一个词多少次机会？):**
            我们不搞一刀切（比如死规定15次点击没出单就全关掉）。
            系统会先算一算，你平时的广告大概**几次点击能卖出一单**？比如你平时平均 10 次点击出一单，如果有个词被点了 15 次甚至更多，却连一单都没出，我们才会判定它在白白浪费你的钱，建议立刻拉黑（精准否定）。
            
            **2. 避免自己人打自己人 (流量内卷):**
            有时候，你的自动广告、广泛匹配都在抢同一个搜索词。这其实是在**自己抬高自己的广告费 (CPC)**。系统会帮你找出谁表现最好，把多余的关掉，把钱花在刀刃上。
            """)

        st.write('点击量过高但从未产生订单的搜索词，建议立即添加为**精准否定 (Negative Exact)**。')

        if not df_bleeders.empty:
            st.dataframe(
                df_bleeders[
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
                ],
                column_config={
                    'audit_action': UIContract.get_label('audit_action'),
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

        st.subheader('⚔️ 流量互斥与内卷 (Match-Type Cannibalization)')
        st.write('多个广告活动正在为同一个搜索词竞价，导致您自己在抬高自己的CPC。')
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

    with tab2:
        st.subheader('💸 结构性亏损 (Operating Below Margin)')

        # --- White-Box UI: The Accordion ---
        with st.expander('💡 算法原理解析 (How We Calculate This)'):
            st.markdown("""
            **怎么算出“纯利润净亏损”的？**
            这不是单纯看你花了多少广告费，而是结合了你设定的**毛利率 (Break-even Margin)** 算出来的一笔结结实实的经济账。
            
            **举个例子：**
            如果你设定的毛利是 30%，当你卖了 $100 时，按理说广告费绝不能超过 $30。如果你实际花了 $50 广告费，那么多出来的这 $20，就是**直接从你口袋里掏走的净亏损**。这个页面帮你一眼揪出这些正在抽干你现金流的“吞金兽”。
            """)

        st.write(
            f'在成熟归因期（{breakeven_data.get("observation_window_days")}天）内，实际ACoS严重超出盈亏平衡线的广告活动。'
        )

        df_loss = breakeven_data['unprofitable_campaigns_df']
        if not df_loss.empty:
            st.write('##### 亏损分布矩阵 (Loss Distribution Matrix)')
            st.caption('气泡大小代表净亏损金额。位于左上方的广告活动正在消耗大量预算却鲜有产出。')

            # Fetch the Excel map to leverage the automatic "($)" suffixes for the chart axes
            excel_map = UIContract.get_excel_map()

            chart_view = df_loss[['total_sales', 'total_spend', 'capital_lost']].copy()
            chart_map = {
                'total_sales': excel_map['total_sales'],
                'total_spend': excel_map['total_spend'],
                'capital_lost': excel_map['capital_lost'],
            }
            chart_view = chart_view.rename(columns=chart_map)

            st.scatter_chart(
                chart_view,
                x=excel_map['total_sales'],
                y=excel_map['total_spend'],
                size=excel_map['capital_lost'],
                color='#ff4b4b',
                height=350,
            )

            # --- THE VIEW LAYER TRANSFORMATION ---
            df_loss_view = df_loss.copy()
            df_loss_view['realized_acos'] = np.where(
                np.isinf(df_loss_view['realized_acos']), 0.0, df_loss_view['realized_acos'] * 100
            )

            columns_to_display = [
                'consultative_action',
                'campaign_name',
                'total_spend',
                'total_sales',
                'total_orders',
                'realized_acos',
                'allowable_spend',
                'capital_lost',
            ]

            st.dataframe(
                df_loss_view[columns_to_display],
                column_config={
                    'consultative_action': UIContract.get_label('consultative_action'),
                    'campaign_name': UIContract.get_label('campaign_name'),
                    'total_spend': st.column_config.NumberColumn(
                        UIContract.get_label('total_spend'), format='$%.2f'
                    ),
                    'total_sales': st.column_config.NumberColumn(
                        UIContract.get_label('total_sales'), format='$%.2f'
                    ),
                    'total_orders': st.column_config.NumberColumn(
                        UIContract.get_label('total_orders')
                    ),
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

    with tab3:
        st.subheader('🌟 黄金扩展词 (Top Performers)')

        # --- White-Box UI: The Accordion ---
        with st.expander('💡 算法原理解析 (How We Calculate This)'):
            st.markdown("""
            **如何安全地把好词放大？**
            系统帮你挑出了既能稳定出单，又不会让你亏钱的“神仙词”。
            
            - **如果它已经是精准匹配：** 说明定位很准，建议直接加点竞价或预算，让它跑得更好。
            - **如果它是从自动或广泛广告里跑出来的：** 建议把它单独拿出来，建一个新的“精准广告组”。给它专属的预算去抢占搜索页顶部，同时这么做也不会破坏你原来广告组的节奏。
            """)

        st.warning(
            '⚠️ **A9 迁移规则 (Peel & Stick):** 提取新词时**切勿直接暂停原词**。应先降低原词竞价 (30%-50%)，待新组观察 7-14 天稳定出单后，再否定原词，以免历史权重清零。'
        )

        st.write('高转化且ACoS低于盈亏平衡线的优质词，根据其当前匹配类型执行不同扩量策略。')

        df_winners = auditor.extract_top_performing_terms(break_even_acos=global_margin)

        if not df_winners.empty:
            # --- THE VIEW LAYER TRANSFORMATION ---
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


def generate_excel_report(auditor, global_margin: float) -> bytes:
    """
    Compiles the entire audit state into a localized, multi-sheet Excel binary buffer.
    """
    # 1. Fetch the raw data
    df_bleeders = auditor.extract_zero_sale_terms()
    cannibal_data = auditor.detect_match_type_cannibalization()
    breakeven_data = auditor.evaluate_campaign_breakeven_health(break_even_acos=global_margin)
    df_winners = auditor.extract_top_performing_terms(break_even_acos=global_margin)

    # 2. Extract the automated Excel Transformation Matrix
    localization_map = UIContract.get_excel_map()

    # 3. Initialize the RAM Buffer and Excel Writer
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Sheet 1: Bleeders
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
            view.rename(columns=localization_map).to_excel(
                writer, sheet_name='紧急止损 (Bleeders)', index=False
            )

        # Sheet 2: Cannibalization
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
                writer, sheet_name='流量内卷 (Cannibalization)', index=False
            )

        # Sheet 3: Structural Loss
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
                writer, sheet_name='结构亏损 (Loss)', index=False
            )

        # Sheet 4: Winners
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
                writer, sheet_name='核心扩展 (Winners)', index=False
            )

    # 4. Return the binary string
    return buffer.getvalue()
