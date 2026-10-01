"""Two-step portal login; credentials stay in this local process."""

import atexit
import base64
import os
import secrets
import subprocess
import sys
import time
from html.parser import HTMLParser
from threading import Lock
from urllib.parse import urljoin

from datagokr import session
from datagokr.config import load
from datagokr.constants import DATAGOKR_AUTH_URL, DATAGOKR_LOGIN_URL

_pending = None
_lock = Lock()
CHALLENGE_TTL = 300


class _LoginForm(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.fields, self.meta, self.image, self.in_form = {}, {}, '', False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.in_form = attrs.get('id') == 'login-form'
        if tag == 'meta':
            self.meta[attrs.get('name')] = attrs.get('content', '')
        if self.in_form and tag == 'input':
            self.fields[attrs.get('name')] = attrs.get('value', '')
        if self.in_form and tag == 'img' and attrs.get('id') == 'captchaImg':
            self.image = attrs.get('src', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.in_form = False


def _captcha_path():
    return load().session_file.parent / 'captcha.png'


def _show(png):
    # Desktop apps fold tool output, so also pop the image up in the system viewer.
    path = _captcha_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    try:
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', str(path)])
    except OSError:
        pass


def _discard():
    global _pending
    _captcha_path().unlink(missing_ok=True)
    if _pending:
        _pending['client'].close()
        _pending = None


atexit.register(_discard)


def _begin():
    global _pending
    _discard()
    username = os.environ.get('DATAGOKR_PORTAL_ID', '')
    password = os.environ.get('DATAGOKR_PORTAL_PASSWORD', '')
    if not username or not password:
        return dict(authenticated=False, message='확장 설정에 포털 아이디·비밀번호를 입력하세요. '
                    'Set DATAGOKR_PORTAL_ID and DATAGOKR_PORTAL_PASSWORD locally.'), None
    client = session._session('')
    client.trust_env = False
    _pending = dict(client=client)
    page = session.portal_request(client, 'GET', DATAGOKR_LOGIN_URL)
    form = _LoginForm(page.text)
    if (not {'username', 'password', 'captcha'} <= form.fields.keys()
            or not all(form.fields.get(k) for k in ('redirectUrl', 'clientId', '_csrf'))
            or not form.meta.get('_csrf') or not form.image
            or form.meta.get('_csrf_header', '').lower() != 'x-xsrf-token'):
        raise ValueError('포털 로그인 양식 변경')
    session.portal_url(form.fields['redirectUrl'])
    image = session.portal_request(client, 'GET', session.portal_url(urljoin(page.url, form.image)))
    if not image.content.startswith(b'\x89PNG\r\n\x1a\n') or len(image.content) > 256_000:
        raise ValueError('보안문자 이미지 오류')
    _show(image.content)
    challenge = secrets.token_urlsafe(24)
    _pending.update(challenge=challenge, expires=time.monotonic() + CHALLENGE_TTL,
                    form=form, username=username, password=password)
    return dict(authenticated=False, challenge_id=challenge, expires_in=CHALLENGE_TTL,
                message='보안문자 그림이 사용자 화면에 따로 열렸습니다. 사용자가 직접 읽은 글자를 받으세요. '
                '같은 challenge_id와 captcha_answer로 login을 다시 호출하세요. '
                'Ask the user to read the CAPTCHA; do not solve it for them.'), image.content


def _complete(challenge_id, captcha_answer):
    if (not _pending or not challenge_id or not captcha_answer
            or challenge_id != _pending.get('challenge')
            or time.monotonic() >= _pending.get('expires', 0)):
        raise ValueError('보안문자 세션 만료')
    client, form = _pending['client'], _pending['form']
    body = {key: form.fields[key] for key in ('redirectUrl', 'clientId', '_csrf')}
    body.update(username=_pending['username'], captcha=captcha_answer,
                password=base64.b64encode(_pending['password'].encode('latin-1')).decode('ascii'))
    response = session.portal_request(client, 'POST', DATAGOKR_AUTH_URL, json=body,
                                      headers={'X-XSRF-TOKEN': form.meta['_csrf']})
    redirect = response.json().get('redirectUrl')
    if not isinstance(redirect, str) or not redirect:
        raise ValueError('로그인 거부')
    session.portal_request(client, 'GET', session.portal_url(redirect))
    if not session.session_ok(client):
        raise ValueError('포털 세션 확인 실패')
    cookie = '; '.join(f'{c.name}={c.value}' for c in client.cookies
                       if c.domain.lstrip('.') in ('www.data.go.kr', 'data.go.kr')
                       and c.path == '/' and not c.is_expired())
    if not cookie:
        raise ValueError('포털 쿠키 없음')
    with session._session(cookie) as restored:
        if not session.session_ok(restored):
            raise ValueError('저장할 세션 확인 실패')
    session.save_cookie(cookie)
    return dict(authenticated=True, message='포털 로그인 확인 및 세션 저장 완료'), None


def login(challenge_id=None, captcha_answer=None):
    with _lock:
        try:
            if challenge_id is None and captcha_answer is None:
                return _begin()
            return _complete(challenge_id, captcha_answer)
        except Exception:
            _discard()
            return dict(authenticated=False, message='로그인 실패 또는 보안문자 만료. '
                        '설정을 확인하고 인자 없이 login을 호출해 다시 시작하세요. '
                        'Login failed; check settings and start a new challenge.'), None
        finally:
            if challenge_id is not None or captcha_answer is not None:
                _discard()
