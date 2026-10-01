# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.5] - 2026-10-01

- Extension settings explain where to copy the data.go.kr API key (My Page → 개인 API 인증키 → 인증키 복사(Decoding)).

## [0.1.4] - 2026-10-01

- Portal login opens the CAPTCHA image in the system viewer, since Claude Desktop folds tool output.

## [0.1.3] - 2026-10-01

- Claude Desktop extension (`datagokr.mcpb`) with a uv runtime and optional sensitive settings.
- Local two-step portal login with a user-read CAPTCHA; existing CLI login remains available.
- Remote previews no longer forward API keys; Windows sessions use Credential Manager.
- Desktop download/install instructions and matching package, CLI, and extension versions.

## [0.1.2] - 2026-09-29

- README: 로컬 패키지가 왜 필요한지·사용자 컴퓨터에서 무엇이 실행되고 무엇이 오가는지 설명 절과 표 추가
- README: PyPI·CI·라이선스·MCP 레지스트리 배지

## [0.1.0] - 2026-09-09

### Added

- Public catalog search, dataset details, field search, and remote previews.
- Local data access with the user's own API key, portal session, and disk:
  fetch, access guidance, explicit portal applications, and downloads.
- A Python API, the `datagokr` CLI, and the `datagokr-mcp` stdio server.
- Configuration through arguments, environment variables, `.env`, and TOML.
- Python 3.11/3.12 CI, data provenance, privacy, and rate-limit documentation.

### Security

- `get` disables automatic portal applications by default (`no_apply=True`);
  opting in requires CLI `--apply` or Python/MCP `no_apply=False`.
- Login cookies stay on the user's computer and are sent directly to the portal.
- Only remote `preview` forwards a configured API key in `X-DataGoKr-Key`;
  local access operations send keys directly to the portal/odcloud.

[0.1.5]: https://github.com/datagokr-dev/datagokr/releases/tag/v0.1.5
[0.1.4]: https://github.com/datagokr-dev/datagokr/releases/tag/v0.1.4
[0.1.3]: https://github.com/datagokr-dev/datagokr/releases/tag/v0.1.3
[0.1.0]: https://github.com/datagokr-dev/datagokr/releases/tag/v0.1.0
