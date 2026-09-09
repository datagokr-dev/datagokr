# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/twlaude/datagokr/releases/tag/v0.1.0
