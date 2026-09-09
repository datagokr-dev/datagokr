"""Load explicit arguments > environment > ./.env > user config.toml.

Both files use the four uppercase DATAGOKR_* setting names. TOML settings
are top-level strings. Dotenv supports export, quotes and comments, with
no shell execution or variable interpolation. None inherits; an empty
API key explicitly disables authenticated access.
"""

import os
import re
import shlex
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from datagokr.constants import DEFAULT_REMOTE_URL

KEYS = ("DATAGOKR_API_KEY", "DATAGOKR_REMOTE_URL", "DATAGOKR_DOWNLOAD_DIR",
        "DATAGOKR_SESSION_FILE")


@dataclass(frozen=True)
class Config:
    api_key: str = field(repr=False)
    remote_url: str
    download_dir: Path
    session_file: Path

    def as_dict(self):
        """Safe configuration display for command-line callers."""
        return dict(zip(KEYS, ("[configured]" if self.api_key else "",
                               self.remote_url, str(self.download_dir), str(self.session_file))))


def _read(path, *, dotenv=False):
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError):
        raise ValueError("Cannot read datagokr configuration file") from None
    try:
        if not dotenv:
            return tomllib.loads(text)
        values = {}
        for line in text.splitlines():
            name, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and name.strip() in KEYS:
                value = value.strip()
                values[name.strip()] = (" ".join(shlex.split(value, comments=True))
                    if value.startswith(("'", '"')) else re.split(r"\s+#", value, maxsplit=1)[0])
        return values
    except ValueError:
        raise ValueError("Invalid datagokr configuration file") from None


def load(*, api_key=None, remote_url=None, download_dir=None, session_file=None,
         config_file=None, env_file=None):
    """Resolve settings on every call, without changing the process environment."""
    user_dir = Path.home() / ".config" / "datagokr"
    values = dict(zip(KEYS, ("", DEFAULT_REMOTE_URL, Path.home() / "datagokr",
                             user_dir / "session.json")))
    sources = (
        _read(Path(config_file).expanduser() if config_file is not None else user_dir / "config.toml"),
        _read(Path(env_file).expanduser() if env_file is not None else Path.cwd() / ".env", dotenv=True),
        os.environ,
        dict(zip(KEYS, (api_key, remote_url, download_dir, session_file))),
    )
    for source in sources:
        values.update({key: source[key] for key in KEYS if source.get(key) is not None})
    for key, value in values.items():
        path_setting = key in KEYS[2:]
        if not isinstance(value, (str, Path) if path_setting else str):
            raise ValueError(f"{key} must be a string") from None
        if key != KEYS[0] and not str(value).strip():
            raise ValueError(f"{key} must not be empty") from None
    return Config(values[KEYS[0]], values[KEYS[1]],
                  Path(values[KEYS[2]]).expanduser(), Path(values[KEYS[3]]).expanduser())
