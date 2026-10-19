import os
import pandas as pd
import streamlit as st

from backend.auditor.amazon_ppc_auditor import AmazonPPCAuditor
from backend.schema import AmazonSPSchema, SchemaValidationError
from backend.telemetry import insert_telemetry_row
from ui.audit_dashboard import generate_excel_report, render_audit_dashboard
from ui.i18n import t  

# Enforce wide layout
st.set_page_config(
    page_title='Amazon PPC Auditor | Alpha',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

# Custom CSS to hide Streamlit watermarks and tighten header padding
st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Page View Tracking ---
if 'page_view_fired' not in st.session_state:
    insert_telemetry_row('PAGE_VIEW')
    st.session_state.page_view_fired = True

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# -------------------------------------------------------------
# 🌐 GLOBAL UI: Language Toggle 
# -------------------------------------------------------------
with st.sidebar:
    lang_choice = st.radio(
        t('lang_selector'),
        ['English', '中文'],
        horizontal=True,
        index=0 if st.session_state.get('lang', 'en') == 'en' else 1
    )
    
    new_lang = 'en' if lang_choice == 'English' else 'zh'
    if st.session_state.get('lang') != new_lang:
        st.session_state['lang'] = new_lang
        st.rerun()

# -------------------------------------------------------------
# 🛡️ ALPHA ACCESS GATEKEEPER
# -------------------------------------------------------------
ALPHA_ACCESS_KEY = os.environ.get('ALPHA_INVITE_CODE', 'SELLER2026')
MAX_FILE_SIZE_MB = 15.0
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

if not st.session_state['authenticated']:
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.write(t('alpha_title'))
        st.caption(t('alpha_caption'))
        st.info(t('alpha_info'))

        invite_code = st.text_input(t('alpha_input'), type='password')
        if st.button(t('alpha_button'), use_container_width=True):
            if invite_code.strip() == ALPHA_ACCESS_KEY:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error(t('alpha_error'))
    st.stop()  

# -------------------------------------------------------------
# 🚀 AUTHENTICATED APP WORKFLOW
# -------------------------------------------------------------
with st.sidebar:
    st.write(t('financial_setup'))
    global_margin_pct = st.slider(
        t('margin_label'),
        min_value=10,
        max_value=80,
        value=30,
        step=1,
        help=t('margin_help'),
    )
    global_margin_float = global_margin_pct / 100.0

    st.divider()
    uploaded_file = st.file_uploader(
        t('upload_label'),
        type=['xlsx', 'csv'],
        help=t('upload_help', max_size=MAX_FILE_SIZE_MB),
    )

if uploaded_file is not None:
    # 🚨 THE CIRCUIT BREAKER
    file_size = uploaded_file.size
    if file_size > MAX_FILE_SIZE_BYTES:
        actual_mb = file_size / (1024 * 1024)
        st.error(t('file_too_large', size=actual_mb))
        st.warning(t('file_too_large_warning', max_size=MAX_FILE_SIZE_MB))
        st.stop() 

    try:
        # 🚀 ROBUST DELIMITER SNIFFING
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
            if len(raw_df.columns) == 1:
                uploaded_file.seek(0)
                raw_df = pd.read_csv(uploaded_file, sep='\t|;', engine='python')
        else:
            raw_df = pd.read_excel(uploaded_file)

        # Gatekeeper normalization
        clean_df = AmazonSPSchema.validate_and_normalize(raw_df)

        report_start = clean_df['start_date'].min()
        report_end = clean_df['end_date'].max()
        report_days = (report_end - report_start).days

        if report_days < 14:
            st.warning(t('temporal_warning', days=report_days))
        else:
            st.info(t('temporal_success', days=report_days))

        auditor = AmazonPPCAuditor(clean_df)
        excel_data = generate_excel_report(auditor, global_margin_float)

        st.sidebar.divider()
        export_clicked = st.sidebar.download_button(
            label=t('export_button'),
            data=excel_data,
            file_name='Amazon_SP_PPC_Audit_Report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
        )

        if export_clicked:
            insert_telemetry_row(
                event_type='ACTION_CLICK',
                details=f'Exported Global Excel | Margin: {global_margin_pct}%',
            )

        render_audit_dashboard(auditor, global_margin=global_margin_float)

    except SchemaValidationError as e:
        # 🚀 HEURISTIC ERROR ROUTING
        raw_cols = [str(c).lower() for c in raw_df.columns]
        
        if any('search frequency rank' in c or '搜索频率排名' in c for c in raw_cols):
            st.error('❌ **错误报表类型 (Wrong Report):** 您上传的是【品牌分析 (ABA)】的搜索词报告。')
            st.info('👉 **解决方法:** 请前往【亚马逊广告后台 (Ad Console)】 -> 侧边栏【数据报表】 -> 下载 Sponsored Products 的搜索词报告。')
            
        elif not any('customer search term' in c or '客户搜索词' in c for c in raw_cols):
            st.error('❌ **错误报表类型 (Wrong Report):** 您上传的似乎是【广告活动】或【已推广的商品】报告。')
            st.info('👉 **解决方法:** 创建报表时，请确保“报告类型”下拉菜单选择的是 **搜索词 (Search Term)**。')
            
        elif any('keyword' in c or '关键词' in c for c in raw_cols) and not any('targeting' in c or '投放' in c for c in raw_cols):
            st.error('❌ **不支持的广告架构:** 您上传的是【品牌推广 (Sponsored Brands)】报告。')
            st.info('👉 **解决方法:** 目前 Alpha 系统仅支持 Sponsored Products (SP) 广告架构的审计。')
            
        else:
            st.error(t('schema_error', error=str(e)))
            st.info(t('upload_checklist'))

else:
    # ---------------------------------------------------------
    # 🚀 THE ZERO-DATA STATE: LANDING PAGE & SCHEMA TEMPLATE
    # ---------------------------------------------------------
    st.title(t('main_title'))
    st.write(t('main_subtitle'))

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.markdown(t('landing_col1'))
    c2.markdown(t('landing_col2'))
    c3.markdown(t('landing_col3'))

    st.divider()
    
    # Render the Visual Template Example
    # col_text, col_table = st.columns([1, 2.5])
    
    current_lang = st.session_state.get('lang', 'en')
    
    # with col_text:
    # Inline ternary operators for clean rendering without needing new i18n keys for a fallback view
    st.subheader("📄 数据格式要求" if current_lang == 'zh' else "📄 Required Format")
    st.write(
        "请确保您上传的表格包含右侧示例中的核心列。请勿手动修改亚马逊导出的标准列名。" 
        if current_lang == 'zh' 
        else "Ensure your uploaded file contains the core columns shown in the example. Do not modify the default headers exported by Amazon."
    )
    
    # with col_table:
    # 🚀 BILINGUAL MOCK DATA PIPELINE
    if current_lang == 'zh':
        schema_data = {
            "开始日期": ["2026-09-01", "2026-09-01"],
            "结束日期": ["2026-09-30", "2026-09-30"],
            "广告活动名称": ["SP_Auto_Shoes", "SP_Manual_Shoes"],
            "广告组名称": ["Broad_Match", "Exact_Match"],
            "匹配类型": ["宽泛匹配", "精准匹配"],  # Note: Translated the match types too for extreme accuracy
            "客户搜索词": ["running shoes men", "red running shoes"],
            "点击量": [45, 12],
            "花费": [32.50, 18.20],
            "7天总销售额": [0.00, 145.00]
        }
    else:
        schema_data = {
            "Start Date": ["2026-09-01", "2026-09-01"],
            "End Date": ["2026-09-30", "2026-09-30"],
            "Campaign Name": ["SP_Auto_Shoes", "SP_Manual_Shoes"],
            "Ad Group Name": ["Broad_Match", "Exact_Match"],
            "Match Type": ["BROAD", "EXACT"],
            "Customer Search Term": ["running shoes men", "red running shoes"],
            "Clicks": [45, 12],
            "Spend": [32.50, 18.20],
            "7 Day Total Sales": [0.00, 145.00]
        }
        
    mock_schema_df = pd.DataFrame(schema_data)
    st.dataframe(mock_schema_df, hide_index=True, use_container_width=True)

    st.info(f"💡 {t('upload_instruction')}")