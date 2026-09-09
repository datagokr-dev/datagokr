import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from unittest.mock import Mock

import pytest

import datagokr
from datagokr import cli
from datagokr.constants import DATAGOKR_ACCOUNT_URL


def test_argparse_routes_options_json_config_and_safe_failures(local_http, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    remote = "https://catalog.invalid/mcp"
    row = dict(id="15012896", title="전국 주차장", dtype="FILE", rank=1,
               org_nm="제공기관", page_url="https://www.data.go.kr/", access_note="무키 미리보기")
    cases = [
        (["search", "전국 주차장", "-n", "3", "--dtype", "FILE", "--org", "제공기관",
          "--field", "위도", "--field", "경도"],
         dict(query="전국 주차장", n=3, dtype="FILE", org="제공기관", fields=["위도", "경도"])),
        (["fields", "위도", "경도"], dict(names=["위도", "경도"], n=10, dtype=None, org=None)),
        (["show", "15012896"], dict(dataset_id="15012896")),
        (["preview", "15012896", "-n", "2", "--api-key", "fixture-api"],
         dict(dataset_id="15012896", n=2, api_key="fixture-api")),
        (["fetch", "15012896", "--version", "v2"],
         dict(dataset_id="15012896", version="v2", n=5, api_key=None)),
        (["get", "15012896", "--probe", "--download-dir", "./data", "--session-file", "./login.json"],
         dict(dataset_id="15012896", n=5, no_apply=True, probe=True, api_key=None,
              download_dir="./data", session_file="./login.json")),
        (["apply", "1", "2", "--purpose", "통계 분석", "--session-file", "./login.json"],
         dict(ids=["1", "2"], purpose="통계 분석", session_file="./login.json")),
        (["download", "15012896", "--all-versions", "--out", "./files", "--utf8"],
         dict(dataset_id="15012896", version=None, all_versions=True, out="./files", utf8=True,
              probe=False, download_dir=None)),
    ]
    for index, (arguments, expected) in enumerate(cases):
        result = [row] if arguments[0] in ("search", "fields") else {"command": arguments[0]}
        function = Mock(return_value=result)
        monkeypatch.setattr(datagokr, arguments[0], function)
        arguments = arguments + ["--remote-url", remote]
        arguments = ["--json", *arguments] if index % 2 else [*arguments, "--json"]
        assert cli.main(arguments) == 0
        captured = capsys.readouterr()
        assert json.loads(captured.out) == result and captured.err == ""
        function.assert_called_once_with(**expected, remote_url=remote)
    assert cli.main(["search", "주차장"]) == 0
    displayed = capsys.readouterr().out
    assert all(row[key] in displayed for key in ("id", "title", "org_nm", "page_url", "access_note"))
    monkeypatch.setattr(datagokr, "search", Mock(return_value=[]))
    assert cli.main(["fields", "위도", "경도", "--json"]) == 0
    capsys.readouterr()
    assert cli.main(["search", "없는 항목"]) == 0
    assert "검색 결과가 없습니다" in capsys.readouterr().out

    monkeypatch.setenv("DATAGOKR_API_KEY", "fixture-environment-api")
    assert cli.main(["config", "--json", "--remote-url", remote, "--download-dir", "~/data"]) == 0
    settings = capsys.readouterr()
    assert json.loads(settings.out)["DATAGOKR_API_KEY"] == "[configured]"
    assert json.loads(settings.out)["DATAGOKR_REMOTE_URL"] == remote
    assert json.loads(settings.out)["DATAGOKR_DOWNLOAD_DIR"] == str(tmp_path / "data")
    assert "fixture-environment-api" not in settings.out + settings.err
    assert cli.main(["config", "--api-key", ""]) == 0
    assert "DATAGOKR_API_KEY=\n" in capsys.readouterr().out

    for arguments in (["search", "x", "-n", "0"], ["preview", "1", "-n", "fixture-private"],
                      ["download", "1", "--version", "v1", "--all-versions"],
                      ["login", "--cookie", "fixture-private", "--browser", "chrome"],
                      ["login", "--browser", "fixture-private"], ["fixture-private"]):
        with pytest.raises(SystemExit) as error:
            cli.main(arguments)
        assert error.value.code == 2
        output = capsys.readouterr()
        assert "fixture-private" not in output.out + output.err
        assert "--help" in output.err
    monkeypatch.setattr(datagokr, "show", Mock(side_effect=RuntimeError("serviceKey=fixture-private")))
    assert cli.main(["show", "1", "--json"]) == 1
    failed = capsys.readouterr()
    assert failed.out == "" and json.loads(failed.err)["command"] == "show"
    assert "fixture-private" not in failed.err and "Traceback" not in failed.err
    (tmp_path / ".env").write_text('DATAGOKR_API_KEY="fixture-private')
    assert cli.main(["config"]) == 1
    assert "fixture-private" not in capsys.readouterr().err


def test_login_guidance_cookie_browser_and_both_entrypoints(local_http, monkeypatch, tmp_path, capsys):
    assert cli.main(["login"]) == 0
    instructions = capsys.readouterr()
    assert instructions.err == ""
    for text in (DATAGOKR_ACCOUNT_URL, "보안문자", "document.cookie", "--cookie", "--browser"):
        assert text in instructions.out
    assert not local_http.calls
    assert cli.main(["--json", "login", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert not result["authenticated"] and result["message"] + "\n" == instructions.out

    local_http.get(DATAGOKR_ACCOUNT_URL, body="로그아웃")
    path = tmp_path / "portal-session.json"
    assert cli.main(["login", "--cookie", "JSESSIONID=fixture-private", "--session-file", str(path), "--json"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["authenticated"]
    assert "fixture-private" not in output.out + output.err
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text())["cookie"] == "JSESSIONID=fixture-private"
    monkeypatch.setitem(sys.modules, "browser_cookie3", None)
    assert cli.main(["login", "--browser", "chrome"]) == 1
    assert 'pip install "datagokr[browser]"' in capsys.readouterr().err

    environment = dict(os.environ, HOME=str(tmp_path), DATAGOKR_API_KEY="fixture-private")
    console = str(Path(sys.executable).parent / "datagokr")
    for prefix in ([sys.executable, "-m", "datagokr"], [console]):
        process = subprocess.run([*prefix, "login", "--json"], cwd=tmp_path, env=environment,
                                 capture_output=True, text=True, timeout=20)
        assert process.returncode == 0 and process.stderr == ""
        assert json.loads(process.stdout) == result
        assert "fixture-private" not in process.stdout
