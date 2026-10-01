import asyncio
import base64
import json
import stat
import traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from fastmcp import Client

from datagokr import portal_login as login, session
from datagokr.constants import DATAGOKR_ACCOUNT_URL, DATAGOKR_AUTH_URL, DATAGOKR_LOGIN_URL
from datagokr.mcp import mcp

AUTH_PAGE = 'https://auth.data.go.kr/sso/common-login'
CAPTCHA = 'https://auth.data.go.kr/captcha'
CALLBACK = 'https://www.data.go.kr/sso/profile.do'
FORM = f'''<meta name="_csrf" content="fixture-meta-token">
<meta name="_csrf_header" content="X-XSRF-TOKEN"><form id="login-form">
<input name="redirectUrl" value="{CALLBACK}"><input name="clientId" value="fixture-client">
<input name="_csrf" value="fixture-hidden-token"><input name="username">
<input name="password"><input name="captcha"><img id="captchaImg" src="/captcha"></form>'''
PNG = (Path(__file__).resolve().parents[1] / 'icon.png').read_bytes()


@pytest.fixture
def portal(local_http, monkeypatch, tmp_path):
    login._discard()
    monkeypatch.setenv('DATAGOKR_PORTAL_ID', 'fixture-user')
    monkeypatch.setenv('DATAGOKR_PORTAL_PASSWORD', 'páss-fixture')
    path = tmp_path / 'session.json'
    monkeypatch.setenv('DATAGOKR_SESSION_FILE', str(path))
    yield local_http, path
    login._discard()


def start(http, form=FORM, png=PNG):
    http.get(DATAGOKR_LOGIN_URL, status=302, headers={'Location': AUTH_PAGE})
    http.get(AUTH_PAGE, body=form, headers={'Set-Cookie': 'SSO_COOKIE=fixture-auth; Path=/; Secure; HttpOnly'})
    if form == FORM:
        http.get(CAPTCHA, body=png, content_type='image/png')
    return login.login()


def finish(http, **kwargs):
    http.post(DATAGOKR_AUTH_URL, json={'redirectUrl': CALLBACK}, **kwargs)
    http.get(CALLBACK, status=302, headers={'Location': '/index.do',
             'Set-Cookie': 'JSESSIONID=fixture-www; Path=/; Secure; HttpOnly'})
    http.get('https://www.data.go.kr/index.do', body='[TEST] callback')
    http.get(DATAGOKR_ACCOUNT_URL, body='로그아웃')


def test_missing_credentials_make_no_requests(portal, monkeypatch):
    http, path = portal
    monkeypatch.delenv('DATAGOKR_PORTAL_ID')
    result, image = login.login()
    assert not result['authenticated'] and '확장 설정' in result['message']
    assert image is None and not http.calls and not path.exists()
    assert login._pending is None


def test_same_session_submission_sso_validation_and_reuse(portal):
    http, path = portal
    result, image = start(http)
    assert image == PNG and result['expires_in'] == 300
    finish(http)
    done, image = login.login(result['challenge_id'], 'user-read-answer')
    assert done['authenticated'] and image is None and login._pending is None
    post = next(call.request for call in http.calls if call.request.method == 'POST')
    assert post.url == DATAGOKR_AUTH_URL
    assert post.headers['X-XSRF-TOKEN'] == 'fixture-meta-token'
    assert 'SSO_COOKIE=fixture-auth' in post.headers['Cookie']
    assert json.loads(post.body) == dict(username='fixture-user', captcha='user-read-answer',
        password=base64.b64encode('páss-fixture'.encode('latin-1')).decode(),
        redirectUrl=CALLBACK, clientId='fixture-client', _csrf='fixture-hidden-token')
    assert json.loads(path.read_text())['cookie'] == 'JSESSIONID=fixture-www'
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert session.login_status()['authenticated']
    with session.ensure_session() as restored:
        assert restored.cookies.get('JSESSIONID') == 'fixture-www'
    assert 'fixture' not in json.dumps(result) + json.dumps(done)
    assert all('fixture-user' not in call.request.url for call in http.calls)


def test_failures_are_masked_consumed_and_never_retried(portal, caplog, capsys):
    http, path = portal
    for response in ({'json': {'error': 'fixture-user páss-fixture'}},
                     {'body': 'fixture-user páss-fixture', 'status': 403},
                     {'body': requests.ConnectionError('páss-fixture')},
                     {'json': {'redirectUrl': 'https://evil.invalid/fixture-user'}},
                     {'status': 307, 'headers': {'Location': DATAGOKR_AUTH_URL}}):
        http.reset()
        result, _ = start(http)
        http.post(DATAGOKR_AUTH_URL, **response)
        done, image = login.login(result['challenge_id'], 'answer')
        assert not done['authenticated'] and image is None
        assert sum(c.request.method == 'POST' for c in http.calls) == 1
        assert not path.exists() and login._pending is None
        assert 'fixture' not in json.dumps(done)
        login.login(result['challenge_id'], 'answer')
        assert sum(c.request.method == 'POST' for c in http.calls) == 1
    assert 'páss-fixture' not in caplog.text + capsys.readouterr().err


