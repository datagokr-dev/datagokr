import json
import stat
import sys
import traceback
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from datagokr import session
from datagokr.constants import DATAGOKR_ACCOUNT_URL


def test_cookie_login_validation_permissions_expiry_and_secret_errors(local_http, tmp_path, monkeypatch, caplog, capsys):
    path = tmp_path / 'sessions' / 'portal.json'
    cookie = 'JSESSIONID=fixture-session;second=fixture-other=='
    local_http.get(DATAGOKR_ACCOUNT_URL, body='로그아웃')
    dump = json.dump

    def private_dump(value, stream):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        return dump(value, stream)

    monkeypatch.setattr(session.json, 'dump', private_dump)
    result = session.login(cookie, session_file=path)
    assert result['authenticated'] and 'cookie' not in result
    assert json.loads(path.read_text())['cookie'] == cookie
    path.chmod(0o644)
    with session.ensure_session(session_file=path) as logged_in:
        assert logged_in.cookies.get('second') == 'fixture-other=='
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert session.login_status(session_file=path)['authenticated']

    local_http.reset()
    local_http.get(DATAGOKR_ACCOUNT_URL, body='로그인')
    assert not session.login_status(session_file=path)['authenticated']
    for invoke in (lambda: session.ensure_session(session_file=path),
                   lambda: session.login(cookie, session_file=path)):
        with pytest.raises(ConnectionError, match='datagokr login'):
            invoke()
    local_http.reset()
    local_http.get(DATAGOKR_ACCOUNT_URL, body=requests.ConnectionError(cookie))
    with pytest.raises(ConnectionError) as error:
        session.login(cookie, session_file=path)
    rendered = ''.join(traceback.format_exception(error.value))
    assert 'fixture-session' not in rendered + caplog.text + capsys.readouterr().err
    assert error.value.__suppress_context__
    path.write_text('{malformed')
    assert not session.login_status(session_file=path)['authenticated']


def test_browser_cookie_import_filter_and_guidance(local_http, tmp_path, monkeypatch):
    assert 'document.cookie' in session.login()['message']
    assert DATAGOKR_ACCOUNT_URL in session.login_instructions()
    monkeypatch.setitem(sys.modules, 'browser_cookie3', None)
    with pytest.raises(ConnectionError, match=r'datagokr\[browser\]'):
        session.login(browser='chrome')
    jar = requests.cookies.RequestsCookieJar()
    jar.set('JSESSIONID', 'fixture-browser', domain='.data.go.kr', path='/')
    jar.set('unrelated', 'fixture-unrelated', domain='example.invalid', path='/')
    reader = Mock(return_value=jar)
    monkeypatch.setitem(sys.modules, 'browser_cookie3', SimpleNamespace(chrome=reader))
    local_http.get(DATAGOKR_ACCOUNT_URL, body='로그아웃')
    path = tmp_path / 'browser.json'
    assert session.login(browser='chrome', session_file=path)['authenticated']
    reader.assert_called_once_with(domain_name='data.go.kr')
    assert 'unrelated' not in path.read_text()
    reader.side_effect = RuntimeError('fixture-browser')
    with pytest.raises(ConnectionError) as error:
        session.login(browser='chrome')
    assert 'fixture-browser' not in ''.join(traceback.format_exception(error.value))
    with pytest.raises(ValueError, match='함께'):
        session.login(cookie='unused', browser='chrome')
    with pytest.raises(ValueError, match='브라우저'):
        session.browser_cookie('unknown')
