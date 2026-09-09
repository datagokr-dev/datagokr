import csv
import re
from html import unescape
import zipfile
from io import BytesIO, StringIO
from itertools import islice
from contextlib import closing
from email import message_from_string
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from datagokr.constants import DATAGOKR_DOWNLOAD_INFO_URL, DATAGOKR_DOWNLOAD_URL, DATAGOKR_OAS_URL, DATAGOKR_PORTAL_URL, DATAGOKR_STD_COLUMNS_URL, DATAGOKR_STD_DATA_URL
import requests
from datagokr.session import http_session, safe_http_errors
from datagokr import remote
from datagokr.config import load
from datagokr.access import external_url

EMPTY_ATTACHMENT = '포털이 등록한 첨부파일이 0바이트다 — 포털 측 결함이고 요청은 정상이다'
DELISTED = '포털이 이 데이터셋 상세 페이지를 내렸다(404) — 카탈로그에만 남은 항목이고 요청은 정상이다'
EMPTY_ATTACHMENT_LINK = '포털 첨부파일이 0바이트라 제공기관 원본 페이지로 안내한다 (포털 측 결함)'


class PortalDefect(RuntimeError):
    """The portal cannot supply the registered attachment."""


def institution_url(row, info):
    """The portal keeps the provider's own page even when its attachment is empty."""
    url = (info.get('dataSetFileDetailInfo') or {}).get('dataUrl') or None
    if not url:
        try:
            url = external_url(row)
        except (ValueError, KeyError, TypeError, OSError, requests.RequestException):
            url = None
    return url


class _DetailKey(HTMLParser):
    key = None

    def handle_starttag(self, tag, pairs):
        if tag != 'input' or self.key is not None:
            return
        attrs = {}
        for name, value in pairs:
            attrs.setdefault(name, value)
        if attrs.get('id') == 'publicDataDetailPk' or attrs.get('name') == 'publicDataDetailPk':
            self.key = attrs.get('value', '')