def test_old_mismatched_expired_and_restarted_challenges(portal, monkeypatch):
    http, _ = portal
    first, _ = start(http)
    close = Mock(wraps=login._pending['client'].close)
    monkeypatch.setattr(login._pending['client'], 'close', close)
    second, _ = login.login()
    assert first['challenge_id'] != second['challenge_id']
    close.assert_called_once()
    assert not login.login(first['challenge_id'], 'answer')[0]['authenticated']
    current, _ = login.login()
    clock = login.time.monotonic
    monkeypatch.setattr(login.time, 'monotonic', lambda: login._pending['expires'] + 1)
    assert not login.login(current['challenge_id'], 'answer')[0]['authenticated']
    monkeypatch.setattr(login.time, 'monotonic', clock)
    login._discard()
    assert not login.login(second['challenge_id'], 'answer')[0]['authenticated']
    assert not any(c.request.method == 'POST' for c in http.calls)


def test_redirects_are_checked_before_the_next_request(portal):
    http, _ = portal
    for target in ('http://www.data.go.kr/', 'https://evil.invalid/',
                   'https://www.data.go.kr.evil.invalid/', 'https://user@www.data.go.kr/',
                   'https://www.data.go.kr:8443/'):
        http.reset()
        http.get(DATAGOKR_LOGIN_URL, status=302, headers={'Location': target})
        assert not login.login()[0]['authenticated']
        assert len(http.calls) == 1
    http.reset()
    http.get(DATAGOKR_LOGIN_URL, status=302, headers={'Location': DATAGOKR_LOGIN_URL})
    assert not login.login()[0]['authenticated']
    assert len(http.calls) == 6 and login._pending is None


def test_invalid_forms_images_and_password_encoding(portal, monkeypatch):
    http, path = portal
    for form in (FORM.replace('name="clientId"', 'name="wrong"'),
                 FORM.replace('X-XSRF-TOKEN', 'X-Credential'),
                 FORM.replace(CALLBACK, 'https://evil.invalid/')):
        http.reset()
        assert not start(http, form=form)[0]['authenticated']
        assert len(http.calls) == 2 and login._pending is None
    http.reset()
    assert not start(http, png=b'not an image')[0]['authenticated']
    assert login._pending is None
    http.reset()
    monkeypatch.setenv('DATAGOKR_PORTAL_PASSWORD', '한글-fixture')
    result, _ = start(http)
    assert not login.login(result['challenge_id'], 'answer')[0]['authenticated']
    assert not any(c.request.method == 'POST' for c in http.calls) and not path.exists()


def test_auth_success_without_valid_portal_session_is_failure(portal):
    http, path = portal
    for account in ('로그인', '로그아웃'):
        http.reset()
        result, _ = start(http)
        http.post(DATAGOKR_AUTH_URL, json={'redirectUrl': CALLBACK})
        http.get(CALLBACK, body='[TEST] callback without portal cookie')
        http.get(DATAGOKR_ACCOUNT_URL, body=account)
        assert not login.login(result['challenge_id'], 'answer')[0]['authenticated']
        assert not path.exists() and login._pending is None


def test_windows_credential_storage_without_fchmod(portal, monkeypatch):
    http, path = portal
    store = Mock()
    store.get_password.return_value = 'JSESSIONID=fixture-win'
    monkeypatch.setattr(session, 'sys', SimpleNamespace(platform='win32'))
    monkeypatch.setattr(session, '_windows_store', lambda: store)
    monkeypatch.delattr(session.os, 'fchmod')
    http.get(DATAGOKR_ACCOUNT_URL, body='로그아웃')
    assert session.login('JSESSIONID=fixture-win')['authenticated']
    assert json.loads(path.read_text())['keyring'] is True
    assert 'fixture-win' not in path.read_text()
    store.set_password.assert_called_once_with('datagokr', str(path.resolve()), 'JSESSIONID=fixture-win')
    assert session.login_status()['authenticated']
    store.get_password.assert_called_once_with('datagokr', str(path.resolve()))
    store.set_password.side_effect = RuntimeError('fixture-win')
    cookie = 'JSESSIONID=fixture-win'
    with pytest.raises(ConnectionError) as error:
        session.login(cookie)
    assert 'fixture-win' not in ''.join(traceback.format_exception(error.value))


def test_mcp_image_and_manifest_configuration_contract(portal):
    http, _ = portal
    manifest = json.loads((Path(__file__).resolve().parents[1] / 'manifest.json').read_text())
    env = manifest['server']['mcp_config']['env']
    assert env == {f'DATAGOKR_{key}': '${user_config.' + field + '}' for key, field in
                   (('API_KEY', 'api_key'), ('PORTAL_ID', 'portal_id'), ('PORTAL_PASSWORD', 'portal_password'))}
    assert all(v['sensitive'] and not v['required'] for v in manifest['user_config'].values())
    assert manifest['server']['type'] == 'uv' and manifest['server']['entry_point'] == 'server.py'
    assert set(manifest['compatibility']['platforms']) >= {'win32', 'darwin'}
    start(http)
    finish(http)

    async def scenario():
        async with Client(mcp) as client:
            result = await client.call_tool('login')
            assert result.data['challenge_id']
            image = next(c for c in result.content if c.type == 'image')
            assert image.mimeType == 'image/png' and base64.b64decode(image.data) == PNG
            assert 'fixture' not in ''.join(c.text for c in result.content if c.type == 'text')
            completed = await client.call_tool('login', dict(challenge_id=result.data['challenge_id'],
                                                            captcha_answer='user-read-answer'))
            assert completed.data['authenticated']
            assert all(c.type == 'text' for c in completed.content)

    asyncio.run(scenario())
