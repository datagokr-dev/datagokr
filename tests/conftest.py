from pathlib import Path

import pytest
import responses

from datagokr import remote
from datagokr.config import KEYS


@pytest.fixture
def local_http(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(remote, 'record', lambda *a, **kw: pytest.fail('[TEST] remote must be mocked'))
    with responses.RequestsMock() as http:
        yield http
