import io

import pandas as pd
from conftest import make_clean_df, make_row

from backend.auditor.amazon_ppc_auditor import AmazonPPCAuditor
from ui.audit_dashboard import generate_excel_report


def read_workbook(data: bytes) -> dict[str, pd.DataFrame]:
    return pd.read_excel(io.BytesIO(data), sheet_name=None)


def test_full_report_contains_every_sheet(sample_report):
    # Add a loss-making campaign so the structural loss sheet is populated
    report = pd.concat(
        [
            sample_report,
            make_clean_df([make_row('loss term', campaign='Loss', spend=60.0)], anchor=False),
        ]
    )

    sheets = read_workbook(generate_excel_report(AmazonPPCAuditor(report), global_margin=0.3))

    assert list(sheets) == ['Bleeders', 'Cannibalization', 'Structural Loss', 'Winners']
    bleeders = sheets['Bleeders']
    assert 'Diagnosis Reason' in bleeders.columns
    assert set(bleeders['Search Term']) == {'chronic term', 'fast term', 'loss term'}
    assert 'Loss' in set(sheets['Structural Loss']['Campaign'])


def test_sheet_names_and_headers_are_localized(sample_report, session_state):
    session_state['lang'] = 'zh'

    sheets = read_workbook(generate_excel_report(AmazonPPCAuditor(sample_report), 0.3))

    assert '紧急止损 (Bleeders)' in sheets
    assert '客户搜索词' in sheets['紧急止损 (Bleeders)'].columns


def test_empty_sections_are_skipped():
    df = make_clean_df([make_row('winner', clicks=20, spend=5.0, orders=4, sales=100.0)])

    sheets = read_workbook(generate_excel_report(AmazonPPCAuditor(df), 0.3))

    assert list(sheets) == ['Winners']
