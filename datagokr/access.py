import re
from html import unescape
from urllib.parse import urljoin, urlparse

import requests
from datagokr.session import http_session, safe_http_errors
from datagokr import remote
from datagokr.config import load


def external_url(row):
    if row.get('external_url'):
        return row['external_url']
    with http_session() as session:
        page = session.get(row['page_url'], timeout=(10, 60))
        page.raise_for_status()
        link = re.search(r'>\s*URL\s*</(?:strong|th|dt)>\s*<(?:div|td|dd)[^>]*>\s*<a\b[^>]*href=[\"\']([^\"\']+)', page.text)
        url = unescape(link[1]) if link else None
        if not url and re.search(r'fn_goUrlLink\([\"\']' + re.escape(row['id']) + r'[\"\']\)', page.text):
            response = session.get(urljoin(row['page_url'], '/tcs/dss/selectApiLinkUrl.do'),
                                   params={'publicDataPk': row['id']}, timeout=(10, 60))
            response.raise_for_status()
            info = response.json()
            url = info.get('linkUrl') if info.get('status') is True else None
    if not url or urlparse(url).scheme not in ('http', 'https') or not urlparse(url).hostname:
        raise ValueError('LINK external URL missing from portal page')
    return url


def sample_url(template, sample):
    """A copy-pasteable call: the portal's own sample values minus the key you must supply."""
    params = '&'.join(f'{k}={v}' for k, v in (sample.get('request') or {}).items()
                      if k.lower() not in ('servicekey', 'authkey'))
    url = template.get('url') or template.get('operation') or ''
    return f"{url}?serviceKey=발급키&{params}" if url and params else None


@safe_http_errors
def get(dataset_id: str, n: int = 5, no_apply: bool = False, probe: bool = False, *,
        api_key=None, remote_url=None, download_dir=None, session_file=None) -> dict:
    if n < 1:
        raise ValueError('n must be positive')
    return _get(str(dataset_id), 2 if probe else n, no_apply or probe, probe,
                api_key=api_key, remote_url=remote_url, download_dir=download_dir,
                session_file=session_file)


def _get(dataset_id, n, no_apply, probe, row=None, *, api_key=None, remote_url=None,
         download_dir=None, session_file=None):
    from datagokr.fetch import fetch
    from datagokr.apply import apply
    from datagokr.download import download, preview as file_preview, std_api_meta, std_columns, std_page
    row = remote.record(dataset_id, remote_url=remote_url) if row is None else row
    result = dict(id=dataset_id, access_kind=row['access_kind'])
    if row['access_kind'] == 'STD_FILE':
        if n < 1:
            raise ValueError('n must be positive')
        with http_session() as session:
            meta = row.get('std_meta') or {}
            if meta.get('file') is not False:
                try:
                    meta, codes, names = std_columns(session, dataset_id)
                except requests.HTTPError as exc:
                    if exc.response is None or exc.response.status_code != 404:
                        raise
                    meta = std_api_meta(session, row)
                    if not meta:
                        raise
            if meta.get('file') is False:
                return dict(result, request_templates=[dict(endpoint=meta['api_endpoint'],
                    url=urljoin(meta['api_endpoint'].rstrip('/') + '/', op['operation_url'].lstrip('/')),
                    params=['serviceKey']) for op in meta['operations'] or [{'operation_url': ''}]],
                    message='파일 없음 — 오픈API 전용 표준, 활용신청 필요')
            names = [names[code] for code in codes]
            rows = std_page(session, dataset_id, meta, codes, 1, n)[:n]
        return dict(result, data=dict(columns=names, rows=rows), total=meta['totalCount'],
                    **({'message': '포털 측 본문 0행'} if meta['totalCount'] == 0 else {}),
                    download_hint=f'datagokr download {dataset_id}')
    if row['access_kind'] == 'STD':
        parent_id = row.get('parent_id')
        if parent_id and parent_id != dataset_id:
            try:
                parent_id = str(parent_id)
                parent = remote.record(parent_id, remote_url=remote_url)
            except (ValueError, remote.RemoteError):
                parent = None
            if parent and parent['access_kind'] == 'STD_FILE':
                return dict(_get(parent_id, n, no_apply, probe, parent, api_key=api_key,
                                 remote_url=remote_url, download_dir=download_dir, session_file=session_file), id=dataset_id,
                            parent_id=parent_id,
                            message='지자체 하위행 — 본문은 전국판(부모)에 포함, 시도명/시군구명 컬럼으로 필터')
        return dict(result, catalog=row)
    if row['access_kind'] == 'LINK':
        result['url'] = row.get('external_url') or row['page_url']
        return result
    if row['access_kind'] == 'OPEN_API':
        sample = row.get('api_sample') or {}
        if not any(t.get('url') for t in row['examples']):
            return dict(result, url=row['page_url'], **({'api_sample': sample} if sample else {}),
                        message='포털이 API 엔드포인트를 제공하지 않아 상세 페이지로 안내')
        call = sample_url(row['examples'][0], sample) if sample else None
        return dict(result, request_templates=row['examples'], page_url=row['page_url'],
                    **({'api_sample': sample} if sample else {}),
                    **({'sample_url': call} if call else {}),
                    message=f'본인 serviceKey로 호출; 미승인 시 활용신청: datagokr apply {dataset_id}')
    try:
        key = load(api_key=api_key).api_key
        preview = (fetch(dataset_id, n=n, api_key=key, remote_url=remote_url) if key else
                   dict(status_code=401, message='인증키 없이 포털 원문 파일로 확인합니다.'))
        if key and preview.get('status_code') == 401 and not no_apply:
            result['application'] = [{k: v for k, v in item.items() if k != 'key'}
                                     for item in apply([dataset_id], remote_url=remote_url, session_file=session_file)]
            if any(a.get('status') == 'applied' or a.get('portal_status') == '승인'
                   for a in result['application']):
                preview = fetch(dataset_id, n=n, api_key=key, remote_url=remote_url)
        if preview.get('status_code') != 401:
            return dict(result, data=preview)
        applied = any(a.get('status') == 'applied' for a in result.get('application', []))
        result['message'] = ('포털 승인은 났지만 odcloud 인증키 반영 대기 중(실측: 수 시간 걸릴 수 있음) — 원문 다운로드로 대체'
                             if applied else preview['message'])
    except (ValueError, RuntimeError, requests.RequestException, ConnectionError):
        result['message'] = '미리보기를 가져올 수 없어 포털 원문 파일로 확인합니다.'
    if not probe and (data := file_preview(dataset_id, n, remote_url=remote_url)) is not None:
        return dict(result, data=data, download_hint=f'datagokr download {dataset_id}')
    files = download(dataset_id, probe=probe, remote_url=remote_url, download_dir=download_dir)
    # A file that explains itself outranks the stale "apply first" line, or the caller
    # reads the summary and never sees that the portal, not the key, is the problem.
    explained = next((f['message'] for f in files if f.get('message') and not f.get('path')), None)
    return dict(result, files=files, **({'message': explained} if explained else {}))
