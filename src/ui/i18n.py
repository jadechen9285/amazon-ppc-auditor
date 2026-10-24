import streamlit as st

TEXTS = {
    # ---------------------------------------------------------
    # 1. Main Landing
    # ---------------------------------------------------------
    'main_title': {'zh': '📊 亚马逊 SP 广告深度审计专家', 'en': '📊 Amazon SP Ads Deep Auditor'},
    'main_subtitle': {
        'zh': '无需授权店铺 API，本地内存脱敏计算，精准定位无效点击与利润流失点。',
        'en': 'No API required. Secure, local-memory computing to identify wasted clicks and profit bleeders.',
    },
    'landing_col1': {
        'zh': '#### 🛑 紧急止损清单\n精准抓取只消耗不转化的无效词及竞价冲突。',
        'en': '#### 🛑 Emergency Stops\nIdentify zero-sale spenders and match-type cannibalization.',
    },
    'landing_col2': {
        'zh': '#### 💸 账户架构风险\n结合保本利润率，揪出长期结构性亏损广告活动。',
        'en': '#### 💸 Structural Risks\nPinpoint campaigns operating structurally below your break-even margin.',
    },
    'landing_col3': {
        'zh': '#### 🚀 核心扩展机会\n筛选出单稳定、ACoS 低于保本线的黄金词以供扩量。',
        'en': '#### 🚀 Scaling Opportunities\nFilter top-performing terms operating safely below target ACoS for exact match scaling.',
    },
    'upload_instruction': {
        'zh': '👈 请在左侧边栏上传从亚马逊卖家中心导出的搜索词报表开始审计。',
        'en': '👈 Please upload your Search Term Report from Amazon Seller Central in the left sidebar to begin.',
    },
    # ---------------------------------------------------------
    # 2. Sidebar Controls
    # ---------------------------------------------------------
    'lang_selector': {'zh': '🌐 语言 / Language', 'en': '🌐 Language / 语言'},
    'financial_setup': {'zh': '### ⚙️ 财务配置', 'en': '### ⚙️ Financial Setup'},
    'margin_label': {
        'zh': '🎯 盈亏平衡 ACoS (Break-even Margin)',
        'en': '🎯 Break-even Margin (Target ACoS)',
    },
    'margin_help': {
        'zh': '您的产品净毛利率。当实际 ACoS 超过此数值时，广告即产生绝对亏损。',
        'en': 'Your net profit margin. If actual ACoS exceeds this, the ad is generating an absolute loss.',
    },
    'upload_label': {
        'zh': '📥 上传搜索词报告 (Excel / CSV)',
        'en': '📥 Upload Search Term Report (Excel/CSV)',
    },
    'upload_help': {
        'zh': '支持中/英文 SP Search Term Report。最大文件为 {max_size}MB。',
        'en': 'Supports EN/ZH SP Search Term Reports. Max file size: {max_size}MB.',
    },
    'export_button': {
        'zh': '📥 导出完整审计报告 (Excel)',
        'en': '📥 Export Full Audit Report (Excel)',
    },
    'feedback_expander': {'zh': '🗣️ 听听您的声音 (Feedback)', 'en': '🗣️ Product Feedback'},
    # ---------------------------------------------------------
    # 3. Validation & Errors
    # ---------------------------------------------------------
    'file_too_large': {
        'zh': '🛑 **文件过大 ({size:.1f} MB)**',
        'en': '🛑 **File too large ({size:.1f} MB)**',
    },
    'file_too_large_warning': {
        'zh': '为了保证计算稳定性，当前最高支持 **{max_size} MB** 的报表。\n1. 缩短报表至 14-30 天。\n2. 删除无关行。',
        'en': 'To ensure stability, max file size is **{max_size} MB**.\n1. Download a 14-30 day report.\n2. Delete irrelevant rows before uploading.',
    },
    'temporal_warning': {
        'zh': '⚠️ **周期过短 ({days} 天):** 存在 7 天归因延迟，系统已强制输出结果，建议保持谨慎避免误杀。',
        'en': '⚠️ **Short Window ({days} days):** Due to 7-day attribution lag, results are forced. Execute caution to avoid pausing good targets.',
    },
    'temporal_success': {
        'zh': '📅 **报表周期:** {days} 天 (数据量充足，模型输出置信度高)',
        'en': '📅 **Report Window:** {days} days (High confidence output)',
    },
    'schema_error': {
        'zh': '❌ **报表格式验证失败:** {error}',
        'en': '❌ **Schema Validation Failed:** {error}',
    },
    'upload_checklist': {
        'zh': '💡 **上传检查清单:**\n1. 必须是 Sponsored Products (SP) 报表。\n2. 导出后请勿更改列名。',
        'en': '💡 **Checklist:**\n1. Must be a Sponsored Products (SP) Search Term report.\n2. Do not modify or delete columns after exporting.',
    },
    # ---------------------------------------------------------
    # 4. Feedback Form
    # ---------------------------------------------------------
    'feedback_prompt': {
        'zh': '告诉我们您的需求 / Bug反馈：',
        'en': 'Feature request / Bug report:',
    },
    'feedback_placeholder': {'zh': '希望增加什么功能？', 'en': 'What else would you like to see?'},
    'feedback_submit': {'zh': '🚀 提交反馈', 'en': '🚀 Submit Feedback'},
    'feedback_warning': {'zh': '⚠️ 请输入反馈内容', 'en': '⚠️ Please enter your feedback'},
    'feedback_success': {'zh': '✅ 收到！感谢支持。', 'en': '✅ Received! Thank you.'},
    # ---------------------------------------------------------
    # 5. Dashboard Hero Metrics
    # ---------------------------------------------------------
    'dashboard_title': {
        'zh': '📊 亚马逊 SP 广告深度审计 (Sponsored Products)',
        'en': '📊 Amazon SP Ads Deep Audit (Sponsored Products)',
    },
    'dashboard_caption': {
        'zh': '基于微观广告组级别的数据聚合，为您精准定位利润泄漏点与扩张机会。',
        'en': 'Micro-ad group level data aggregation to pinpoint profit leaks and scaling opportunities.',
    },
    'hero_waste_label': {'zh': '🚨 预估可挽回损失 (30天)', 'en': '🚨 Est. Recoverable Loss (30D)'},
    'hero_waste_delta': {'zh': '- 立即操作', 'en': '- Action Required'},
    'hero_waste_help': {
        'zh': '计算逻辑：[无转化无效花费] + [流量互斥与内卷]。这部分预算完全未产生转化或属于自我消耗，可通过执行下方表格的操作立即止损。',
        'en': 'Logic: [Zero-Sale Spend] + [Cannibalized Spend]. This budget generated no conversions and can be recovered by executing the actions below.',
    },
    'hero_loss_label': {'zh': '📉 长期亏损广告活动', 'en': '📉 Unprofitable Campaigns'},
    'hero_loss_delta': {'zh': '- 结构性亏损', 'en': '- Structural Loss'},
    'hero_loss_help': {
        'zh': '计算逻辑：在归因周期内，实际 ACoS 持续高于您设定的全局盈亏平衡线（{margin:.0f}%）的广告活动数量。',
        'en': 'Logic: Number of campaigns operating consistently above your {margin:.0f}% break-even threshold, draining net profit.',
    },
    'hero_risk_label': {'zh': '🏗️ 核心词流量集中度', 'en': '🏗️ Traffic Concentration Risk'},
    'hero_risk_status_high': {'zh': '⚠️ 极高风险', 'en': '⚠️ High Risk'},
    'hero_risk_status_ok': {'zh': '✅ 健康', 'en': '✅ Healthy'},
    'hero_risk_help': {
        'zh': '计算逻辑：账户花费前 10 名的搜索词占总花费的比例。若比例过高（>40%），极易因竞争对手提价导致整体单量崩盘。',
        'en': 'Logic: % of total spend driven by the top 10 search terms. >40% indicates a fragile account highly vulnerable to competitor CPC spikes.',
    },
    # ---------------------------------------------------------
    # 6. Tab 1: Bleeders
    # ---------------------------------------------------------
    'tab_bleeders': {'zh': '🛑 紧急止损清单', 'en': '🛑 Emergency Stops'},
    'tab1_subheader1': {
        'zh': '🩸 无转化无效花费 (Zero-Sale Bleeders)',
        'en': '🩸 Zero-Sale Bleeders',
    },
    'tab1_expander_title': {
        'zh': '💡 算法原理解析 (How We Calculate This)',
        'en': '💡 Algorithm Explained (How We Calculate This)',
    },
    'tab1_expander_content': {
        'zh': '**1. 🩸 无效点击止损：双引擎防御机制**\n传统的软件只会死板地规定“大于15次点击不出单就关闭”，这非常容易误判。我们采用了更贴近商业逻辑的双引擎算法，为您计算出每一行的 **最大容忍点击数 (Max Tolerated Clicks)**：\n* **🚨 极速消耗 (流血太快):** 系统结合了您的客单价与左侧设置的保本利润率，算出极限获客成本。如果某个词一单没出，但花费极高，系统会严格压缩它的容忍点击数。（*商业逻辑：亏得太快，根本等不起亚马逊的数据延迟！*）\n* **⏳ 长期不转化 (慢性放血):** 对于花钱不快的词，系统会分析您平时的转化率，给出一个相对宽松的容忍点击数。\n👉 **怎么看表？** 当表格中的实际“点击量”超过了系统给出的“最大容忍点击数”时，即被判定为无效词，建议立刻精准否定。\n\n**2. ⚔️ 流量内卷：避免“自己人打自己人”**\n有时候，您的自动广告、广泛匹配和词组匹配都在同时竞价抢夺同一个搜索词。这会导致多个广告组互相竞争，自己抬高自己的单次点击费 (CPC)。系统会帮您揪出这些“同室操戈”的词，把钱花在转化率最高的那一个上。',
        'en': "**1. 🩸 Zero-Sale Defense: Dual-Engine Algorithm**\nTraditional software strictly cuts keywords at '15 clicks without a sale', causing false positives. We dynamically calculate a **Max Tolerated Clicks** threshold for every single row:\n* **🚨 Fast Hemorrhage:** We combine your AOV and Target Break-even Margin. If a term is spending too fast without a sale, we strictly compress its tolerated clicks. *(Logic: You are losing money too fast to wait for Amazon's attribution lag)*.\n* **⏳ Chronic Non-Converter:** For slow spenders, we analyze historical CVR to grant a more lenient click threshold.\n👉 **How to read the table:** If actual 'Clicks' exceed our calculated 'Max Tolerated Clicks', the term is flagged. We recommend negating it immediately.\n\n**2. ⚔️ Match-Type Cannibalization**\nSometimes Auto, Broad, and Phrase match compete against each other for the exact same search term, artificially inflating your own CPC. We isolate these conflicts so you can pause redundant targets.",
    },
    'tab1_advice': {
        'zh': '点击量过高但从未产生订单的搜索词，建议立即添加为**精准否定 (Negative Exact)**。',
        'en': 'Search terms with high clicks but no orders. We recommend adding these as **Negative Exact** immediately.',
    },
    'tab1_success': {
        'zh': '🎉 **太棒了！** 您的报表中没有发现严重超标的纯消耗词，预算拦截做得非常出色！',
        'en': '🎉 **Excellent!** No severe zero-sale bleeders found in your report. Great budget control!',
    },
    'tab1_subheader2': {
        'zh': '⚔️ 流量互斥与内卷 (Match-Type Cannibalization)',
        'en': '⚔️ Match-Type Cannibalization',
    },
    'tab1_advice2': {
        'zh': '多个广告活动正在为同一个搜索词竞价，导致您自己在抬高自己的CPC。',
        'en': 'Multiple campaigns are bidding on the exact same search term, artificially inflating your CPC.',
    },
    # ---------------------------------------------------------
    # 7. Tab 2: Structural Loss
    # ---------------------------------------------------------
    'tab_loss': {'zh': '💸 账户架构风险', 'en': '💸 Structural Risks'},
    'tab2_subheader': {
        'zh': '💸 结构性亏损 (Operating Below Margin)',
        'en': '💸 Structural Loss (Operating Below Margin)',
    },
    'tab2_expander_content': {
        'zh': '**怎么算出“纯利润净亏损”的？**\n这不是单纯看你花了多少广告费，而是结合了你设定的**毛利率 (Break-even Margin)** 算出来的一笔结结实实的经济账。\n\n**举个例子：**\n如果你设定的毛利是 30%，当你卖了 $100 时，按理说广告费绝不能超过 $30。如果你实际花了 $50 广告费，那么多出来的这 $20，就是**直接从你口袋里掏走的净亏损**。这个页面帮你一眼揪出这些正在抽干你现金流的“吞金兽”。',
        'en': "**How do we calculate 'Capital Lost'?**\nIt's not just your total ad spend. We calculate an economic threshold based on the Break-even Margin you set in the sidebar.\n\n**Example:**\nIf your margin is 30% and a campaign generates $100 in sales, your allowable ad spend is $30. If you actually spent $50, that extra $20 is directly pulled from your net profit. This page visualizes the campaigns bleeding your cash flow.",
    },
    'tab2_desc': {
        'zh': '在成熟归因期（{days}天）内，实际ACoS严重超出盈亏平衡线的广告活动。',
        'en': 'Campaigns where actual ACoS severely exceeds your break-even threshold during the {days}-day observation window.',
    },
    'tab2_chart_title': {
        'zh': '##### 亏损分布矩阵 (Loss Distribution Matrix)',
        'en': '##### Loss Distribution Matrix',
    },
    'tab2_chart_caption': {
        'zh': '气泡大小代表净亏损金额。位于左上方的广告活动正在消耗大量预算却鲜有产出。',
        'en': 'Bubble size represents net capital lost. Campaigns in the top-left are burning budget with minimal output.',
    },
    'tab2_success': {
        'zh': '📈 **盈利健康！** 在 {margin:.0f}% 的保本利润率下，没有发现长期处于绝对亏损状态的广告组。',
        'en': '📈 **Healthy!** No campaigns found operating at an absolute structural loss under a {margin:.0f}% break-even threshold.',
    },
    # ---------------------------------------------------------
    # 8. Tab 3: Winners
    # ---------------------------------------------------------
    'tab_winners': {'zh': '🚀 核心扩展机会', 'en': '🚀 Scaling Opportunities'},
    'tab3_subheader': {
        'zh': '🌟 黄金扩展词 (Top Performers)',
        'en': '🌟 Scaling Opportunities (Top Performers)',
    },
    'tab3_expander_content': {
        'zh': '**如何安全地把好词放大？**\n系统帮你挑出了既能稳定出单，又不会让你亏钱的“神仙词”。\n\n- **如果它已经是精准匹配：** 说明定位很准，建议直接加点竞价或预算，让它跑得更好。\n- **如果它是从自动或广泛广告里跑出来的：** 建议把它单独拿出来，建一个新的“精准广告组”。给它专属的预算去抢占搜索页顶部，同时这么做也不会破坏你原来广告组的节奏。',
        'en': "**How to scale winners safely?**\nWe've isolated terms generating stable orders without burning profit.\n\n- **If already Exact Match:** Increase bids/budget slightly.\n- **If from Auto/Broad/Phrase:** Isolate it into a dedicated Exact Match campaign with dedicated budget. This lets you dominate Top of Search without ruining the algorithm of your original Auto campaign.",
    },
    'tab3_warning': {
        'zh': '⚠️ **A9 迁移规则 (Peel & Stick):** 提取新词时**切勿直接暂停原词**。应先降低原词竞价 (30%-50%)，待新组观察 7-14 天稳定出单后，再否定原词，以免历史权重清零。',
        'en': '⚠️ **A9 Algorithm Rule (Peel & Stick):** When extracting a term, **do not pause the original target immediately**. Lower the original bid by 30-50% first, let the new campaign run for 7-14 days to build history, then negate the original.',
    },
    'tab3_desc': {
        'zh': '高转化且ACoS低于盈亏平衡线的优质词，根据其当前匹配类型执行不同扩量策略。',
        'en': 'High-converting terms with ACoS below break-even. Execute scaling strategies based on their current match type.',
    },
    # ---------------------------------------------------------
    # 9. Excel Sheet Names
    # ---------------------------------------------------------
    'sheet_bleeders': {'zh': '紧急止损 (Bleeders)', 'en': 'Bleeders'},
    'sheet_cannibal': {'zh': '流量内卷 (Cannibalization)', 'en': 'Cannibalization'},
    'sheet_loss': {'zh': '结构亏损 (Loss)', 'en': 'Structural Loss'},
    'sheet_winners': {'zh': '核心扩展 (Winners)', 'en': 'Winners'},
    # ---------------------------------------------------------
    # DataFrame Column Headers
    # ---------------------------------------------------------
    'col_bleeding_reason': {'zh': '诊断原因', 'en': 'Diagnosis Reason'},
    'col_audit_action': {'zh': '操作建议', 'en': 'Action'},
    'col_campaign_name': {'zh': '广告活动', 'en': 'Campaign'},
    'col_ad_group_name': {'zh': '广告组', 'en': 'Ad Group'},
    'col_match_type': {'zh': '匹配类型', 'en': 'Match Type'},
    'col_targeting': {'zh': '投放词/ASIN', 'en': 'Targeting'},
    'col_customer_search_term': {'zh': '客户搜索词', 'en': 'Search Term'},
    'col_clicks': {'zh': '点击量', 'en': 'Clicks'},
    'col_dynamic_click_threshold': {
        'zh': '最大容忍点击数',
        'en': 'Max Tolerated Clicks',
    },  # Renamed & Clarified
    'col_spend': {'zh': '花费', 'en': 'Spend'},
    'col_status': {'zh': '状态', 'en': 'Status'},
    'col_total_spend': {'zh': '总花费', 'en': 'Total Spend'},
    'col_total_sales': {'zh': '总销售额', 'en': 'Total Sales'},
    'col_total_orders': {'zh': '总订单量', 'en': 'Total Orders'},
    'col_realized_acos': {'zh': '实际 ACoS', 'en': 'Actual ACoS'},
    'col_allowable_spend': {'zh': '保本花费上限', 'en': 'Allowable Spend'},
    'col_capital_lost': {'zh': '净利润流失', 'en': 'Capital Lost'},
    'col_orders_7d': {'zh': '7天订单量', 'en': 'Orders (7D)'},
    'col_acos': {'zh': 'ACoS', 'en': 'ACoS'},
    'col_gross_profit': {'zh': '毛利润预估', 'en': 'Est. Gross Profit'},
    'col_consultative_action': {'zh': '诊断建议', 'en': 'Diagnostic Action'},
}


def t(key: str, **kwargs) -> str:
    """
    Retrieves the translated text based on the current session state language.
    Pass kwargs to format dynamic strings (e.g., file sizes).
    """
    lang = st.session_state.get('lang', 'en')

    text_dict = TEXTS.get(key, {})
    raw_text = text_dict.get(lang, key)

    if kwargs:
        return raw_text.format(**kwargs)
    return raw_text
