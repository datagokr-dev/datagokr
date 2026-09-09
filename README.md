# datagokr

공공데이터포털의 데이터를 검색하고, **자기 키·자기 로그인·자기 디스크**로 조회·활용신청·다운로드하는 Python 패키지다. CLI, Python API, 로컬 MCP stdio 서버를 제공한다.

검색과 메타데이터는 공개 원격 MCP 서버를 사용한다. `get`, `fetch`, `apply`, `download`는 메타데이터를 받은 뒤 사용자 컴퓨터에서 포털에 접속한다. `preview`는 원격 서버가 본문을 조회하므로, 키를 설정했다면 그 키도 원격 서버로 전송된다. 자세한 전송 범위는 아래 보안 안내를 확인하자.

## 설치와 첫 조회

Python **3.11 이상**과 인터넷 연결이 필요하다. 명령은 macOS/Linux의 Bash 기준이다. 저장소는 https://github.com/twlaude/datagokr 이고, 소스 없이 바로 설치하려면 `pip install git+https://github.com/twlaude/datagokr` 를 쓰면 된다.

```bash
git clone https://github.com/twlaude/datagokr
cd datagokr
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
datagokr --version
datagokr search "전국 주차장"
datagokr show 15012896
datagokr get 15012896
```

`15012896`은 전국주차장정보표준데이터다. `get`은 키와 로그인 없이 첫 5행을 반환한다. 검색 순위·전체 행 수·행 내용은 포털 갱신에 따라 달라진다. CLI 실행파일 대신 `python -m datagokr`도 사용할 수 있다.

원문 전체를 저장하려면 다음을 실행한다. 이 명령은 첫 5행이 아니라 전체 표준데이터를 CSV로 저장하므로 시간이 더 걸릴 수 있다.

```bash
datagokr download 15012896 --out ./downloads
```

응답의 `path`가 실제 저장 경로다. 기본 저장 위치는 `~/datagokr/<dataset_id>/`이고, `--out`을 주면 그 디렉터리에 저장한다. 같은 경로의 파일은 덮어쓴다.

## 설정

우선순위는 **함수·CLI 인자 > 환경변수 > 현재 작업 디렉터리의 `.env` > `~/.config/datagokr/config.toml` > 기본값**이다. `None`은 하위 설정을 상속하고, 빈 API 키 문자열은 키 사용을 끈다. TOML과 `.env` 모두 아래 대문자 이름을 사용한다.

| 설정 키 | 용도 | 기본값 |
| --- | --- | --- |
| `DATAGOKR_API_KEY` | 본인의 odcloud serviceKey, **디코딩 값** | 빈 값 |
| `DATAGOKR_REMOTE_URL` | 원격 검색·메타·미리보기 MCP 주소 | `https://159-223-75-71.sslip.io/mcp` |
| `DATAGOKR_DOWNLOAD_DIR` | 다운로드 기본 폴더 | `~/datagokr` |
| `DATAGOKR_SESSION_FILE` | 포털 로그인 세션 파일 | `~/.config/datagokr/session.json` |

여러 AI 클라이언트에서 함께 쓰려면 `~/.config/datagokr/config.toml`에 설정하는 편이 간단하다. 아래 내용은 TOML 파일의 최상위에 넣는다. 키가 필요한 경우 빈 문자열을 본인 키로 바꾸고 파일 권한을 제한한다.

```toml
DATAGOKR_API_KEY = ""
DATAGOKR_REMOTE_URL = "https://159-223-75-71.sslip.io/mcp"
DATAGOKR_DOWNLOAD_DIR = "~/datagokr"
DATAGOKR_SESSION_FILE = "~/.config/datagokr/session.json"
```

```bash
chmod 600 ~/.config/datagokr/config.toml
datagokr config
datagokr config --json
```

`config`는 유효 설정을 **조회만** 하며 파일을 수정하지 않는다. 키가 있으면 실제 값 대신 `[configured]`를 표시한다. `.env`는 같은 네 이름을 `이름=값`으로 적는다. 셸 명령 실행이나 `${변수}` 치환은 지원하지 않는다. MCP의 작업 디렉터리는 AI 클라이언트마다 다를 수 있어 프로젝트 `.env`에 의존하려면 실행 위치를 확인해야 한다.

