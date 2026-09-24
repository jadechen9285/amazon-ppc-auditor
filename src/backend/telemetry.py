import uuid
from datetime import UTC, datetime

import requests
import streamlit as st


def insert_telemetry_row(event_type: str, sentiment: int = None, details: str = ''):
    """
    Atomic HTTP POST to Supabase.
    event_type: 'PAGE_VIEW', 'USAGE_METRIC', 'SCHEMA_ERROR', 'FEEDBACK'
    """

    # 🚨 THE FIX: Blanket exception catch for missing local secrets file
    try:
        supabase_url = st.secrets['SUPABASE_URL']
        supabase_key = st.secrets['SUPABASE_KEY']
    except Exception:
        # Failsafe for local dev: If secrets are missing, silently abort telemetry
        # so the main PPC auditing app can still run.
        return

    if not supabase_url or not supabase_key:
        return  # Failsafe for local dev without secrets

    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }

    # Attach a session ID to track unique users without requiring login
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    payload = {
        'created_at': datetime.now(UTC).isoformat(),
        'event_type': event_type,
        'sentiment': sentiment,
        'details': f'[Session: {st.session_state.session_id}] {details}',
    }

    endpoint = f'{supabase_url}/rest/v1/app_telemetry'

    try:
        requests.post(endpoint, headers=headers, json=payload, timeout=2.0)
    except Exception:
        pass  # Protect the main thread at all costs
