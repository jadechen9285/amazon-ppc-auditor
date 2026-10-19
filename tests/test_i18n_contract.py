import pytest

from ui.contract import UIContract
from ui.i18n import TEXTS, t


def test_defaults_to_english():
    assert t('alpha_button') == 'Enter System'


def test_returns_chinese_when_selected(session_state):
    session_state['lang'] = 'zh'

    assert t('alpha_button') == '进入系统'


def test_unknown_key_falls_back_to_key():
    assert t('does_not_exist') == 'does_not_exist'


def test_formats_kwargs():
    TEXTS['_test_template'] = {'en': '{size:.1f} MB', 'zh': '{size:.1f} 兆'}
    try:
        assert t('_test_template', size=12.345) == '12.3 MB'
    finally:
        del TEXTS['_test_template']


@pytest.mark.parametrize('key', sorted(TEXTS))
def test_every_text_has_both_languages(key):
    assert set(TEXTS[key]) >= {'en', 'zh'}


def test_excel_map_has_translation_for_every_column(session_state):
    for lang in ('en', 'zh'):
        session_state['lang'] = lang
        excel_map = UIContract.get_excel_map()

        for column, label in excel_map.items():
            assert label != f'col_{column}', f'missing {lang} label for {column}'


def test_get_label_routes_through_col_prefix():
    assert UIContract.get_label('spend') == 'Spend'
