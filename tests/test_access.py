import importlib
import traceback
from unittest.mock import Mock

import pytest

import datagokr
from datagokr import remote
from datagokr.constants import (DATAGOKR_DATA_URL, DATAGOKR_DOWNLOAD_INFO_URL,
    DATAGOKR_DOWNLOAD_URL, DATAGOKR_STD_COLUMNS_URL, DATAGOKR_STD_DATA_URL)

apply_mod = importlib.import_module('datagokr.apply')
fetch_mod = importlib.import_module('datagokr.fetch')
download_mod = importlib.import_module('datagokr.download')


def test_get_401_apply_retry_attachment_fallback_and_no_apply(local_http, monkeypatch, tmp_path):
    row = dict(id='1', dtype='FILE', access_kind='PORTAL_FILE', page_url='https://portal.invalid/1',
               version_keys=['v'], versions={'v': {'date': '20260909'}})
    metadata = Mock(return_value=row)
    monkeypatch.setattr(remote, 'record', metadata)
    application = Mock(return_value=[dict(id='1', status='applied', portal_status='승인', key='fixture-hidden')])
    monkeypatch.setattr(apply_mod, 'apply', application)
    url = f'{DATAGOKR_DATA_URL}/1/v1/v'
    local_http.get(url, status=401)
    local_http.get(url, json={'data': [{'name': '서울'}]})
    result = datagokr.get('1', api_key='fixture-user', session_file=tmp_path / 'login.json')
    assert result['data'] == {'data': [{'name': '서울'}]}
    assert result['application'] == [dict(id='1', status='applied', portal_status='승인')]
    assert 'fixture-hidden' not in repr(result)
    application.assert_called_once_with(['1'], remote_url=None, session_file=tmp_path / 'login.json')
    assert len(local_http.calls) == 2

    local_http.reset()
    local_http.get(url, status=401)
    local_http.post(DATAGOKR_DOWNLOAD_INFO_URL, json=dict(status=True, atchFileId='attachment', fileDetailSn=1))
    local_http.get(DATAGOKR_DOWNLOAD_URL, body='name\n서울\n'.encode(),
                   headers={'Content-Disposition': 'attachment; filename="data.csv"'})
    application.reset_mock()
    result = datagokr.get('1', api_key='fixture-user')
    assert result['data']['rows'] == [['서울']] and '반영 대기' in result['message']
    assert sum(c.request.url.startswith(url) for c in local_http.calls) == 2
    assert result['download_hint'] == 'datagokr download 1'

    local_http.reset()
    local_http.get(url, status=401)
    local_http.post(DATAGOKR_DOWNLOAD_INFO_URL, json=dict(status=True, atchFileId='attachment', fileDetailSn=1))
    local_http.get(DATAGOKR_DOWNLOAD_URL, body=b'PK\x03\x04',
                   headers={'Content-Disposition': 'attachment; filename="data.zip"'})
    application.reset_mock()
    result = datagokr.get('1', api_key='fixture-user', no_apply=True, download_dir=tmp_path / 'downloads')
    assert result['files'][0]['path'] == str(tmp_path / 'downloads/1/data.zip')
    assert sum(c.request.url.startswith(url) for c in local_http.calls) == 1
    application.assert_not_called()

    # Explicit empty key bypasses fetch and login, even with a configured key.
    local_http.reset()
    local_http.post(DATAGOKR_DOWNLOAD_INFO_URL, json=dict(status=True, atchFileId='attachment', fileDetailSn=1))
    local_http.get(DATAGOKR_DOWNLOAD_URL, body=b'name\nseoul\n',
                   headers={'Content-Disposition': 'attachment; filename="data.csv"'})
    monkeypatch.setenv('DATAGOKR_API_KEY', 'fixture-environment')
    fetch = Mock(side_effect=AssertionError('[TEST] fetch must be bypassed'))
    monkeypatch.setattr(fetch_mod, 'fetch', fetch)
    assert datagokr.get('1', api_key='')['data']['rows'] == [['seoul']]
    fetch.assert_not_called()
    application.assert_not_called()
    assert all('api.odcloud.kr' not in call.request.url for call in local_http.calls)

    # A failed login does not submit or repeat the API call, and probe never applies.
    local_http.reset()
    fetch.side_effect = None
    fetch.return_value = dict(status_code=401, message='신청 필요')
    application.return_value = [dict(id='1', status='manual', reason='datagokr login')]
    monkeypatch.setattr(download_mod, 'preview', Mock(return_value=None))
    download = Mock(return_value=[dict(url='https://provider.invalid', message=download_mod.EMPTY_ATTACHMENT_LINK)])
    monkeypatch.setattr(download_mod, 'download', download)
    assert datagokr.get('1')['message'] == download_mod.EMPTY_ATTACHMENT_LINK
    assert fetch.call_count == 1
    application.reset_mock()
    assert datagokr.get('1', probe=True)['files']
    application.assert_not_called()
    download.assert_called_with('1', probe=True, remote_url=None, download_dir=None)


