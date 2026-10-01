"""User-owned portal cookies and credential-safe HTTP sessions."""

import json
import logging
import os
import sys
import time
from functools import wraps
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from datagokr.config import load
from datagokr.constants import DATAGOKR_ACCOUNT_URL

LOGIN_REQUIRED = '포털 세션이 없거나 만료됐습니다. datagokr login 으로 다시 로그인하세요.'


def safe_http_errors(function):
    """Public operations must not expose credential-bearing exception URLs."""
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except requests.RequestException:
            raise ConnectionError('포털 요청 실패; 잠시 후 다시 시도하세요.') from None
    return guarded


class _PortalSession(requests.Session):
    def request(self, *args, **kwargs):
        try:
            return super().request(*args, **kwargs)
        except requests.RequestException:
            raise ConnectionError('포털 연결 실패; 잠시 후 다시 시도하세요.') from None


def http_session(allowed_methods=('GET',)):
    logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)
    session = _PortalSession()
    session.headers['User-Agent'] = 'datagokr/1.0 (public-data catalog index)'
    retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 503),
                  allowed_methods=allowed_methods, raise_on_status=False)
    for scheme in ('http://', 'https://'):
        session.mount(scheme, HTTPAdapter(max_retries=retry))
    return session


def _session(cookie):
    session = _PortalSession()
    session.headers.update({'User-Agent': 'Mozilla/5.0 datagokr/1.0', 'Referer': 'https://www.data.go.kr/'})
    for item in cookie.split(';'):
        if '=' in item:
            name, value = item.strip().split('=', 1)
            session.cookies.set(name, value, domain='www.data.go.kr', path='/')
    return session


def session_ok(session):
    response = portal_request(session, 'GET', DATAGOKR_ACCOUNT_URL)
    return (response.status_code == 200 and urlparse(response.url).hostname == 'www.data.go.kr'
            and '로그아웃' in response.text)


def portal_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname not in ('www.data.go.kr', 'auth.data.go.kr')
            or parsed.port not in (None, 443) or parsed.username or parsed.password):
        raise ValueError('공식 포털 HTTPS 주소만 허용합니다.')
    return url


def portal_request(client, method, url, **kwargs):
    for _ in range(6):
        response = client.request(method, portal_url(url), allow_redirects=False, timeout=30, **kwargs)
        if not response.is_redirect:
            response.raise_for_status()
            return response
        if method != 'GET':
            raise ValueError('로그인 제출 리다이렉트는 허용하지 않습니다.')
        url = urljoin(url, response.headers['Location'])
    raise ValueError('포털 리다이렉트가 너무 많습니다.')


def _windows_store():
    from keyring.backends.Windows import WinVaultKeyring
    return WinVaultKeyring()


def save_cookie(cookie, *, session_file=None):
    path = load(session_file=session_file).session_file
    payload = dict(cookie=cookie, saved_at=time.time())
    if sys.platform == 'win32':
        _windows_store().set_password('datagokr', str(path.resolve()), cookie)
        payload = dict(keyring=True, saved_at=time.time())
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as target:
        if sys.platform != 'win32':
            os.fchmod(target.fileno(), 0o600)
        json.dump(payload, target)


def ensure_session(*, session_file=None):
    path = load(session_file=session_file).session_file
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        cached = (_windows_store().get_password('datagokr', str(path.resolve()))
                  if payload.get('keyring') else payload.get('cookie', ''))
        if not isinstance(cached, str) or not cached:
            raise ValueError()
    except Exception:
        raise ConnectionError(LOGIN_REQUIRED) from None
    session = _session(cached)
    try:
        if session_ok(session):
            if sys.platform != 'win32':
                path.chmod(0o600)
            return session
    except (requests.RequestException, ConnectionError, OSError, ValueError):
        pass
    session.close()
    raise ConnectionError(LOGIN_REQUIRED) from None


def browser_cookie(browser):
    if browser not in ('chrome', 'safari', 'firefox'):
        raise ValueError('지원 브라우저: chrome, safari, firefox')
    try:
        import browser_cookie3
    except ImportError:
        raise ConnectionError('브라우저 쿠키 지원 설치: pip install "datagokr[browser]"') from None
    try:
        cookies = getattr(browser_cookie3, browser)(domain_name='data.go.kr')
        return '; '.join(f'{c.name}={c.value}' for c in cookies
                         if c.domain.lstrip('.') in ('www.data.go.kr', 'data.go.kr'))
    except Exception:
        raise ConnectionError('브라우저 쿠키를 읽을 수 없습니다. datagokr login --cookie 로 다시 시도하세요.') from None


def login_instructions():
    return (f'브라우저에서 {DATAGOKR_ACCOUNT_URL} 를 열어 로그인하고 보안문자를 직접 입력하세요.\n'
            '로그인 후 www.data.go.kr 페이지 개발자도구 콘솔에서 document.cookie 를 복사하세요.\n'
            'datagokr login --cookie "복사한 쿠키" 또는 datagokr login --browser chrome|safari|firefox\n'
            '쿠키는 로그인 권한입니다. 다른 사람에게 공유하지 마세요.')


def login(cookie=None, browser=None, *, session_file=None):
    if cookie is not None and browser is not None:
        raise ValueError('--cookie 와 --browser 는 함께 사용할 수 없습니다.')
    if cookie is None and browser is None:
        return dict(authenticated=False, message=login_instructions())
    cookie = browser_cookie(browser) if browser else cookie
    if not isinstance(cookie, str) or not cookie.strip():
        raise ConnectionError(LOGIN_REQUIRED)
    try:
        with _session(cookie) as session:
            if not session_ok(session):
                raise ConnectionError(LOGIN_REQUIRED)
        save_cookie(cookie, session_file=session_file)
    except Exception:
        raise ConnectionError('로그인 확인 또는 세션 저장 실패. datagokr login 으로 다시 시도하세요.') from None
    return dict(authenticated=True, message='포털 로그인 확인 및 세션 저장 완료')


def login_status(*, session_file=None):
    try:
        with ensure_session(session_file=session_file):
            return dict(authenticated=True, message='포털 로그인 유효')
    except ConnectionError:
        return dict(authenticated=False, message=LOGIN_REQUIRED)