def download_std(session, dataset_id, out=None, per_page=10000, *, download_dir=None):
    meta, codes, names = std_columns(session, dataset_id)
    names = [names[code] for code in codes]
    filename = Path(meta['fileName'].replace('\\', '/')).name
    path = (Path(out).expanduser() if out else load(download_dir=download_dir).download_dir / dataset_id) / (filename.removesuffix('.csv') + '.csv')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary, count = path.with_suffix('.csv.part'), 0
    try:
        with temporary.open('w', encoding='utf-8-sig', newline='') as target:
            writer = csv.writer(target)
            writer.writerow(names)
            for page in range(1, (meta['totalCount'] + per_page - 1) // per_page + 1):
                rows = std_page(session, dataset_id, meta, codes, page, per_page)
                writer.writerows(rows)
                count += len(rows)
        if count != meta['totalCount']:
            raise ValueError('STD_FILE row count changed during download; retry')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return [dict(path=str(path), rows=count, columns=names)]


def _file_info(session, dataset_id, row, version=None, all_versions=False, portal_only=False):
    versions = dict.fromkeys(row.get('version_keys') or [], {}) | (row.get('versions') or {})
    if not versions and not version:
        if not portal_only:  # 미리보기는 상세 페이지 직행으로 최대 세 요청을 지킨다.
            response = session.get(DATAGOKR_OAS_URL, params={'namespace': f'{dataset_id}/v1'}, timeout=(10, 60))
            if response.status_code != 404:
                response.raise_for_status(); _, versions = parse_file_oas(response.json())
        if not versions:
            response = session.get(f'{DATAGOKR_PORTAL_URL}/{dataset_id}/fileData.do', timeout=(10, 60))
            if response.status_code == 404:
                raise PortalDefect(DELISTED)
            response.raise_for_status()
            parser = _DetailKey(); parser.feed(response.text)
            if parser.key:
                versions = {parser.key: {}}
    selected = list(versions) if all_versions else [version or max(versions, key=lambda v: versions[v].get('date') or '', default=None)]
    if not selected or selected == [None]: raise ValueError('no FILE versions available')
    for key in selected:
        response = session.post(DATAGOKR_DOWNLOAD_INFO_URL, data=dict(publicDataPk=dataset_id, publicDataDetailPk=key, fileDetailSn=1, publicDataTyCode='PR0051'), timeout=(10, 60))
        response.raise_for_status(); yield key, response.json()


def _file_response(session, info, stream=False):
    return session.get(DATAGOKR_DOWNLOAD_URL, params=dict(atchFileId=info['atchFileId'], fileDetailSn=info['fileDetailSn'], insertDataPrcus='N'), timeout=(10, 60), **({'stream': True} if stream else {}))


def preview(dataset_id, n=5, max_bytes=262144, max_full=5_000_000, *, remote_url=None) -> dict | None:
    """Read the first n attachment rows without a key or disk writes."""
    try:
        dataset_id = str(dataset_id)
        row = remote.record(dataset_id, remote_url=remote_url)
        if row['access_kind'] != 'PORTAL_FILE' or min(n, max_bytes, max_full) < 1: return None
        with http_session(allowed_methods=('GET', 'POST')) as session:
            session.max_redirects = 0
            for adapter in session.adapters.values(): adapter.max_retries = adapter.max_retries.new(total=0)
            _, info = next(_file_info(session, dataset_id, row, portal_only=True))
            if not info['status'] or not info.get('atchFileId'): return None
            with closing(_file_response(session, info, True)) as response:
                response.raise_for_status()
                header = message_from_string('Content-Disposition: ' + response.headers.get('Content-Disposition', ''))
                ext = Path(unquote(header.get_filename() or '')).suffix.lower()
                if ext not in ('.csv', '.txt', '.tsv', '.xlsx'): return None
                limit = int(response.headers.get('Content-Length', 0)) if ext == '.xlsx' else max_bytes
                if ext == '.xlsx' and not 0 < limit <= max_full: return None
                body = response.raw.read(limit, decode_content=True)
            if ext == '.xlsx':
                try: from openpyxl import load_workbook
                except ImportError: return None
                with closing(load_workbook(BytesIO(body), read_only=True, data_only=True)) as book:
                    rows = list(islice(book.worksheets[0].values, n + 1))
            else:
                body = body.rsplit(b'\n', 1)[0] if b'\n' in body else b''
                try: text = body.decode('utf-8-sig')
                except UnicodeDecodeError: text = body.decode('cp949')
                rows = list(islice(csv.reader(StringIO(text, newline=''), delimiter='\t' if ext == '.tsv' else ',', strict=True), n + 1))
            return dict(columns=list(rows[0]), rows=[list(row) for row in rows[1:]], truncated=True) if rows else None
    except PortalDefect:
        raise
    except (ValueError, KeyError, csv.Error, UnicodeDecodeError, requests.RequestException, ConnectionError, zipfile.BadZipFile):
        return None


@safe_http_errors
def download(dataset_id: str, version: str | None = None, all_versions: bool = False, out: str | None = None, utf8: bool = False, probe: bool = False, *, remote_url=None, download_dir=None) -> list[dict]:
    dataset_id = str(dataset_id)
    row, files = remote.record(dataset_id, remote_url=remote_url), []
    if row['dtype'] != 'FILE': raise ValueError('download requires FILE data')
    if version and all_versions: raise ValueError('--version and --all-versions are mutually exclusive')
    if row['access_kind'] == 'LINK': return [{'url': row['external_url']}]
    if row['access_kind'] == 'STD_FILE':
        with http_session() as session:
            if probe:
                meta, codes, _ = std_columns(session, dataset_id)
                return [dict(rows=std_page(session, dataset_id, meta, codes, 1, 2))]
            return download_std(session, dataset_id, out, download_dir=download_dir)
    with http_session(allowed_methods=('GET', 'POST')) as session:
        for key, info in _file_info(session, dataset_id, row, version, all_versions):
            if not info['status']:
                if not probe: files.append(info)
                continue
            if not info.get('atchFileId'):
                # Some FILE catalog entries are now institution-hosted links.
                url = institution_url(row, info)
                if not url:
                    raise PortalDefect(DELISTED)
                files.append(dict(url=url))
                continue
            response = _file_response(session, info, probe)
            if probe:
                try:
                    response.raise_for_status()
                    empty = (not response.headers.get('Content-Disposition')
                             or not next(response.iter_content(chunk_size=1024), b''))
                finally:
                    response.close()
                if not empty:
                    files.append(dict(version=key, probed=True))
                    continue
                url = institution_url(row, info)
                if not url:
                    raise PortalDefect(EMPTY_ATTACHMENT)
                files.append(dict(version=key, url=url, message=EMPTY_ATTACHMENT_LINK))
                continue
            response.raise_for_status()
            if not response.headers.get('Content-Disposition') or not response.content:
                url = institution_url(row, info)
                if not url: raise PortalDefect(EMPTY_ATTACHMENT)
                files.append(dict(version=key, url=url, message=EMPTY_ATTACHMENT_LINK)); continue
            header = message_from_string('Content-Disposition: ' + response.headers['Content-Disposition'].encode('latin1').decode('utf-8'))
            path = (Path(out).expanduser() if out else load(download_dir=download_dir).download_dir / dataset_id) / (Path(str(key)).name if all_versions else '') / Path(unquote(header.get_filename()).replace('\\', '/')).name
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(response.content)
            files.append(dict(version=key, path=str(path)))
            if utf8 and path.suffix.lower() == '.csv':
                try: text = response.content.decode('utf-8-sig')
                except UnicodeDecodeError: text = response.content.decode('cp949')
                converted = path.with_suffix('.utf8.csv'); converted.write_text(text, encoding='utf-8'); files[-1]['utf8_path'] = str(converted)
    return files


def parse_file_oas(document):
    """Keep callable version IDs, including models without an exposed GET path."""
    fields, versions = [], {}
    for path, methods in document.get('paths', {}).items():
        if 'get' in methods:
            summary = methods['get'].get('summary', '')
            date = re.search(r'(\d{4}(?:[-.]?\d{2}){0,2})\s*$', summary)
            versions[path.rsplit('/', 1)[-1]] = {
                'path': path, 'summary': summary, 'date': date[1] if date else None}
    for model, definition in document.get('definitions', {}).items():
        if model.endswith('_model'):
            version = model.removesuffix('_model')
            for pos, (name, prop) in enumerate(definition.get('properties', {}).items(), 1):
                fields.append(('file_oas', version, 'column', pos, name, None, prop.get('type')))
    return fields, versions


def parse_api_meta(html, operation_seq=None):
    """Only labelled service/request URLs identify callable API addresses."""
    urls = {}
    for label, body in re.findall(r'<strong\b[^>]*>\s*(서비스\s*URL|요청주소)\s*</strong>'
                                 r'\s*<div\b[^>]*>(.*?)</div>', html, re.S | re.I):
        match = re.search(r'https?://[^\s<>"\']+', unescape(body))
        if match:
            urls.setdefault(''.join(label.split()), []).append(match[0].rstrip('/'))
    endpoint = next(iter(urls.get('서비스URL', [])), None)
    requests_ = list(dict.fromkeys(urls.get('요청주소', [])))
    if not endpoint and requests_:
        endpoint = requests_[0].rsplit('/', 1)[0]
    if not endpoint:
        return {}
    return dict(api_endpoint=endpoint, operations=[dict(
        operation_seq=str(operation_seq or ''), operation_url=url[len(endpoint):])
        for url in requests_ if url.startswith(endpoint + '/')])


def std_api_meta(session, dataset):
    response = get_response(session, dataset.get('page_url') or
                            f"{DATAGOKR_PORTAL_URL}/{dataset['id']}/standard.do")
    response.raise_for_status()
    meta = parse_api_meta(response.text)
    if not re.match(r'https?://apis\.data\.go\.kr/', meta.get('api_endpoint', '')):
        return {}
    return dict(meta, file=False)


def get_response(session, url, **kwargs):
    response = session.get(url, timeout=(10, 60), **kwargs)
    if response.status_code != 404:
        response.raise_for_status()
    response.encoding = 'utf-8'
    return response


def std_columns(session, dataset_id):
    response = get_response(session, DATAGOKR_STD_COLUMNS_URL, params=dict(pk=dataset_id, ext='CSV'))
    response.raise_for_status()
    document = response.json()
    codes = document['tableVO']['colNmList']
    names = {c['columCode']: c['columNm'] for c in document['columList']}
    meta = dict(svcTableNm=document['tableVO']['svcTableNm'],
                totalCount=int(document['totalCount']), fileName=document['fileName'])
    return meta, codes, names


def std_page(session, dataset_id, meta, codes, page, per_page):
    params = dict(publicDataPk=dataset_id, totalCount=meta['totalCount'],
                  svcTableNm=meta['svcTableNm'], perPage=per_page, page=page, colNmList=codes)
    response = get_response(session, DATAGOKR_STD_DATA_URL, params=params)
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or (not rows and (page - 1) * per_page < meta['totalCount']):
        raise ValueError('invalid or premature empty STD_FILE page')
    return [[row.get(code) for code in codes] for row in rows]
