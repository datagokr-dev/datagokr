import traceback
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest
import requests

import datagokr
from datagokr import remote
from datagokr.constants import DATAGOKR_DATA_URL


def test_local_fetch_versions_key_precedence_401_templates_and_safe_errors(local_http, monkeypatch, caplog, capsys):
    row = dict(id='1', dtype='FILE', access_kind='PORTAL_FILE', page_url='https://portal.invalid/1',
               version_keys=['old', 'new'], versions={'old': {'date': '20240101'}, 'new': {'date': '20250101'}})
    metadata = Mock(side_effect=lambda *a, **kw: row)
    monkeypatch.setattr(remote, 'record', metadata)
    monkeypatch.setenv('DATAGOKR_API_KEY', 'fixture-environment')
    url = f'{DATAGOKR_DATA_URL}/1/v1/new'
    local_http.get(url, json={'data': [{'x': 1}], 'totalCount': 1})
    assert datagokr.fetch(1, n=2, api_key='fixture-explicit')['data'] == [{'x': 1}]
    query = parse_qs(urlsplit(local_http.calls[-1].request.url).query)
    assert query == dict(page=['1'], perPage=['2'], serviceKey=['fixture-explicit'])
    metadata.assert_called_once_with('1', remote_url=None)
    with pytest.raises(ValueError, match='version'):
        datagokr.fetch('1', version='missing')
    with pytest.raises(ValueError, match='DATAGOKR_API_KEY'):
        datagokr.fetch('1', api_key='')
    local_http.reset()
    local_http.get(url, status=401)
    assert datagokr.fetch('1')['status_code'] == 401
    row['versions'] = {}
    local_http.get(f'{DATAGOKR_DATA_URL}/1/v1/old', json={'data': []})
    assert datagokr.fetch('1', version='old') == {'data': []}
    for body, status in ((requests.ConnectionError('fixture-sensitive-url'), 200), ('invalid', 200), ('busy', 500)):
        local_http.reset()
        local_http.get(f'{DATAGOKR_DATA_URL}/1/v1/old', body=body, status=status)
        with pytest.raises(RuntimeError) as error:
            datagokr.fetch('1', version='old')
        rendered = ''.join(traceback.format_exception(error.value))
        assert 'fixture-sensitive-url' not in rendered
        assert 'fixture-environment' not in rendered + caplog.text + capsys.readouterr().err
    row.update(access_kind='OPEN_API', examples=[{'url': 'https://api.invalid/list'}])
    assert datagokr.fetch('1')['request_templates'] == row['examples']
    row['access_kind'] = 'STD_FILE'
    with pytest.raises(ValueError, match='STD_FILE'):
        datagokr.fetch('1')
