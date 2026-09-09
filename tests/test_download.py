import csv
import importlib
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs

import pytest
import requests
from openpyxl import Workbook

from datagokr import remote
from datagokr.constants import (DATAGOKR_DOWNLOAD_INFO_URL, DATAGOKR_DOWNLOAD_URL,
    DATAGOKR_OAS_URL, DATAGOKR_PORTAL_URL, DATAGOKR_STD_COLUMNS_URL, DATAGOKR_STD_DATA_URL)
from datagokr.session import http_session

mod = importlib.import_module('datagokr.download')


def portal_row():
    return dict(id='1', dtype='FILE', access_kind='PORTAL_FILE',
                page_url=f'{DATAGOKR_PORTAL_URL}/1/fileData.do',
                version_keys=['old', 'new'], versions={'old': {'date': '20240101'}, 'new': {'date': '20250101'}})


def attachment(http, body, name='data.csv', length=None):
    http.post(DATAGOKR_DOWNLOAD_INFO_URL, json=dict(status=True, atchFileId='attachment', fileDetailSn='2'))
    headers = {'Content-Disposition': f'attachment; filename="{name}"'}
    if length is not None:
        headers['Content-Length'] = str(length)
    http.get(DATAGOKR_DOWNLOAD_URL, body=body, headers=headers)


def test_attachment_previews_preserve_csv_tsv_xlsx_and_bounds(local_http, monkeypatch, tmp_path):
    monkeypatch.setattr(remote, 'record', Mock(return_value=portal_row()))
    for data, name, expected in (
        ('이름,값\r\n서울,1\r\n부산,2\r\n잘린행,3'.encode('utf-8-sig'), 'data.csv', [['서울', '1'], ['부산', '2']]),
        ('이름,값\r\n서울,1\r\n잘린행,2'.encode('cp949'), 'data.txt', [['서울', '1']]),
        ('이름\t값\n서울\t1\n'.encode(), 'data.tsv', [['서울', '1']]),
    ):
        local_http.reset()
        attachment(local_http, data, name)
        result = mod.preview('1', n=2)
        assert result == dict(columns=['이름', '값'], rows=expected, truncated=True)
        assert len(local_http.calls) == 2
        assert parse_qs(local_http.calls[0].request.body)['publicDataDetailPk'] == ['new']
    local_http.reset()
    data = b'col\nfirst\nsecond\n'
    attachment(local_http, data)
    assert mod.preview('1', max_bytes=11)['rows'] == [['first']]
    book, buffer = Workbook(), BytesIO()
    book.active.append(['이름', '값'])
    book.active.append(['서울', 1])
    book.active.append(['부산', 2])
    book.save(buffer)
    book.close()
    data = buffer.getvalue()
    local_http.reset()
    attachment(local_http, data, 'data.xlsx', len(data))
    assert mod.preview('1', n=1)['rows'] == [['서울', 1]]
    assert mod.preview('1', max_full=10) is None
    local_http.reset()
    attachment(local_http, b'PK\x03\x04', 'data.zip')
    assert mod.preview('1') is None
    local_http.reset()
    local_http.post(DATAGOKR_DOWNLOAD_INFO_URL, body=requests.ConnectionError('fixture-request-error'))
    assert mod.preview('1') is None
    assert list(tmp_path.iterdir()) == []


def test_download_versions_fallbacks_encoding_and_standard_atomic_pages(local_http, tmp_path, monkeypatch):
    row = portal_row()
    monkeypatch.setattr(remote, 'record', Mock(side_effect=lambda *a, **kw: row))
    monkeypatch.setenv('DATAGOKR_DOWNLOAD_DIR', str(tmp_path / 'configured'))
    body = '이름,값\r\n서울,1\r\n'.encode('cp949')
    name = '../한글.csv'.encode().decode('latin1')
    attachment(local_http, body, name)
    saved, = mod.download(1, utf8=True)
    assert saved['version'] == 'new'
    assert Path(saved['path']) == tmp_path / 'configured/1/한글.csv'
    assert Path(saved['path']).read_bytes() == body
    assert Path(saved['utf8_path']).read_text() == '이름,값\n서울,1\n'
    all_files = mod.download('1', all_versions=True, out=tmp_path / 'all')
    assert {Path(item['path']).parent.name for item in all_files} == {'old', 'new'}
    assert mod.download('1', version='old', download_dir=tmp_path / 'override')[0]['version'] == 'old'
    with pytest.raises(ValueError, match='mutually exclusive'):
        mod.download('1', version='old', all_versions=True)
    local_http.reset()
    row.update(versions={}, version_keys=[])
    local_http.get(DATAGOKR_OAS_URL, json={'paths': {'/1/v1/oas': {'get': {'summary': '통계_20260101'}}}})
    attachment(local_http, body)
    assert mod.download('1', probe=True) == [dict(version='oas', probed=True)]
    local_http.reset()
    local_http.get(DATAGOKR_OAS_URL, status=404)
    local_http.get(row['page_url'], body='<input name="publicDataDetailPk" value="first" value="">')
    attachment(local_http, body)
    assert mod.download('1', probe=True) == [dict(version='first', probed=True)]
    local_http.reset()
    row.update(version_keys=['first'])
    local_http.post(DATAGOKR_DOWNLOAD_INFO_URL, json=dict(status=True, atchFileId=None,
        dataSetFileDetailInfo={'dataUrl': 'https://provider.invalid/data'}))
    assert mod.download('1') == [dict(url='https://provider.invalid/data')]
    local_http.reset()
    row['external_url'] = 'https://provider.invalid/data'
    attachment(local_http, b'')
    assert mod.download('1')[0]['message'] == mod.EMPTY_ATTACHMENT_LINK

    local_http.reset()
    row.update(access_kind='STD_FILE')
    columns = dict(tableVO=dict(colNmList=['a', 'b'], svcTableNm='std'), totalCount=3,
                   fileName='../../standard.csv', columList=[dict(columCode='a', columNm='이름'), dict(columCode='b', columNm='값')])
    local_http.get(DATAGOKR_STD_COLUMNS_URL, json=columns)
    local_http.get(DATAGOKR_STD_DATA_URL, json=[{'a': '서울', 'b': 1}, {'a': '부산', 'b': 2}])
    local_http.get(DATAGOKR_STD_DATA_URL, json=[{'a': '제주', 'b': 3}])
    with http_session() as client:
        saved, = mod.download_std(client, '1', per_page=2, download_dir=tmp_path / 'std')
    path = Path(saved['path'])
    assert saved['rows'] == 3
    with path.open(encoding='utf-8-sig', newline='') as handle:
        assert list(csv.reader(handle)) == [['이름', '값'], ['서울', '1'], ['부산', '2'], ['제주', '3']]
    before = path.read_bytes()
    local_http.reset()
    local_http.get(DATAGOKR_STD_COLUMNS_URL, json=columns)
    local_http.get(DATAGOKR_STD_DATA_URL, json=[])
    with http_session() as client, pytest.raises(ValueError, match='premature empty'):
        mod.download_std(client, '1', per_page=2, download_dir=tmp_path / 'std')
    assert path.read_bytes() == before and not path.with_suffix('.csv.part').exists()
