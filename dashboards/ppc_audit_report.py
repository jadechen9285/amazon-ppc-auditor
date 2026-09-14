import pandas as pd
import streamlit as st
from ui.audit_dashboard import render_audit_dashboard
from backend.auditor.amazon_ppc_auditor import AmazonPPCAuditor

# 1. ENFORCE WIDE LAYOUT (Must be the first st command)
st.set_page_config(page_title="PPC Auditor", layout="wide", initial_sidebar_state="expanded")

# --- Dev Bypass ---
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = True
    st.session_state["name"] = "Jianhong (Dev)"

if st.session_state.get("authentication_status"):
    # 2. MOVE CONTROLS TO SIDEBAR
    with st.sidebar:
        st.write(f"### 欢迎回来, *{st.session_state['name']}*")
        st.divider()

        # --- Injecting the Aesthetic Financial Control ---
        st.subheader("⚙️ 财务配置 (Financial Settings)")
        
        # We use whole numbers (10 to 80) for UX, but convert to float (0.10 to 0.80) for the backend
        global_margin_pct = st.slider(
            "🎯 盈亏平衡 ACoS (Break-even Margin)", 
            min_value=10, 
            max_value=80, 
            value=30, 
            step=1,
            help="您的产品净毛利率。当实际 ACoS 超过此数值时，广告即产生绝对亏损。"
        )
        global_margin_float = global_margin_pct / 100.0
        
        st.divider()

        ## 
        uploaded_file = st.file_uploader("📥 上传搜索词报告", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)
            
        df_clean = raw_df # Replace with your actual cleaner
        
        auditor = AmazonPPCAuditor(df_clean)
        render_audit_dashboard(auditor, global_margin=global_margin_float)
        
    else:
        # Use the wide main canvas to show a beautiful placeholder
        st.title("📊 亚马逊 PPC 深度审计报告")
        st.info("👈 请在左侧边栏上传您的广告报表以生成审计看板。")
else:
    st.error("🔒 访问被拒绝。请先登录。")