def test_get_standard_parent_links_api_templates_and_404_api_only(local_http, monkeypatch):
    parent = dict(id='parent', dtype='FILE', access_kind='STD_FILE', std_meta={}, page_url='https://portal.invalid/standard')
    child = dict(id='child', dtype='STD', access_kind='STD', parent_id='parent')
    rows = dict(parent=parent, child=child)
    monkeypatch.setattr(remote, 'record', Mock(side_effect=lambda ident, **kw: rows[ident]))
    columns = dict(tableVO=dict(colNmList=['city'], svcTableNm='std'), totalCount=1,
                   fileName='std.csv', columList=[dict(columCode='city', columNm='시군구명')])
    local_http.get(DATAGOKR_STD_COLUMNS_URL, json=columns)
    local_http.get(DATAGOKR_STD_DATA_URL, json=[{'city': '강릉시'}])
    result = datagokr.get('child')
    assert result['id'] == 'child' and result['parent_id'] == 'parent'
    assert result['data'] == dict(columns=['시군구명'], rows=[['강릉시']])
    assert result['total'] == 1
    child['parent_id'] = 'child'
    assert datagokr.get('child')['catalog'] == child
    child['parent_id'] = 'parent'
    rows['parent'] = dict(access_kind='STD')
    assert datagokr.get('child')['catalog'] == child
    rows['link'] = dict(access_kind='LINK', external_url='https://provider.invalid/data')
    assert datagokr.get('link')['url'] == 'https://provider.invalid/data'
    rows['api'] = dict(access_kind='OPEN_API', page_url='https://portal.invalid/api',
        examples=[dict(url='https://api.invalid/list', params=['serviceKey'])],
        api_sample=dict(request={'pageNo': '1'}, response={'name': '서울'}))
    result = datagokr.get('api')
    assert result['sample_url'] == 'https://api.invalid/list?serviceKey=발급키&pageNo=1'
    assert result['api_sample']['response'] == {'name': '서울'}
    assert 'serviceKey' in result['message']
    rows['api']['examples'] = []
    assert datagokr.get('api')['url'] == rows['api']['page_url']

    rows['parent'] = parent
    local_http.reset()
    local_http.get(DATAGOKR_STD_COLUMNS_URL, status=404)
    local_http.get(parent['page_url'], body='<strong>서비스 URL</strong><div>https://apis.data.go.kr/service</div>'
                   '<strong>요청주소</strong><div>https://apis.data.go.kr/service/list</div>')
    result = datagokr.get('parent')
    assert result['request_templates'][0]['url'] == 'https://apis.data.go.kr/service/list'
    assert result['message'] == '파일 없음 — 오픈API 전용 표준, 활용신청 필요'
    local_http.reset()
    parent['std_meta'] = dict(file=False, api_endpoint='https://apis.data.go.kr/service', operations=[])
    assert datagokr.get('parent')['request_templates'][0]['url'] == 'https://apis.data.go.kr/service/'
    assert not local_http.calls
    with pytest.raises(ValueError, match='positive'):
        datagokr.get('parent', n=0)
    parent['std_meta'] = {}
    target = 'https://portal.invalid/failure?serviceKey=fixture-never-expose'
    local_http.get(DATAGOKR_STD_COLUMNS_URL, status=302, headers={'Location': target})
    local_http.get(target, status=500)
    with pytest.raises(ConnectionError) as error:
        datagokr.get('parent')
    assert 'fixture-never-expose' not in ''.join(traceback.format_exception(error.value))
