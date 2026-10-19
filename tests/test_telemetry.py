import pytest
import streamlit as st

from backend import telemetry


@pytest.fixture
def posts(monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({'url': url, 'headers': headers, 'json': json, 'timeout': timeout})

    monkeypatch.setattr(telemetry.requests, 'post', fake_post)
    return calls


@pytest.fixture
def secrets(monkeypatch):
    monkeypatch.setattr(
        st, 'secrets', {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_KEY': 'key'}
    )


def test_missing_secrets_skip_network(posts):
    telemetry.insert_telemetry_row('PAGE_VIEW')

    assert posts == []


def test_empty_secrets_skip_network(monkeypatch, posts):
    monkeypatch.setattr(st, 'secrets', {'SUPABASE_URL': '', 'SUPABASE_KEY': ''})

    telemetry.insert_telemetry_row('PAGE_VIEW')

    assert posts == []


@pytest.mark.usefixtures('secrets')
def test_posts_event_with_session_id(posts, session_state):
    telemetry.insert_telemetry_row('FEEDBACK', sentiment=1, details='great')

    assert len(posts) == 1
    call = posts[0]
    assert call['url'] == 'https://example.supabase.co/rest/v1/app_telemetry'
    assert call['headers']['Authorization'] == 'Bearer key'
    assert call['timeout'] == 2.0
    assert call['json']['event_type'] == 'FEEDBACK'
    assert call['json']['sentiment'] == 1
    assert call['json']['details'] == f'[Session: {session_state["session_id"]}] great'


@pytest.mark.usefixtures('secrets')
def test_session_id_is_stable_across_events(posts):
    telemetry.insert_telemetry_row('PAGE_VIEW')
    telemetry.insert_telemetry_row('USAGE_METRIC')

    first, second = (call['json']['details'] for call in posts)
    assert first == second


@pytest.mark.usefixtures('secrets')
def test_network_errors_never_propagate(monkeypatch):
    def failing_post(*args, **kwargs):
        raise ConnectionError('offline')

    monkeypatch.setattr(telemetry.requests, 'post', failing_post)

    telemetry.insert_telemetry_row('PAGE_VIEW')
