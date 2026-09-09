import importlib
import json
from unittest.mock import Mock
from urllib.parse import parse_qs

import pytest

from datagokr import remote
from datagokr.constants import (DATAGOKR_ACCOUNT_URL, DATAGOKR_APPLY_FORM_URL,
    DATAGOKR_APPLY_SAVE_URL, DATAGOKR_WEBFILTER_URL)
from datagokr.session import http_session

mod = importlib.import_module('datagokr.apply')
FORM_URL = 'https://www.data.go.kr/iim/api/multiCloudApiRequestForm.do'
FORM = ('<input name="outside" type="hidden" value="ignored"><form id="reqForm">'
        '<input name="publicDataDetailPk" type="hidden" value="uddi:one">'
        '<input name="testStepAtmcConfmAt" value="Y" type="hidden" value="">'
        '<input name="sysTy" value="20" type="hidden" value="">'
        '<input name="token" value="a&amp;b" type="hidden"></form>')


def test_application_http_sequence_approval_guards_and_manual_login(local_http, tmp_path, monkeypatch):
    path = tmp_path / 'session.json'
    path.write_text(json.dumps({'cookie': 'JSESSIONID=fixture-apply'}))
    sleep = Mock()
    monkeypatch.setattr(mod.time, 'sleep', sleep)
    record = Mock(return_value={'list_title': '공공 통계', 'title': '다른 제목'})
    monkeypatch.setattr(remote, 'record', record)
    local_http.get(DATAGOKR_ACCOUNT_URL, body='로그아웃 <b>[승인]</b> 공공 통계')
    local_http.get(DATAGOKR_APPLY_FORM_URL, status=302, headers={'Location': FORM_URL})
    local_http.get(FORM_URL, body=FORM)
    local_http.post(DATAGOKR_WEBFILTER_URL, json={'isBlocked': False})
    local_http.post(DATAGOKR_APPLY_SAVE_URL, json={'result': True, 'key': 'fixture-never-return'})
    result = mod.apply(['1', '1'], purpose='[TEST] 분석', session_file=path, remote_url='https://catalog.invalid/mcp')
    assert len(result) == 1 and result[0]['status'] == 'applied'
    assert result[0]['portal_status'] == '승인' and 'key' not in result[0]
    assert 'fixture-' not in repr(result)
    posts = [c.request for c in local_http.calls if c.request.method == 'POST']
    assert [p.url for p in posts] == [DATAGOKR_WEBFILTER_URL, DATAGOKR_APPLY_SAVE_URL]
    fields = parse_qs(posts[1].body)
    assert fields['testStepAtmcConfmAt'] == ['Y'] and fields['sysTy'] == ['20']
    assert fields['token'] == ['a&b'] and 'outside' not in fields
    assert fields['prcusePurps'] == ['[TEST] 분석'] and fields['useScopeAgreAt'] == ['Y']
    record.assert_called_once_with('1', remote_url='https://catalog.invalid/mcp')
    sleep.assert_called_once_with(1)

    for markup, blocked, save, expected, count in (
        (FORM.replace('value="Y"', 'value=""'), False, True, 'error', 0),
        (FORM, True, True, 'error', 1),
        (FORM, False, False, 'rejected', 2),
    ):
        local_http.reset()
        local_http.get(DATAGOKR_APPLY_FORM_URL, status=302, headers={'Location': FORM_URL})
        local_http.get(FORM_URL, body=markup)
        if count:
            local_http.post(DATAGOKR_WEBFILTER_URL, json={'isBlocked': blocked})
        if count == 2:
            local_http.post(DATAGOKR_APPLY_SAVE_URL, json={'result': save})
        with http_session() as client:
            assert mod.apply_one(client, '1', '[TEST] 목적')['status'] == expected
        assert sum(c.request.method == 'POST' for c in local_http.calls) == count
    path.unlink()
    manual = mod.apply('1', session_file=path)
    assert manual[0]['status'] == 'manual' and 'datagokr login' in manual[0]['reason']
    for ids in ([], list(range(51))):
        with pytest.raises(ValueError, match='dataset ids'):
            mod.apply(ids)
