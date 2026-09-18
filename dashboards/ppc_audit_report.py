import pandas as pd
import streamlit as st

from backend.auditor.amazon_ppc_auditor import AmazonPPCAuditor
from backend.schema import AmazonSPSchema, SchemaValidationError
from ui.audit_dashboard import generate_excel_report, render_audit_dashboard

# 1. ENFORCE WIDE LAYOUT (Must be the first st command)
st.set_page_config(page_title='PPC Auditor', layout='wide', initial_sidebar_state='expanded')

# --- Dev Bypass ---
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = True
    st.session_state['name'] = 'Jianhong (Dev)'

if st.session_state.get('authentication_status'):
    # 2. MOVE CONTROLS TO SIDEBAR
    with st.sidebar:
        st.write(f'### 欢迎回来, *{st.session_state["name"]}*')
        st.divider()

        # --- Injecting the Aesthetic Financial Control ---
        st.subheader('⚙️ 财务配置 (Financial Settings)')

        # We use whole numbers (10 to 80) for UX, but convert to float (0.10 to 0.80) for the backend
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

        ##
        uploaded_file = st.file_uploader('📥 上传搜索词报告', type=['xlsx', 'csv'])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                raw_df = pd.read_csv(uploaded_file)
            else:
                raw_df = pd.read_excel(uploaded_file)

            clean_df = AmazonSPSchema.validate_and_normalize(raw_df)

            auditor = AmazonPPCAuditor(clean_df)

            excel_data = generate_excel_report(auditor, global_margin_float)

            st.sidebar.divider()
            st.sidebar.download_button(
                label='📥 导出完整审计报告 (Export Excel)',
                data=excel_data,
                file_name='Amazon_PPC_Audit_Report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True,
            )

            render_audit_dashboard(auditor, global_margin=global_margin_float)

        except SchemaValidationError as e:
            # Graceful, layman-friendly UI failure
            st.error(f'❌ **报表格式错误 (Format Error):** {str(e)}')
            st.info(
                '💡 **排查指南:**\n'
                '1. 请确保您上传的是 **SP 搜索词报告 (Sponsored Products Search Term Report)**，而不是 Sponsored Brands (SB) 或其他报告。\n'
                '2. 请确保您下载报表后没有手动删除任何列。\n'
                '3. 当前系统仅支持**中文语言**的亚马逊后台报表。'
            )
            st.stop()  # Immediately halts Streamlit execution cleanly

        except Exception:
            # Catch-all for catastrophic Pandas failures (e.g., completely corrupted file)
            st.error('🚨 **文件读取失败:** 请确保上传的是标准的 Excel 或 CSV 文件。')
            st.stop()

    else:
        # Use the wide main canvas to show a beautiful placeholder
        st.title('📊 亚马逊 PPC 深度审计报告')
        st.info('👈 请在左侧边栏上传您的广告报表以生成审计看板。')
else:
    st.error('🔒 访问被拒绝。请先登录。')
