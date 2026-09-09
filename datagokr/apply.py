"""Apply through the portal's HTTP form using the user's saved login."""

import re
import time
from html import unescape

from datagokr import remote
from datagokr.constants import (DATAGOKR_ACCOUNT_URL, DATAGOKR_APPLY_FORM_URL,
    DATAGOKR_APPLY_SAVE_URL, DATAGOKR_PORTAL_URL, DATAGOKR_WEBFILTER_URL)
from datagokr.session import ensure_session, safe_http_errors, LOGIN_REQUIRED

PURPOSE_DEFAULT = '공공데이터 색인·검색 도구 개발 및 통계 분석 연구'
MAX_IDS = 50
_FORM = re.compile(r'<form\b[^>]*id="reqForm"[^>]*>(.*?)</form>', re.I | re.S)
_TAG = re.compile(r'<input\b[^>]*>', re.I)
_ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def parse_hidden_inputs(html):
    """form#reqForm의 hidden input → {name: value}. 같은 속성이 반복되면 브라우저처럼 첫 값을 쓴다."""
    form = _FORM.search(html)
    fields = {}
    for tag in _TAG.findall(form.group(1) if form else html):
        attrs = {}
        for key, value in _ATTR.findall(tag):
            attrs.setdefault(key.lower(), unescape(value))
        if attrs.get('type', '').lower() == 'hidden' and attrs.get('name'):
            fields[attrs['name']] = attrs.get('value', '')
    return fields


@safe_http_errors
def apply_one(session, dataset_id, purpose):
    page_url = f'{DATAGOKR_PORTAL_URL}/{dataset_id}/fileData.do'
    form = session.get(DATAGOKR_APPLY_FORM_URL, params={'publicDataPk': dataset_id, 'isBusinessApply': ''}, timeout=30)
    if form.status_code != 200:
        return {'id': dataset_id, 'status': 'error', 'reason': f'신청 폼 HTTP {form.status_code}', 'page_url': page_url}
    if 'multiCloudApiRequestForm' not in form.url:
        return {'id': dataset_id, 'status': 'not_applicable', 'reason': '활용신청 버튼 없음(LINK형 등) 또는 이미 신청됨', 'page_url': page_url}
    fields = parse_hidden_inputs(form.text)
    if not fields.get('publicDataDetailPk') or fields.get('testStepAtmcConfmAt') != 'Y':
        return {'id': dataset_id, 'status': 'error', 'reason': '신청 폼의 식별자 또는 자동승인 값이 유효하지 않음', 'page_url': page_url}
    check = session.post(DATAGOKR_WEBFILTER_URL, timeout=30,
                         json={'content': purpose, 'board': 'API 개발계정 신청', 'hostUrl': form.url, 'referer': page_url},
                         headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': form.url})
    try:
        if check.status_code != 200 or check.json().get('isBlocked') is not False:
            return {'id': dataset_id, 'status': 'error', 'reason': '웹필터(금칙어)에 걸림', 'page_url': page_url}
    except ValueError:
        return {'id': dataset_id, 'status': 'error', 'reason': f'웹필터 검사 실패 (HTTP {check.status_code})', 'page_url': page_url}
    fields.update({'prcusePrpos': 'PROS03', 'prcusePurps': purpose, 'useScopeAgreAt': 'Y'})
    saved = session.post(DATAGOKR_APPLY_SAVE_URL, data=fields, timeout=30,
                         headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': form.url})
    try:
        result = saved.json()
    except ValueError:
        result = {}
    if saved.status_code == 200 and result.get('result') is True:
        return {'id': dataset_id, 'status': 'applied', 'page_url': page_url}
    return {'id': dataset_id, 'status': 'rejected', 'reason': '이미 신청됨 또는 실패', 'page_url': page_url}


def approval_status(session, ids, *, remote_url=None):
    """Match account approval labels with titles from the remote catalog."""
    titles = {}
    for dataset_id in ids:
        row = remote.record(dataset_id, remote_url=remote_url)
        titles[dataset_id] = row.get('list_title') or row.get('title')
    text = unescape(re.sub(r'<[^>]+>', ' ', session.get(DATAGOKR_ACCOUNT_URL, timeout=30).text))
    status = {}
    for dataset_id, title in titles.items():
        match = re.search(r'\[(승인|신청|보류|반려)\]\s*' + re.escape(title), text) if title else None
        status[dataset_id] = match.group(1) if match else None
    return status


@safe_http_errors
def apply(ids, purpose=PURPOSE_DEFAULT, *, remote_url=None, session_file=None):
    ids = list(dict.fromkeys(str(i) for i in ([ids] if isinstance(ids, (str, int)) else ids)))
    if not ids or len(ids) > MAX_IDS:
        raise ValueError(f'1..{MAX_IDS} dataset ids required')
    try:
        session = ensure_session(session_file=session_file)
    except ConnectionError:
        return [dict(id=i, status='manual', reason=LOGIN_REQUIRED,
                     page_url=f'{DATAGOKR_PORTAL_URL}/{i}/fileData.do') for i in ids]
    results = []
    with session:
        for dataset_id in ids:
            results.append(apply_one(session, dataset_id, purpose))
            time.sleep(1)
        status = approval_status(session, ids, remote_url=remote_url)
    for row in results:
        row['portal_status'] = status.get(row['id'])
    return results