한 번만 무키로 실행하거나 출력 경로를 바꿀 수도 있다.

```bash
DATAGOKR_API_KEY='' datagokr get 15012896
DATAGOKR_DOWNLOAD_DIR=./downloads datagokr download 15012896
```

## 포털 로그인과 활용신청

검색·표준데이터 조회에는 로그인이 필요 없다. odcloud 활용신청에는 본인의 공공데이터포털 계정 세션이 필요하며 API 키와 로그인 쿠키는 서로 다른 인증정보다.

1. `datagokr login`을 실행하면 절차 안내가 나온다. 이 명령만으로 브라우저를 열거나 로그인하지 않는다.
2. [포털 활용신청 현황](https://www.data.go.kr/iim/api/selectAcountList.do)을 브라우저에서 열고 로그인한다. 보안문자는 직접 입력한다.
3. 로그인 후 `www.data.go.kr` 페이지에서 브라우저 쿠키를 가져온다. 다음 세 방법 중 하나를 사용한다.

브라우저 쿠키 읽기를 사용하려면 현재 소스 디렉터리에서 선택 의존성을 설치한다.

```bash
python -m pip install -e '.[browser]'
datagokr login --browser chrome
# 같은 방식으로 --browser safari 또는 --browser firefox
```

브라우저·운영체제의 쿠키 암호화나 권한 때문에 읽기가 실패할 수 있다. 직접 입력하려면 개발자도구 콘솔에서 `document.cookie`를 평가해 복사한다. 값을 생략한 `datagokr login --cookie`는 숨김 입력으로 받는다(권장). `--cookie "값"`처럼 명령줄에 직접 넣으면 셸 기록과 프로세스 인자에 남는다.

```bash
python - <<'PY'
from getpass import getpass
from datagokr.session import login

result = login(cookie=getpass("포털 쿠키: "))
print(result["message"])
PY
```

계정 페이지에서 로그인을 확인한 뒤 세션을 저장하며, 파일 권한은 `0600`이다. `document.cookie`로는 HttpOnly 쿠키를 읽을 수 없으므로 복사한 값으로 검증이 실패하면 브라우저 쿠키 읽기 경로를 사용하거나 다시 로그인한다. 만료된 세션은 `datagokr login`으로 갱신한다. MCP에서는 `login_status` 툴로 상태를 확인할 수 있다.

키가 필요한 포털 파일을 검색하고 `show`의 상세 페이지·요청 예시를 확인한 다음, 검색 결과의 id로 신청·조회한다. 아래 셸 변수에는 실제 검색 결과의 id를 입력한다.

```bash
read -r -p '포털 파일 dataset id: ' dataset_id
datagokr show "$dataset_id"
datagokr apply "$dataset_id" --purpose "공공데이터 통계 분석"
datagokr fetch "$dataset_id" -n 5
datagokr get "$dataset_id" -n 5
```

`apply`는 저장된 세션으로 실제 신청을 제출한다(한 번에 1~50개 id). `applied`나 `portal_status`를 확인하자. 이미 신청했거나 자동 신청 대상이 아니면 `not_applicable`, 로그인이 필요하면 `manual` 등이 반환된다. 일반 오픈API는 상세 페이지에서 별도 신청이 필요할 수 있다. 승인 직후에도 키 반영이 늦어 401이 계속되면 잠시 후 재시도하거나 `get`의 원문 경로를 이용한다.

## CLI와 데이터 접근 방식

`--json`은 명령 앞이나 뒤에 붙일 수 있다. 성공 결과는 stdout, 실패 안내는 stderr에 출력하며 CLI 요청 실패는 종료 코드 1, 잘못된 인자는 2다. 성공적으로 전달된 응답 안에 `status_code=401`이나 신청 상태가 있을 수 있으므로 자동화에서는 응답 내용도 확인한다.

| 명령 | 예시 | 동작 |
| --- | --- | --- |
| `search` | `datagokr search "전국 주차장" -n 5 --json` | 주제 검색; `--dtype FILE\|API\|STD`, `--org`, 반복 가능한 `--field` |
| `show` | `datagokr show 15012896` | 컬럼·접근 방식·요청 예시 조회 |
| `fields` | `datagokr fields 위도 경도 -n 5` | 지정 컬럼을 모두 가진 데이터 검색 |
| `preview` | `datagokr preview 15012896 -n 3` | 원격 서버에서 미리보기; 설정 키 전송 |
| `fetch` | `datagokr fetch "$dataset_id" -n 5` | 본인 로컬 키로 odcloud 조회; `--version` 선택 가능 |
| `get` | `datagokr get 15012896 -n 3` | 접근 방식별 조회·신청·원문 폴백 |
| `apply` | `datagokr apply "$dataset_id"` | 본인 세션으로 활용신청 제출 |
| `download` | `datagokr download 15012896 --out ./downloads` | 원문을 로컬 디스크에 저장 |
| `login` | `datagokr login` | 로그인 안내 또는 쿠키 등록 |
| `config` | `datagokr config --json` | 키를 가린 유효 설정 조회 |

각 명령의 전체 옵션은 `datagokr <명령> --help`로 확인한다. 검색·컬럼 검색은 원격 서버에서 최대 20건, 원격 미리보기는 최대 20행·50컬럼이다. `show`도 컬럼을 최대 50개 표시한다.

| `access_kind` | `get`의 결과 |
| --- | --- |
| `STD_FILE` | 무키로 표준데이터 첫 n행. 파일이 없는 API 전용 표준은 요청 템플릿 안내 |
| `STD` | 전국판 부모가 있으면 그 본문과 부모 id 반환; 없으면 카탈로그 안내 |
| `LINK` | 제공기관의 외부 URL |
| `OPEN_API` | 본인 serviceKey로 호출할 요청 템플릿 또는 포털 상세 페이지 |
| `PORTAL_FILE` | 키로 odcloud 조회 → 401이면 로그인 세션으로 신청 → 승인 확인 후 재조회 → 원문 미리보기·다운로드 폴백. 키가 없으면 바로 원문 경로 |

`get`은 기본적으로 활용신청을 하지 않고 원문 파일 저장으로 폴백한다. 본인 계정으로 신청까지 하려면 `get --apply`를 명시한다(MCP·Python API는 `no_apply=False`). `get --probe`는 신청·파일 저장 없이 접근을 확인한다. `download --probe`도 저장하지 않는다. 포털 원문 미리보기는 CSV/TSV/TXT/XLSX를 지원하고, 지원하지 않는 형식이나 미리보기 실패는 원문 다운로드로 이어질 수 있다.

포털 파일은 `download --version 버전키` 또는 `download --all-versions`로 버전을 선택한다(동시 사용 불가). `show`의 요청 예시를 참고한다. `--utf8`은 CSV 원문과 함께 UTF-8 변환본을 추가 저장한다. 표준데이터 CSV는 기본적으로 UTF-8 BOM 인코딩이다.

## AI 클라이언트에 MCP 등록

로컬 `datagokr-mcp`가 stdio로 실행되며 툴 9개를 제공한다: `search`, `show`, `fields`, `preview`, `fetch`, `get`, `apply`, `download`, `login_status`. 툴 설명은 한국어·영어를 함께 제공한다. `login`과 `config`는 CLI에서 실행하고, MCP에는 키·쿠키 입력 인자가 없다.

먼저 설치한 가상환경에서 `command -v datagokr-mcp`로 실행파일의 **절대경로**를 확인한다. 아래 예시는 `datagokr-mcp`가 AI 클라이언트의 PATH에도 있을 때 동작한다. 찾지 못하면 각 `command` 또는 CLI의 마지막 실행파일을 방금 확인한 절대경로로 바꾼다. JSON/TOML의 명령 경로에 `~` 확장을 기대하지 말자. `command`를 가상환경 Python 절대경로로 하고 `args`를 `["-m", "datagokr.mcp"]`로 지정해도 된다.

각 설정은 기존 파일의 다른 항목을 유지하며 병합한다. 키는 개인 `~/.config/datagokr/config.toml`에 두면 아래 예시에 비밀값을 넣지 않아도 된다. 등록 후 클라이언트에서 MCP 연결을 새로고침하거나 재시작한다.

### Claude Code

```bash
claude mcp add datagokr-local -s user -- /absolute/path/to/.venv/bin/datagokr-mcp
claude mcp add --transport http datagokr-public https://datagokr.dev/mcp -s user
claude mcp list
```

로컬은 사용자 컴퓨터에서 실행되고 원격은 검색·조회용 공개 서버에 연결한다. 필요한 연결만 등록하면 된다. `-s user`는 모든 프로젝트에 적용되며, `claude mcp list` 또는 대화창의 `/mcp`에서 연결을 확인한다. 삭제는 `claude mcp remove datagokr-local -s user`와 `claude mcp remove datagokr-public -s user`다. [Claude Code 공식 MCP 문서](https://code.claude.com/docs/en/mcp).

### Codex CLI

CLI로 필요한 연결을 등록한다.

```bash
codex mcp add datagokr-local -- /absolute/path/to/.venv/bin/datagokr-mcp
codex mcp add datagokr-public --url https://datagokr.dev/mcp
codex mcp list
codex exec --skip-git-repo-check "datagokr-public 서버의 search 툴로 '전국 주차장' 1건만 검색해서 제목만 답해"
```

`list`의 `enabled`는 등록 상태다. 실제 연결·호출 성공은 대화의 툴 응답으로 확인한다. 삭제는 `codex mcp remove datagokr-local`과 `codex mcp remove datagokr-public`이다. 직접 설정하려면 CLI 등록 대신 `~/.codex/config.toml`에 추가한다.

```toml
[mcp_servers.datagokr-local]
command = "datagokr-mcp"
startup_timeout_sec = 30
tool_timeout_sec = 180
```

`codex mcp list` 또는 `/mcp`에서 확인한다. 환경변수 방식으로 키를 관리한다면 위 테이블에 `env_vars = ["DATAGOKR_API_KEY"]`를 추가해 전달할 수 있다. [OpenAI 공식 MCP 문서](https://developers.openai.com/codex/mcp).

### Cursor

프로젝트의 `.cursor/mcp.json`에 추가한다. 모든 프로젝트에서 사용하려면 `~/.cursor/mcp.json`을 사용한다.

```json
{
  "mcpServers": {
    "datagokr": {
      "command": "datagokr-mcp",
      "args": []
    }
  }
}
```

[Cursor 공식 MCP 문서](https://cursor.com/docs/mcp).

### Gemini CLI

`~/.gemini/settings.json`에 추가한다.

```json
{
  "mcpServers": {
    "datagokr": {
      "command": "datagokr-mcp",
      "args": [],
      "timeout": 180000
    }
  }
}
```

`/mcp`에서 연결을 확인한다. `timeout` 단위는 밀리초다. [Gemini CLI 공식 MCP 문서](https://geminicli.com/docs/tools/mcp-server/).

### Windsurf

`~/.codeium/windsurf/mcp_config.json`에 추가한다.

```json
{
  "mcpServers": {
    "datagokr": {
      "command": "datagokr-mcp",
      "args": []
    }
  }
}
```

Cascade의 MCP 설정에서 서버와 툴을 확인한다. [Windsurf 공식 MCP 문서](https://docs.windsurf.com/windsurf/cascade/mcp).

다른 클라이언트도 **로컬 stdio MCP**를 지원하면 같은 명령으로 연결할 수 있다. `datagokr-mcp`는 MCP 클라이언트가 시작하는 프로세스이므로 터미널에서 직접 실행해 출력이 없어도 입력 대기일 수 있다. 대화에서 “전국 주차장 데이터를 검색하고 15012896의 첫 3행을 보여줘”처럼 요청하면 된다. 대용량 다운로드는 클라이언트 제한 시간을 넘을 수 있으므로 CLI로 실행할 수도 있다.

## Python API

```python
import datagokr

datasets = datagokr.search("전국 주차장", n=5)
details = datagokr.show("15012896")
result = datagokr.get("15012896", n=3, api_key="")
print(result["data"]["columns"])
print(result["data"]["rows"])
files = datagokr.download("15012896", out="./downloads")
```

최상위 공개 함수는 `search`, `show`, `fields`, `preview`, `fetch`, `get`, `apply`, `download`다. `fields`에는 컬럼명 리스트, `apply`에는 id 리스트를 전달한다. 원격 주소는 `remote_url=`, 키를 사용하는 함수에는 `api_key=`로 설정을 덮어쓸 수 있다. `get`의 `no_apply`(기본 `True`, 신청 안 함)·`probe=True`와 `download`의 `probe=True`는 CLI와 같은 의미다. 반환값은 dict 또는 list이고 Python API는 동기 호출이다.

## 보안과 데이터 전송

### 원격 서버로 전송되는 것 / 안 되는 것

| 작업 | 원격 MCP 서버로 전송되는 것 | 원격 MCP 서버로 전송되지 않는 것 |
| --- | --- | --- |
| `search`·`show`·`fields`·`record`·`download_url` | 질의·필드 조건·식별자·건수 등 조회 인자만 | API 키·로그인 쿠키·로컬 파일 |
| `preview` (원격 `get_preview`) | 조회 인자 + 설정 시 API 키 헤더 `X-DataGoKr-Key` | 로그인 쿠키·로컬 파일 |
| `get`·`fetch`·`apply`·`download` | `record`로 카탈로그 식별자 조회만 | 키·쿠키·신청 본문: 사용자 컴퓨터에서 포털/odcloud로 직접 전송; 파일은 로컬 저장 |

`record`·`download_url`은 원격 툴이며 최상위 Python API나 CLI 명령은 아니다. 로그인 쿠키는 어떤 경우에도 원격 MCP 서버로 보내지 않는다. AI 클라이언트에 반환한 데이터의 처리는 해당 클라이언트의 정책을 따른다.

- 검색어·필드 조건·데이터셋 id는 설정한 원격 MCP 서버로 전달된다. 서버는 검색·메타·원격 미리보기를 제공하며 원격 서버 자체는 활용신청이나 사용자 파일 저장을 하지 않는다.
- **`preview`는 설정된 API 키를 `X-DataGoKr-Key` HTTP 헤더로 원격 서버에 보낸다.** 해당 연결의 초기화·툴 목록 요청에도 이 헤더가 포함된다. 표준데이터 미리보기여도 키가 설정돼 있으면 전송된다. 원격 서버로 키를 보내지 않으려면 `preview(..., api_key="")`, CLI `preview --api-key ''`를 쓰거나 로컬 `get`/`fetch`를 사용한다. MCP `preview`는 인자로 키를 끌 수 없으므로 서버 프로세스의 `DATAGOKR_API_KEY`를 빈 값으로 설정한다.
- `get`/`fetch`의 API 키는 로컬에서 odcloud로 전달된다. 포털 로그인 쿠키는 사용자 세션 파일에 저장하고 포털 접속에 사용하며 원격 검색 MCP에는 보내지 않는다. 다운로드는 MCP 서버 프로세스가 실행되는 컴퓨터에 저장된다.
- CLI/MCP는 키·쿠키를 출력하거나 오류 메시지에 포함하지 않도록 처리한다. 하지만 사용자가 직접 인쇄하거나 HTTP 디버그 로깅을 켜거나 명령줄 인자에 비밀값을 넣으면 노출될 수 있다. 키·쿠키를 AI 대화, 버그 보고, 커밋에 붙여 넣지 않는다.
- 세션 파일은 `0600`으로 저장한다. `.env`·개인 설정 파일도 접근 권한을 제한하고 버전 관리에서 제외한다. 원격 주소를 변경하면 그 서버가 검색 입력과 `preview`의 키를 받으므로 신뢰하는 HTTPS 주소를 사용한다.
- `get`은 기본적으로 자동 활용신청을 하지 않으며 파일 저장으로 폴백할 수 있다. `get --apply`로 신청을 허용할 수 있고, `apply`는 신청 제출, `download`는 파일 저장을 수행한다. `get`/`download`는 같은 파일을 덮어쓸 수 있다. 조회만 원하면 `probe` 옵션을 사용한다.

## 데이터 출처와 이용조건

데이터 출처는 [공공데이터포털(data.go.kr)](https://www.data.go.kr/)과 각 제공기관이다. 데이터셋별 이용허락(공공누리 유형, 출처표시 등)은 검색 결과의 `page_url`에 표시된 조건을 따른다. 이 패키지와 원격 서버는 카탈로그 색인과 접근 안내를 제공하며, 미리보기·조회·다운로드로 받은 데이터의 별도 이용권을 부여하지 않는다. 패키지의 [MIT 라이선스](LICENSE)는 코드에 적용되고 데이터셋의 이용조건을 대체하지 않는다.

## 레이트리밋

공개 원격 서버는 **IP당 최근 60초 30회, UTC 날짜당 2,000회** HTTP 요청을 허용한다. 초기화·툴 목록 요청도 포함되며 `/health`는 제외된다. 전체 IP 합계 제한(최근 60초 120회·최근 24시간 10,000회)도 적용된다. HTTP 429를 받으면 `Retry-After`만큼 기다린다. 패키지는 이를 읽어 한 번 재시도한다. 자체 호스팅 서버의 한도는 운영 설정에 따라 달라질 수 있다.

## 문제 신고

오류·문서 수정·서비스 문의는 [GitHub Issues](https://github.com/twlaude/datagokr/issues)에 남긴다. 패키지 버전과 재현 명령, 비밀값을 제거한 오류를 함께 적고 API 키·로그인 쿠키·개인 설정 파일은 첨부하지 않는다.

## 검증과 문제 해결

개발 테스트는 HTTP mock과 실제 stdio 프로세스를 사용한다. 기본 실행에서는 외부 네트워크 테스트 한 개를 건너뛴다. 모든 테스트 출력에 `[TEST]`를 붙이는 실행 예시는 다음과 같다.

```bash
python -m pip install -e '.[dev]'
set -o pipefail
python -m pytest -q 2>&1 | sed 's/^/[TEST] /'
DATAGOKR_LIVE_TEST=1 python -m pytest -q -s 2>&1 | sed 's/^/[TEST] /'
```

실서버 테스트는 기본 공개 서버와 포털에 접속해 무키 CLI 검색·`get 15012896`·MCP stdio 목록/검색을 검증한다. 다운로드·로그인 세션 경로는 임시 디렉터리로 지정한다. 최초 health 연결 자체가 불가능하면 skip하고, 연결 후 잘못된 응답·데이터·툴 계약은 실패로 처리한다. 실제 환경 점검에서는 skip을 성공으로 간주하지 말자.

| 증상 | 확인할 것 |
| --- | --- |
| `datagokr-mcp` 실행파일을 못 찾음 | 설치한 가상환경의 절대경로를 MCP 설정에 지정 |
| 검색·메타 조회 실패 | 인터넷·`DATAGOKR_REMOTE_URL` 확인, 잠시 후 재시도; 429는 `Retry-After`만큼 기다려 한 번 재시도 |
| `fetch`의 401 또는 키 관련 안내 | 본인의 디코딩 키·활용신청·승인 반영 상태 확인; 무키 조회는 `get` |
| 로그인 실패·만료 | `datagokr login`의 절차로 재로그인; 브라우저 선택 의존성·쿠키 읽기 권한 확인 |
| `get`이 행 대신 URL·템플릿·파일 경로 반환 | `access_kind`에 따른 정상 경로; 반환된 안내와 파일 확인 |
| 원문이 없거나 빈 파일 안내 | 포털 상세 페이지와 제공기관 링크 확인; 모든 카탈로그 항목이 다운로드 가능한 파일인 것은 아님 |
