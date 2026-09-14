import streamlit as st

# from src.auditor.amazon_ppc_auditor import AmazonPPCAuditor

def render_audit_dashboard(auditor): # auditor is an initialized AmazonPPCAuditor instance

    st.title("📊 亚马逊 PPC 深度审计报告")
    st.caption("基于微观广告组级别的数据聚合，为您精准定位利润泄漏点与扩张机会。")

    # Fetch Data
    df_bleeders = auditor.extract_zero_sale_terms()
    cannibal_data = auditor.detect_match_type_cannibalization()
    fragility_data = auditor.assess_portfolio_fragility()
    breakeven_data = auditor.evaluate_campaign_breakeven_health()
    df_winners = auditor.extract_top_performing_terms()

    # Hero Metrics (Updated to $)
    total_waste = df_bleeders['spend'].sum() if not df_bleeders.empty else 0.0
    total_waste += cannibal_data.get('total_cannibalized_spend', 0.0)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🚨 预估可挽回损失 (30天)", f"${total_waste:,.2f}", "- 立即操作", delta_color="inverse")
    col2.metric("📉 长期亏损广告活动", f"{breakeven_data.get('unprofitable_campaign_count', 0)} 个", "- 结构性亏损", delta_color="inverse")
    
    risk_status = "⚠️ 极高风险" if fragility_data.get('is_fragile') else "✅ 健康"
    col3.metric("🏗️ 核心词流量集中度", f"{fragility_data.get('concentration_ratio', 0) * 100:.1f}%", risk_status, delta_color="off")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["🛑 紧急止损清单", "💸 账户架构风险", "🚀 核心扩展机会"])

    with tab1:
        st.subheader("🩸 无转化无效花费 (Zero-Sale Bleeders)")
        st.write("点击量过高但从未产生订单的搜索词，建议立即添加为**精准否定 (Negative Exact)**。")
        if not df_bleeders.empty:
            st.dataframe(
                df_bleeders[['audit_action', 'campaign_name', 'ad_group_name', 'customer_search_term', 'clicks', 'spend']],
                column_config={
                    "audit_action": "系统建议操作",
                    "campaign_name": "广告活动",
                    "ad_group_name": "广告组",
                    "customer_search_term": "客户搜索词",
                    "clicks": st.column_config.NumberColumn("白嫖点击数"),
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
        st.write(f"在成熟归因期（{breakeven_data.get('observation_window_days')}天）内，实际ACoS严重超出盈亏平衡线的广告活动。")
        
        df_loss = breakeven_data['unprofitable_campaigns_df']
        if not df_loss.empty:
            
            # --- VISUALIZATION ADDITION ---
            st.write("##### 亏损分布矩阵 (Loss Distribution Matrix)")
            st.caption("气泡大小代表净亏损金额。位于左上方的广告活动正在消耗大量预算却鲜有产出。")
            
            # Native Streamlit scatter chart mapped to our backend variables
            st.scatter_chart(
                df_loss,
                x='total_sales',
                y='total_spend',
                size='capital_lost',
                color='#ff4b4b', # Use a strict alert red
                height=350
            )
            
            # --- FIXED TABLE BASED ON IMAGE FEEDBACK ---
            st.dataframe(
                df_loss,
                column_config={
                    "campaign_name": "广告活动",
                    "total_spend": st.column_config.NumberColumn("总花费", format="$%.2f"),
                    "total_sales": st.column_config.NumberColumn("总销售额", format="$%.2f"),
                    "total_orders": st.column_config.NumberColumn("总订单量"),
                    "realized_acos": st.column_config.NumberColumn("实际 ACoS", format="%.2f"),
                    "allowable_spend": st.column_config.NumberColumn("允许花费阈值", format="$%.2f"),
                    "capital_lost": st.column_config.NumberColumn("纯利润净亏损", format="$%.2f")
                },
                use_container_width=True, hide_index=True
            )

    with tab3:
        st.subheader("🌟 黄金扩展词 (Top Performers)")

        st.warning(
            "⚠️ **A9 权重迁移警告 (Migration Risk):**\n\n"
            "不要直接暂停原广告组中的词！直接迁移会导致该词历史权重清零。请采用 **平滑过渡法 (Peel & Stick)**：\n"
            "1. 将词提取到全新的 SKAG 精准组，给予充足预算。\n"
            "2. 保留原广告组中的该词，但将其竞价 (Bid) 降低 30%-50%。\n"
            "3. 观察 7-14 天，等新组 A9 权重建立并稳定出单后，再将原组词精确否定或完全降价。"
        )

        st.write("高转化且ACoS低于盈亏平衡线的优质词，建议**移至独立精准广告组 (SKAG)** 并放大预算。")
        if not df_winners.empty:
            st.dataframe(
                df_winners[['audit_action', 'campaign_name', 'customer_search_term', 'orders_7d', 'acos', 'gross_profit']],
                column_config={
                    "audit_action": "系统建议操作",
                    "campaign_name": "来源广告活动",
                    "customer_search_term": "优质搜索词",
                    "orders_7d": "订单量",
                    "acos": st.column_config.NumberColumn("实际 ACoS"),
                    "gross_profit": st.column_config.NumberColumn("预估毛利润贡献", format="$%.2f")
                },
                use_container_width=True, hide_index=True
            )