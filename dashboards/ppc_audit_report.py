import os

import pandas as pd
import streamlit as st

from backend.auditor.amazon_ppc_auditor import AmazonPPCAuditor
from backend.schema import AmazonSPSchema, SchemaValidationError
from backend.telemetry import insert_telemetry_row
from ui.audit_dashboard import generate_excel_report, render_audit_dashboard
from ui.i18n import t  # 🚀 IMPORT TRANSLATION ENGINE

# Enforce wide layout
st.set_page_config(
    page_title='SP PPC Auditor | Alpha',
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

# --- Page View Tracking (Fires exactly once per session) ---
if 'page_view_fired' not in st.session_state:
    insert_telemetry_row('PAGE_VIEW')
    st.session_state.page_view_fired = True

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# -------------------------------------------------------------
# 🌐 GLOBAL UI: Language Toggle (Always Visible)
# -------------------------------------------------------------
with st.sidebar:
    lang_choice = st.radio(
        t('lang_selector'),
        ['English', '中文'],
        horizontal=True,
        index=0 if st.session_state.get('lang', 'en') == 'en' else 1,
    )

    # State check to instantly repaint UI
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
        # Streamlit file uploader returns an in-memory buffer
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)

        # 1. Gatekeeper normalization
        clean_df = AmazonSPSchema.validate_and_normalize(raw_df)

        # ---------------------------------------------------------
        # 🚨 Temporal Data Validation & Warning
        # ---------------------------------------------------------
        report_start = clean_df['start_date'].min()
        report_end = clean_df['end_date'].max()
        report_days = (report_end - report_start).days

        if report_days < 14:
            st.warning(t('temporal_warning', days=report_days))
        else:
            st.info(t('temporal_success', days=report_days))

        # 2. Math engine processing
        auditor = AmazonPPCAuditor(clean_df)

        # 3. Excel report generator
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

        # 4. Render Main UI (Feedback has been moved inside here)
        render_audit_dashboard(auditor, global_margin=global_margin_float)

    except SchemaValidationError as e:
        st.error(t('schema_error', error=str(e)))
        st.info(t('upload_checklist'))

else:
    # LANDING PAGE RENDERED DYNAMICALLY
    st.title(t('main_title'))
    st.write(t('main_subtitle'))

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.markdown(t('landing_col1'))
    c2.markdown(t('landing_col2'))
    c3.markdown(t('landing_col3'))

    st.info(t('upload_instruction'))
