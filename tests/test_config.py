import os
from dataclasses import asdict
from pathlib import Path

import pytest

from datagokr.config import KEYS, load
from datagokr.constants import DEFAULT_REMOTE_URL


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults_and_every_precedence_layer(monkeypatch, tmp_path):
    defaults = load()
    assert defaults.api_key == ""
    assert defaults.remote_url == DEFAULT_REMOTE_URL
    assert defaults.download_dir == tmp_path / "datagokr"
    assert defaults.session_file == tmp_path / ".config/datagokr/session.json"
    config_file = tmp_path / ".config/datagokr/config.toml"
    config_file.parent.mkdir(parents=True)

    def values(layer):
        return (f"fixture-{layer}", f"https://{layer}.invalid/mcp",
                f"~/downloads-{layer}", f"~/session-{layer}.json")

    def expected(layer):
        key, url, download, session = values(layer)
        return dict(api_key=key, remote_url=url, download_dir=Path(download).expanduser(),
                    session_file=Path(session).expanduser())

    config_file.write_text("\n".join(f'{key} = "{value}"' for key, value in zip(KEYS, values("toml"))))
    assert asdict(load()) == expected("toml")
    (tmp_path / ".env").write_text("\n".join(f'{key}="{value}"' for key, value in zip(KEYS, values("dotenv"))))
    assert asdict(load()) == expected("dotenv")
    for key, value in zip(KEYS, values("environment")):
        monkeypatch.setenv(key, value)
    assert asdict(load()) == expected("environment")
    assert asdict(load(**expected("argument"))) == expected("argument")
    assert load(api_key="").api_key == ""


def test_dotenv_quotes_comments_and_safe_display(tmp_path):
    (tmp_path / ".env").write_text(
        '# comment\nexport DATAGOKR_API_KEY="fixture +/= # literal" # comment\n'
        "DATAGOKR_DOWNLOAD_DIR=~/folder  with#spaces # comment\n"
        'DATAGOKR_SESSION_FILE="~/literal-$UNEXPANDED.json"\n'
        'UNRELATED="ignored\n', encoding="utf-8")
    config = load()
    assert config.api_key == "fixture +/= # literal"
    assert config.download_dir == Path("~/folder  with#spaces").expanduser()
    assert config.session_file == Path("~/literal-$UNEXPANDED.json").expanduser()
    assert config.api_key not in repr(config)
    assert config.as_dict()["DATAGOKR_API_KEY"] == "[configured]"
    assert "DATAGOKR_API_KEY" not in os.environ
    assert load(env_file=tmp_path / "absent.env").api_key == ""


def test_invalid_configuration_errors_do_not_echo_values(tmp_path, monkeypatch):
    config_file = tmp_path / "bad.toml"
    config_file.write_text('DATAGOKR_API_KEY = "fixture-private-value')
    with pytest.raises(ValueError) as error:
        load(config_file=config_file)
    assert "fixture-private-value" not in str(error.value)
    assert error.value.__suppress_context__
    config_file.write_text("DATAGOKR_API_KEY = 123")
    with pytest.raises(ValueError, match="DATAGOKR_API_KEY must be a string"):
        load(config_file=config_file)
    monkeypatch.setenv("DATAGOKR_REMOTE_URL", " ")
    with pytest.raises(ValueError, match="DATAGOKR_REMOTE_URL must not be empty"):
        load()
