import io 
import numpy as np
import pandas as pd
import streamlit as st


def render_audit_dashboard(auditor, global_margin:float): 
    st.title("📊 亚马逊 SP 广告深度审计 (Sponsored Products)")
    st.caption("基于微观广告组级别的数据聚合，为您精准定位利润泄漏点与扩张机会。")

    # Fetch Data``
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
        label="🚨 预估可挽回损失 (30天)", 
        value=f"${total_waste:,.2f}", 
        delta="- 立即操作", 
        delta_color="inverse",
        help="计算逻辑：[无转化无效花费] + [同词竞价互斥中的劣势词花费]。这部分预算完全未产生转化或属于自我消耗，可通过执行下方表格的操作立即止损。"
    )
    
    col2.metric(
        label="📉 长期亏损广告活动", 
        value=f"{breakeven_data.get('unprofitable_campaign_count', 0)} 个", 
        delta="- 结构性亏损", 
        delta_color="inverse",
        help=f"计算逻辑：在归因周期内，实际 ACoS 持续高于您设定的全局盈亏平衡线（{global_margin * 100:.0f}%）的广告活动数量。这些活动正在吞噬其他优质活动的净利润。"
    )
    
    risk_status = "⚠️ 极高风险" if fragility_data.get('is_fragile') else "✅ 健康"
    col3.metric(
        label="🏗️ 核心词流量集中度", 
        value=f"{fragility_data.get('concentration_ratio', 0) * 100:.1f}%", 
        delta=risk_status, 
        delta_color="off",
        help="计算逻辑：账户花费前 10 名的搜索词占总花费的比例。若比例过高（>40%），说明账户过度依赖极少数词，极易因竞争对手提价或 A9 算法波动导致整体单量崩盘。"
    )

    st.divider()

    tab1, tab2, tab3 = st.tabs(["🛑 紧急止损清单", "💸 账户架构风险", "🚀 核心扩展机会"])

    with tab1:
        st.subheader("🩸 无转化无效花费 (Zero-Sale Bleeders)")

        # --- White-Box UI: The Accordion ---
        with st.expander("💡 算法原理解析 (How We Calculate This)"):
            st.markdown("""
            **1. 动态容忍阈值 (Dynamic Click Threshold):**
            系统**没有**使用死板的固定规则（例如“满15次点击无转化就暂停”）。
            算法首先计算该广告活动的**历史平均转化率**，推算出一单所需的预期点击量。只有当一个搜索词的点击量超过预期的 1.5 倍（包含安全缓冲期）且仍未出单时，系统才会判定其为真正的“无效花费”。
            
            **2. 流量互斥 (Cannibalization):**
            当您的多个匹配方式（如广泛、词组、自动）同时为同一个搜索词竞价时，您实际上是在**自己和自己竞价**，抬高了单次点击成本 (CPC)。系统会对比它们的转化效率，保留最优解，建议暂停内部竞争者。
            """)
            
        st.write("点击量过高但从未产生订单的搜索词，建议立即添加为**精准否定 (Negative Exact)**。")

        if not df_bleeders.empty:
            st.dataframe(
                # Added match_type and dynamic_click_threshold
                df_bleeders[['audit_action', 'campaign_name', 'ad_group_name', 'customer_search_term', 'match_type', 'clicks', 'dynamic_click_threshold', 'spend']],
                column_config={
                    "audit_action": "系统建议操作",
                    "campaign_name": "广告活动",
                    "ad_group_name": "广告组",
                    "customer_search_term": "客户搜索词",
                    "match_type": "匹配类型",
                    "clicks": st.column_config.NumberColumn("实际点击数"),
                    "dynamic_click_threshold": st.column_config.NumberColumn("动态容忍阈值"),
                    "spend": st.column_config.NumberColumn("浪费花费", format="$%.2f")
                },
                use_container_width=True, hide_index=True
            )
        
        st.subheader("⚔️ 流量互斥与内卷 (Match-Type Cannibalization)")
        st.write("多个广告活动正在为同一个搜索词竞价，导致您自己在抬高自己的CPC。")
        if not cannibal_data['overlap_df'].empty:
            st.dataframe(
                cannibal_data['overlap_df'][['status', 'customer_search_term', 'campaign_name', 'match_type', 'spend']],
                column_config={
                    "status": "胜败状态",
                    "customer_search_term": "冲突搜索词",
                    "campaign_name": "所属广告活动",
                    "match_type": "匹配类型",
                    "spend": st.column_config.NumberColumn("花费", format="$%.2f")
                },
                use_container_width=True, hide_index=True
            )

    with tab2:
        st.subheader("💸 结构性亏损 (Operating Below Margin)")

        # --- White-Box UI: The Accordion ---
        with st.expander("💡 算法原理解析 (How We Calculate This)"):
            st.markdown("""
            **纯利润净亏损 (Capital Lost) 的计算逻辑：**
            这不是简单的总花费。系统基于您在侧边栏设定的 **盈亏平衡线 (Break-even Margin)** 进行逆向推算。
            
            例如：如果您设定毛利为 30%，产生 $100 销售额时，您的“允许最高花费”就是 $30。如果实际花费了 $50，系统会精准标注出 $20 的**纯利润净亏损**。这帮您一眼看出哪些活动在抽干您的现金流。
            """)

        st.write(f"在成熟归因期（{breakeven_data.get('observation_window_days')}天）内，实际ACoS严重超出盈亏平衡线的广告活动。")
        
        df_loss = breakeven_data['unprofitable_campaigns_df']
        if not df_loss.empty:
            
            st.write("##### 亏损分布矩阵 (Loss Distribution Matrix)")
            st.caption("气泡大小代表净亏损金额。位于左上方的广告活动正在消耗大量预算却鲜有产出。")

            chart_view = df_loss[['total_sales', 'total_spend', 'capital_lost']].copy()
            
            # 2. Rename the columns to professional frontend labels
            chart_map = {
                'total_sales': '总销售额 ($)',
                'total_spend': '总花费 ($)',
                'capital_lost': '纯利润净亏损 ($)'
            }
            chart_view = chart_view.rename(columns=chart_map)
            
            st.scatter_chart(
                chart_view,
                x='总销售额 ($)',
                y='总花费 ($)',
                size='纯利润净亏损 ($)',
                color='#ff4b4b', 
                height=350
            )
            
            # --- THE VIEW LAYER TRANSFORMATION ---
            df_loss_view = df_loss.copy()
            # Handle infinite values (when sales = 0) gracefully before multiplication
            df_loss_view['realized_acos'] = np.where(
                np.isinf(df_loss_view['realized_acos']), 
                0.0, 
                df_loss_view['realized_acos'] * 100
            )
            
            columns_to_display = ['consultative_action', 'campaign_name', 'total_spend', 'total_sales', 'total_orders', 'realized_acos', 'allowable_spend', 'capital_lost']
            
            st.dataframe(
                df_loss_view[columns_to_display],
                column_config={
                    "consultative_action": "系统建议 (Action)",
                    "campaign_name": "广告活动",
                    "total_spend": st.column_config.NumberColumn("总花费", format="$%.2f"),
                    "total_sales": st.column_config.NumberColumn("总销售额", format="$%.2f"),
                    "total_orders": st.column_config.NumberColumn("总订单量"),
                    # Format as percentage with 2 decimals
                    "realized_acos": st.column_config.NumberColumn("实际 ACoS", format="%.2f%%"),
                    "allowable_spend": st.column_config.NumberColumn("允许花费阈值", format="$%.2f"),
                    "capital_lost": st.column_config.NumberColumn("纯利润净亏损", format="$%.2f")
                },
                use_container_width=True, hide_index=True
            )

    with tab3:
        st.subheader("🌟 黄金扩展词 (Top Performers)")

        # --- White-Box UI: The Accordion ---
        with st.expander("💡 算法原理解析 (How We Calculate This)"):
            st.markdown("""
            **动态扩量策略 (Context-Aware Scaling):**
            系统筛选出出单稳定（≥3单）且 ACoS 严格低于您盈亏平衡线的优质词。
            - 如果该词已经是 **精准匹配 (Exact)**：系统建议您原位提高竞价或放宽预算。
            - 如果该词属于 **广泛/词组/自动 (Broad/Phrase/Auto)**：系统建议将其剥离，建立独立的精准广告组 (SKAG)，以独占顶部流量，同时防止原广告组权重受损。
            """)

        st.warning("⚠️ **A9 迁移规则 (Peel & Stick):** 提取新词时**切勿直接暂停原词**。应先降低原词竞价 (30%-50%)，待新组观察 7-14 天稳定出单后，再否定原词，以免历史权重清零。")

        st.write("高转化且ACoS低于盈亏平衡线的优质词，根据其当前匹配类型执行不同扩量策略。")
        df_winners = breakeven_data.get('unprofitable_campaigns_df', pd.DataFrame()) # Placeholder check
        df_winners = auditor.extract_top_performing_terms(break_even_acos=global_margin)
        
        if not df_winners.empty:
            
            # --- THE VIEW LAYER TRANSFORMATION ---
            df_winners_view = df_winners.copy()
            df_winners_view['acos'] = df_winners_view['acos'] * 100
            
            st.dataframe(
                df_winners_view[['audit_action', 'campaign_name', 'customer_search_term', 'match_type', 'orders_7d', 'acos', 'gross_profit']],
                column_config={
                    "audit_action": "系统建议操作",
                    "campaign_name": "来源广告活动",
                    "customer_search_term": "优质搜索词",
                    "match_type": "当前匹配类型",
                    "orders_7d": "订单量",
                    # Format as percentage with 2 decimals
                    "acos": st.column_config.NumberColumn("实际 ACoS", format="%.2f%%"),
                    "gross_profit": st.column_config.NumberColumn("预估毛利润贡献", format="$%.2f")
                },
                use_container_width=True, hide_index=True
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

    # 2. Define the Universal Transformation Matrix (Localization)
    localization_map = {
        "audit_action": "系统建议操作",
        "consultative_action": "系统建议 (Action)",
        "status": "胜败状态",
        "campaign_name": "广告活动",
        "ad_group_name": "广告组",
        "customer_search_term": "客户搜索词",
        "match_type": "匹配类型",
        "clicks": "实际点击数",
        "dynamic_click_threshold": "动态容忍阈值",
        "spend": "总花费 ($)",
        "total_spend": "总花费 ($)",
        "total_sales": "总销售额 ($)",
        "total_orders": "总订单量",
        "orders_7d": "订单量",
        "realized_acos": "实际 ACoS",
        "acos": "实际 ACoS",
        "allowable_spend": "允许花费阈值 ($)",
        "capital_lost": "纯利润净亏损 ($)",
        "gross_profit": "预估毛利润贡献 ($)"
    }

    # 3. Initialize the RAM Buffer and Excel Writer
    buffer = io.BytesIO()
    
    # xlsxwriter handles CJK encoding natively and beautifully
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        
        # Sheet 1: Bleeders
        if not df_bleeders.empty:
            view = df_bleeders[['audit_action', 'campaign_name', 'ad_group_name', 'customer_search_term', 'match_type', 'clicks', 'dynamic_click_threshold', 'spend']].copy()
            view.rename(columns=localization_map).to_excel(writer, sheet_name='紧急止损 (Bleeders)', index=False)
            
        # Sheet 2: Cannibalization
        if not cannibal_data['overlap_df'].empty:
            view = cannibal_data['overlap_df'][['status', 'customer_search_term', 'campaign_name', 'match_type', 'spend']].copy()
            view.rename(columns=localization_map).to_excel(writer, sheet_name='流量内卷 (Cannibalization)', index=False)
            
        # Sheet 3: Structural Loss
        df_loss = breakeven_data.get('unprofitable_campaigns_df', pd.DataFrame())
        if not df_loss.empty:
            view = df_loss[['consultative_action', 'campaign_name', 'total_spend', 'total_sales', 'total_orders', 'realized_acos', 'allowable_spend', 'capital_lost']].copy()
            view['realized_acos'] = np.where(np.isinf(view['realized_acos']), 0, view['realized_acos']) # Fix infinity
            view.rename(columns=localization_map).to_excel(writer, sheet_name='结构亏损 (Loss)', index=False)
            
        # Sheet 4: Winners
        if not df_winners.empty:
            view = df_winners[['audit_action', 'campaign_name', 'customer_search_term', 'match_type', 'orders_7d', 'acos', 'gross_profit']].copy()
            view.rename(columns=localization_map).to_excel(writer, sheet_name='核心扩展 (Winners)', index=False)

    # 4. Return the binary string
    return buffer.getvalue()