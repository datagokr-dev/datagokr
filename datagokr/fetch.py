"""Local odcloud calls, copied from the original index fetch path."""

import requests
from datagokr import remote
from datagokr.config import load
from datagokr.constants import DATAGOKR_DATA_URL
from datagokr.session import http_session


def fetch(dataset_id: str, version: str | None = None, n: int = 5, *, api_key=None, remote_url=None) -> dict:
    if n < 1:
        raise ValueError("n must be positive")
    dataset_id = str(dataset_id)
    row = remote.record(dataset_id, remote_url=remote_url)
    if row.get('access_kind') == 'STD_FILE':
        raise ValueError('STD_FILE은 get/download 사용')
    if row['dtype'] != 'FILE' or row.get('access_kind') == 'OPEN_API':
        return {'request_templates': row['examples'], 'page_url': row['page_url']}
    versions = dict.fromkeys(row.get('version_keys') or [], {}) | (row.get('versions') or {})
    version = version or max(versions, key=lambda v: versions[v].get('date') or '', default=None)
    if version not in versions:
        raise ValueError('no such FILE version; check datagokr show or use get/download')
    key = load(api_key=api_key).api_key
    if not key:
        raise ValueError("DATAGOKR_API_KEY is required for fetch; use get/download without a key")
    with http_session() as session:
        try:
            response = session.get(f'{DATAGOKR_DATA_URL}/{dataset_id}/v1/{version}',
                params={'page': 1, 'perPage': n, 'serviceKey': key}, timeout=(10, 60), allow_redirects=False)
            if response.status_code == 401:
                return {'status_code': 401, 'message': f"활용신청 필요: {row['page_url']}"}
            if response.status_code != 200:
                raise RuntimeError(f'fetch HTTP {response.status_code}')
            return response.json()
        except (requests.RequestException, ConnectionError, ValueError) as exc:
            raise RuntimeError(f'fetch {type(exc).__name__}') from None
