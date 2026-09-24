import os

import pandas as pd
import streamlit as st

from backend.auditor.amazon_ppc_auditor import AmazonPPCAuditor
from backend.schema import AmazonSPSchema, SchemaValidationError
from ui.audit_dashboard import generate_excel_report, render_audit_dashboard

# Enforce wide layout
st.set_page_config(
    page_title='SP PPC 智能审计专家 | Alpha',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

# Custom CSS to hide Streamlit watermarks and tighten header padding
st.markdown(
    """
    <style>
        /*
        Removed `header {visibility: hidden;}` to restore the sidebar toggle button.
        Relying on config.toml `toolbarMode = "minimal"` to hide the right-side menus.
        */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    </style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# 🛡️ ALPHA ACCESS GATEKEEPER
# -------------------------------------------------------------
ALPHA_ACCESS_KEY = os.environ.get('ALPHA_INVITE_CODE', 'SELLER2026')
# Define our mathematically calculated safety limit (in Bytes)
MAX_FILE_SIZE_MB = 15.0
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.write('### 🔒 卖家受邀内测通道 (Private Alpha)')
        st.caption('亚马逊 Sponsored Products 广告深度诊断与结构止损系统')
        st.info('👋 本系统目前处于特邀内测阶段。请输入您的专属邀请码开启分析。')

        invite_code = st.text_input('内测邀请码 (Invite Code)', type='password')
        if st.button('进入系统', use_container_width=True):
            if invite_code.strip() == ALPHA_ACCESS_KEY:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error('❌ 邀请码无效，请联系技术顾问获取访问权限。')
    st.stop()


# -------------------------------------------------------------
# 🚀 AUTHENTICATED APP WORKFLOW
# -------------------------------------------------------------
with st.sidebar:
    st.write('### ⚙️ 财务配置 (Financial)')
    global_margin_pct = st.slider(
        '🎯 盈亏平衡 ACoS (Break-even Margin)',
        min_value=10,
        max_value=80,
        value=30,
        step=1,
        help='您的产品净毛利率。当实际 ACoS 超过此数值时，广告即产生绝对亏损。',
    )
    global_margin_float = global_margin_pct / 100.0

    st.divider()
    uploaded_file = st.file_uploader(
        '📥 上传搜索词报告 (Excel / CSV)',
        type=['xlsx', 'csv'],
        help=f'支持中/英文 SP Search Term Report。内测期间限制最大文件为 {MAX_FILE_SIZE_MB}MB。',
    )

if uploaded_file is not None:
    # 🚨 THE CIRCUIT BREAKER
    file_size = uploaded_file.size

    if file_size > MAX_FILE_SIZE_BYTES:
        actual_mb = file_size / (1024 * 1024)
        st.error(f'🛑 **文件过大 ({actual_mb:.1f} MB)**')
        st.warning(
            f'为了保证 Alpha 内测期间服务器的计算稳定性，当前系统最高支持 **{MAX_FILE_SIZE_MB} MB** 的报表。\n\n'
            '**建议解决方案：**\n'
            '1. 在亚马逊后台下载报表时，将时间跨度缩短至 14-30 天。\n'
            '2. 仅保留您想要诊断的核心广告活动，删除无关行后再上传。'
        )
        st.stop()  # Halts execution instantly, protecting server memory

    try:
        # Streamlit file uploader returns an in-memory buffer
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)

        # 1. Gatekeeper normalization
        clean_df = AmazonSPSchema.validate_and_normalize(raw_df)

        # ---------------------------------------------------------
        # 🚨 NEW: Temporal Data Validation & Warning
        # ---------------------------------------------------------
        report_start = clean_df['start_date'].min()
        report_end = clean_df['end_date'].max()
        report_days = (report_end - report_start).days

        if report_days < 14:
            st.warning(
                f'⚠️ **数据周期过短警告 ({report_days} 天):** 您上传的报表时间跨度不足 14 天。 '
                '由于亚马逊广告存在 **7 天归因延迟 (Attribution Lag)**，近几天的点击可能已经产生订单，但尚未显示在报表中。'
                '系统已自动下调时间阈值以强制输出分析结果，但建议您在处理「⏳ 长期不转化」词汇时保持谨慎，避免误杀。'
            )
        else:
            st.info(f'📅 **报表周期:** {report_days} 天 (数据量充足，模型输出置信度高)')

        # 2. Math engine processing
        auditor = AmazonPPCAuditor(clean_df)

        # 3. Excel report generator
        excel_data = generate_excel_report(auditor, global_margin_float)

        st.sidebar.divider()
        st.sidebar.download_button(
            label='📥 导出完整审计报告 (Excel)',
            data=excel_data,
            file_name='Amazon_SP_PPC_Audit_Report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
        )

        # 4. Render UI
        render_audit_dashboard(auditor, global_margin=global_margin_float)

    except SchemaValidationError as e:
        st.error(f'❌ **报表格式验证失败:** {str(e)}')
        st.info(
            '💡 **上传检查清单:**\n'
            '1. 请确认文件属于 **Sponsored Products (SP)** 搜索词报告，而非品牌广告 (SB) 或展示广告 (SD)。\n'
            '2. 报表从亚马逊后台导出后，请勿手动删除或更名数据列。\n'
            '3. 系统原生支持中国站与海外站（中/英双语）原始报表。'
        )
    # except Exception:
    #     st.error('🚨 **系统处理异常:** 无法解析该报表，请确认文件内容未受损。')
else:
    st.title('📊 亚马逊 SP 广告深度审计专家')
    st.write('无需授权店铺 API，本地内存脱敏计算，帮助卖家精准定位无效点击与利润流失点。')

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        '#### 🛑 紧急止损清单\n'
        '精准抓取只消耗不转化的无效词，以及多广告活动内部竞价冲突（自己抬高自己 CPC）的消耗点。'
    )
    c2.markdown(
        '#### 💸 账户架构风险\n'
        '结合您的保本利润率，揪出长期实际 ACoS 严重超标、正在吞噬净利润的结构性亏损广告活动。'
    )
    c3.markdown(
        '#### 🚀 核心扩展机会\n'
        '筛选出出单稳定、ACoS 低于保本线的黄金词，提供安全的词组剥离与精准裂变策略。'
    )

    st.info('👈 请在左侧边栏上传从亚马逊卖家中心导出的搜索词报表开始审计。')
