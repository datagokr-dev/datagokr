"""User-owned portal cookies and credential-safe HTTP sessions."""

import json
import logging
import os
import time
from functools import wraps
from urllib.parse import urlparse

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
    response = session.get(DATAGOKR_ACCOUNT_URL, timeout=30)
    return (response.status_code == 200 and urlparse(response.url).hostname == 'www.data.go.kr'
            and '로그아웃' in response.text)


def ensure_session(*, session_file=None):
    path = load(session_file=session_file).session_file
    try:
        cached = json.loads(path.read_text(encoding='utf-8')).get('cookie', '')
        if not isinstance(cached, str) or not cached:
            raise ValueError()
    except (OSError, ValueError, AttributeError):
        raise ConnectionError(LOGIN_REQUIRED) from None
    session = _session(cached)
    try:
        if session_ok(session):
            path.chmod(0o600)
            return session
    except (requests.RequestException, ConnectionError, OSError):
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
        path = load(session_file=session_file).session_file
        path.parent.mkdir(parents=True, exist_ok=True)
        # Permissions are restrictive before the first credential byte is written.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as target:
            os.fchmod(target.fileno(), 0o600)
            json.dump(dict(cookie=cookie, saved_at=time.time()), target)
    except (OSError, ValueError, requests.RequestException):
        raise ConnectionError('로그인 확인 또는 세션 저장 실패. datagokr login 으로 다시 시도하세요.') from None
    return dict(authenticated=True, message='포털 로그인 확인 및 세션 저장 완료')


def login_status(*, session_file=None):
    try:
        with ensure_session(session_file=session_file):
            return dict(authenticated=True, message='포털 로그인 유효')
    except ConnectionError:
        return dict(authenticated=False, message=LOGIN_REQUIRED)
