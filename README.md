# datagokr

[![PyPI](https://img.shields.io/pypi/v/datagokr-mcp?label=PyPI)](https://pypi.org/project/datagokr-mcp/) [![CI](https://github.com/datagokr-dev/datagokr/actions/workflows/ci.yml/badge.svg)](https://github.com/datagokr-dev/datagokr/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![MCP Registry](https://img.shields.io/badge/MCP%20Registry-dev.datagokr%2Fdatagokr-green)](https://registry.modelcontextprotocol.io/v0/servers?search=datagokr) [![Remote MCP](https://img.shields.io/badge/remote-datagokr.dev%2Fmcp-informational)](https://datagokr.dev)

**공공데이터, AI한테 말로 찾고 신청까지 맡기세요.**

공공데이터포털(data.go.kr)의 데이터 10.9만 건을 AI와 대화하며 찾고, 내 계정으로 활용신청부터 다운로드까지 처리해 주는 AI 확장 기능(MCP)이에요. 검색은 클로드·ChatGPT 어디서나 되고, 활용신청·다운로드는 클로드 데스크탑처럼 내 컴퓨터에서 도는 앱에서 돼요. 소개 페이지: https://datagokr.dev

> **처음엔 내 AI 앱에 설치(연결)부터 해야 써요.** 클로드 데스크탑이면 [설치 파일(datagokr.mcpb)](https://github.com/datagokr-dev/datagokr/releases/latest/download/datagokr.mcpb)을 받아 더블클릭하면 끝이에요. 다른 앱은 [사용 환경별 설치·사용 방법](#사용-환경별-설치사용-방법)을 보세요.

## 왜 만들었나요?

공공데이터포털에서 직접 데이터셋을 찾다 보면 두 가지 걸림돌을 만나요.

- **검색 결과가 수백 개씩 쏟아져요.** 같은 주제를 기관마다 따로 올리다 보니 제목이 비슷비슷한 데이터셋이 잔뜩 나와요.
- **목록만 봐서는 어떤 컬럼이 있는지 몰라요.** 내가 찾는 내용이 진짜 들어 있는지는 하나씩 열어 봐야 알아요.

그래서 포털 전체를 **컬럼(표의 열 이름)까지 미리 색인하고 임베딩**해 뒀어요. 필요한 데이터를 말로 설명하면 제목이 딱 맞지 않아도 뜻이 통하는 데이터셋을 찾아 주고, 비슷한 건 주제별로 묶어서 보여 주고, 컬럼과 첫 행까지 바로 확인할 수 있어요.

## 이렇게 물어보면 돼요

| 질문 | 찾은 데이터 | 받은 것 |
| --- | --- | --- |
| "위도·경도 정보가 있는 병원 데이터 찾아줘" | 3075427 위탁병원 현황 | 키 없이 첫 행 확인: 포항의료원 (36.035, 129.354) 등 10컬럼 |
| "전국 주차장 표준데이터 첫 행 보여줘" | 15012896 전국주차장정보표준데이터 | 키 없이 첫 행(34컬럼, 총 18,883행) + 전체 다운로드 주소 |
| "아파트 실거래가 API는 어떻게 사용해?" | 15126469 국토교통부 오픈API | 호출 템플릿(엔드포인트·serviceKey)과 활용신청 방법 안내 |

2026-09-27 실제 호출 결과예요. 검색, 구조 확인, 첫 행 미리보기는 인증키가 필요 없어요.

## 할 수 있는 일은 두 단계예요

**1단계 · 찾기와 구조 확인 — 설치·가입 없이 바로**

- 대화로 검색: "서울 공영주차장 위치 데이터 있어?" — 정확한 단어가 아니어도 뜻이 통하면 찾아내요
- 컬럼으로 검색: "위도·경도·병원명이 같이 있는 자료"
- 구조 미리보기: 어떤 열이 들어 있는지, 첫 몇 줄이 어떻게 생겼는지
- 받는 법 안내: 어디서 어떻게 받을 수 있는지 알려줘요

이 단계는 공개 원격 서버(`https://datagokr.dev/mcp`)가 처리해요. 키도 로그인도 필요 없어요.

**2단계 · 활용신청과 데이터 받기 — 내 컴퓨터에 프로그램 필요 (클로드 웹·ChatGPT에선 안 돼요)**

- **활용신청을 말 한마디로.** 포털에서는 데이터셋마다 상세 페이지에서 신청 버튼을 누르고 목적 선택·설명 입력·약관 동의까지 한 건씩 반복해야 해요. 여기서는 "이 데이터들 활용신청해줘" 한마디면 최대 50개를 한 번에 신청해요. 자동승인 데이터라면 바로 쓸 수 있어요.
- **내 API 키로 바로 조회.** API 문서를 읽고 주소에 키를 붙여 직접 호출할 필요 없이, "이 API 데이터 몇 줄만 가져와"라고 하면 내 키로 불러와요.
- **파일 다운로드도 말로.** 데이터셋마다, 지난 버전마다 다운로드 버튼을 누를 필요 없이 "이 데이터 전부 받아줘"면 지난 버전까지 한꺼번에 받고, 엑셀에서 한글이 안 깨지는 UTF-8 파일도 같이 만들어 줘요.

2단계는 내 data.go.kr 계정과 API 키로 하는 일이에요. 계정과 키가 남의 서버(우리 서버 포함)를 거치지 않도록, 내 컴퓨터에서 포털로 직접 접속하는 프로그램(이 패키지)이 대신 처리해요.

## 내 앱에선 어디까지 될까요?

| 쓰는 앱 | 1단계 찾기 | 2단계 신청·받기 | 설치 |
| --- | --- | --- | --- |
| 클로드 데스크탑 (윈도우·맥) | ✅ | ✅ | [설치 파일 더블클릭](#claude-데스크탑-windowsmac) |
| 클로드 웹(claude.ai) · ChatGPT(웹·앱) | ✅ | ❌ data.go.kr에서 직접 | [커넥터 주소 연결](#클로드-웹chatgpt-커넥터-1단계만) |
| 터미널 AI (Claude Code·Codex·Cursor 등) | ✅ | ✅ 이 패키지 설치 시 | [MCP 등록](#ai-클라이언트에-mcp-등록) + `pip install datagokr-mcp` |

## 사용 환경별 설치·사용 방법

- **클로드 데스크탑 (추천, 1·2단계 모두)**: [datagokr.mcpb 받기](https://github.com/datagokr-dev/datagokr/releases/latest/download/datagokr.mcpb) → 더블클릭 → 설치. 입력 칸 3개(API 키·포털 아이디·비밀번호)는 검색만 할 거면 비워 두세요. API 키는 data.go.kr 로그인 → 마이페이지 → "개인 API 인증키" 칸의 **인증키 복사(Decoding)** 값이에요. 활용신청은 대화에서 "공공데이터포털에 로그인해줘"(보안문자 글자 입력) → "이 데이터 활용신청해줘". [자세히](#claude-데스크탑-windowsmac)
- **클로드 웹·ChatGPT (1단계만)**: 커넥터에 `https://datagokr.dev/mcp` 주소만 넣으면 돼요. 로그인 창 없이 연결돼요. [자세히](#클로드-웹chatgpt-커넥터-1단계만)
- **터미널 AI (개발자용)**: `claude mcp add --transport http datagokr https://datagokr.dev/mcp`, 2단계는 `pip install datagokr-mcp`. 또는 에이전트에게 `Fetch and execute the setup instructions from https://datagokr.dev/agent-setup/prompt.md` 한 줄을 붙여 넣으세요.

---

아래부터는 개발자용 상세 문서예요.

## 2단계 프로그램(이 패키지)이 내 컴퓨터에서 하는 일

검색·구조 확인·첫 행 미리보기는 공개 원격 MCP 서버(`https://datagokr.dev/mcp`)만 등록하면 끝나고, 아무것도 설치하지 않는다. 파일 **전체 다운로드**, **활용신청**, **본인 키로 오픈API 조회**는 사용자 본인의 data.go.kr 계정과 키가 있어야 하는 일이다. 그 키와 로그인이 남의 서버(원격 MCP 서버 포함)를 거치지 않게 하려고, 사용자 컴퓨터에서 포털에 직접 접속하는 작은 프로그램을 따로 둔다. 그게 이 패키지다.

| 하는 일 | 어디서 실행되나 | 무엇이 오가나 |
| --- | --- | --- |
| 검색·구조·컬럼 검색 | 원격 MCP 서버 | 검색어·데이터셋 id만 전송. 키·쿠키 없음 |
| 미리보기 `preview` | 원격 MCP 서버 | 조회 인자만 전송. 키·쿠키 없음 |
| 다운로드·활용신청·본인 키 조회 | **사용자 컴퓨터** | data.go.kr/odcloud에 직접 접속. 키·쿠키는 공식 서비스에만 전송 |
| 받은 파일 | **사용자 컴퓨터** | `~/datagokr/<dataset_id>/`에 저장 |

이 프로그램은 백그라운드에 상주하지 않고 CLI를 칠 때나 AI 클라이언트가 MCP로 부를 때만 실행된다. 코드는 MIT 오픈소스라 전부 읽어볼 수 있고, 전송 범위의 정확한 목록은 아래 [보안과 데이터 전송](#보안과-데이터-전송)에 있다.

## 설치와 첫 조회

Python **3.11 이상**과 인터넷 연결이 필요하다. 명령은 macOS/Linux의 Bash 기준이다. 저장소는 https://github.com/datagokr-dev/datagokr 이고, PyPI 이름은 `datagokr-mcp`(import 이름과 CLI는 `datagokr` 그대로)라 `pip install datagokr-mcp` 로 설치할 수 있고, 최신 소스는 `pip install git+https://github.com/datagokr-dev/datagokr` 로 받는다.

```bash
git clone https://github.com/datagokr-dev/datagokr
cd datagokr
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
datagokr --version
datagokr search "전국 주차장"
datagokr show 15012896
datagokr get 15012896
```

검색어는 예시다. 위 `15012896`은 전국주차장정보표준데이터다. `get`은 키와 로그인 없이 첫 5행을 반환한다. 검색 순위·전체 행 수·행 내용은 포털 갱신에 따라 달라진다. CLI 실행파일 대신 `python -m datagokr`도 사용할 수 있다.

원문 전체를 저장하려면 다음을 실행한다. 이 명령은 첫 5행이 아니라 전체 표준데이터를 CSV로 저장하므로 시간이 더 걸릴 수 있다.

```bash
datagokr download 15012896 --out ./downloads
```

응답의 `path`가 실제 저장 경로다. 기본 저장 위치는 `~/datagokr/<dataset_id>/`이고, `--out`을 주면 그 디렉터리에 저장한다. 같은 경로의 파일은 덮어쓴다.

## AI 에이전트에게 한 줄로 설치시키기

클로드 코드·코덱스·커서 등 어떤 에이전트든 아래 문장 하나를 그대로 던지면 클라이언트를 감지해 원격 서버를 등록하고 검색 1회로 검증까지 한다.

```
Fetch and execute the setup instructions from https://datagokr.dev/agent-setup/prompt.md
```

## 설정

우선순위는 **함수·CLI 인자 > 환경변수 > 현재 작업 디렉터리의 `.env` > `~/.config/datagokr/config.toml` > 기본값**이다. `None`은 하위 설정을 상속하고, 빈 API 키 문자열은 키 사용을 끈다. TOML과 `.env` 모두 아래 대문자 이름을 사용한다.

| 설정 키 | 용도 | 기본값 |
| --- | --- | --- |
| `DATAGOKR_API_KEY` | 본인의 odcloud serviceKey, **디코딩 값** | 빈 값 |
| `DATAGOKR_REMOTE_URL` | 원격 검색·메타·미리보기 MCP 주소 | `https://datagokr.dev/mcp` |
| `DATAGOKR_DOWNLOAD_DIR` | 다운로드 기본 폴더 | `~/datagokr` |
| `DATAGOKR_SESSION_FILE` | 포털 로그인 세션 파일 | `~/.config/datagokr/session.json` |

여러 AI 클라이언트에서 함께 쓰려면 `~/.config/datagokr/config.toml`에 설정하는 편이 간단하다. 아래 내용은 TOML 파일의 최상위에 넣는다. 키가 필요한 경우 빈 문자열을 본인 키로 바꾸고 파일 권한을 제한한다.

```toml
DATAGOKR_API_KEY = ""
DATAGOKR_REMOTE_URL = "https://datagokr.dev/mcp"
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

계정 페이지에서 로그인을 확인한 뒤 세션을 저장한다. macOS/Linux에서는 세션 파일 권한이 `0600`이고, Windows에서는 쿠키를 Credential Manager에 저장하고 파일에는 저장 위치 표시만 남긴다. `document.cookie`로는 HttpOnly 쿠키를 읽을 수 없으므로 복사한 값으로 검증이 실패하면 브라우저 쿠키 읽기 경로를 사용하거나 다시 로그인한다. 만료된 세션은 CLI의 `datagokr login` 또는 MCP의 `login`으로 갱신한다. MCP에서는 `login_status` 툴로 상태를 확인할 수 있다.

로컬 MCP에서는 터미널 없이 `login` 도구로 로그인할 수 있다. 확장 설정의 포털 아이디·비밀번호를 입력하거나 로컬 서버에 `DATAGOKR_PORTAL_ID`, `DATAGOKR_PORTAL_PASSWORD` 환경변수를 전달한다. 이 두 설정은 환경변수 전용이며 `config` 출력이나 개인 TOML에 넣지 않는다. 대화에 “공공데이터포털에 로그인해줘”라고 말하고, 표시된 보안문자를 직접 읽어 입력한다. 도구는 같은 `challenge_id`와 `captcha_answer`로 5분 안에 완료하며, 다시 시작하면 이전 이미지는 무효다. 아이디·비밀번호는 도구 인자에 넣지 않는다. 실제 포털 로그인과 Windows/macOS 앱 실행은 아직 실기 검증 전이다.

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
| `preview` | `datagokr preview 15012896 -n 3` | 키 없이 원격 서버에서 미리보기 |
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

로컬 `datagokr-mcp`가 stdio로 실행되며 툴 10개를 제공한다: `search`, `show`, `fields`, `preview`, `fetch`, `get`, `apply`, `download`, `login`, `login_status`. 툴 설명은 한국어·영어를 함께 제공한다. CLI의 `login`과 `config`도 유지하며, MCP에는 키·아이디·비밀번호·쿠키 입력 인자가 없다.

먼저 설치한 가상환경에서 `command -v datagokr-mcp`로 실행파일의 **절대경로**를 확인한다. 아래 예시는 `datagokr-mcp`가 AI 클라이언트의 PATH에도 있을 때 동작한다. 찾지 못하면 각 `command` 또는 CLI의 마지막 실행파일을 방금 확인한 절대경로로 바꾼다. JSON/TOML의 명령 경로에 `~` 확장을 기대하지 말자. `command`를 가상환경 Python 절대경로로 하고 `args`를 `["-m", "datagokr.mcp"]`로 지정해도 된다.

각 설정은 기존 파일의 다른 항목을 유지하며 병합한다. 키는 개인 `~/.config/datagokr/config.toml`에 두면 아래 예시에 비밀값을 넣지 않아도 된다. 등록 후 클라이언트에서 MCP 연결을 새로고침하거나 재시작한다.

### 클로드 웹·ChatGPT (커넥터, 1단계만)

로컬 프로그램을 돌릴 수 없는 앱이라 원격 서버만 커넥터로 붙인다(Claude 데스크탑은 아래 확장 파일이 낫다). Claude는 설정 → 커넥터 → 추가 → 사용자 지정 커넥터에서 이름은 아무거나, URL은 `https://datagokr.dev/mcp`(끝의 `/mcp`까지)를 넣고 연결한다. 고급 설정의 OAuth 클라이언트 ID·시크릿은 비워 둔다. 연결 과정의 승인은 로그인 화면 없이 자동으로 끝난다. ChatGPT(웹·앱)는 설정 → 통합 → 플러그인 → 추가 → MCP 앱 만들기에서 같은 URL을 넣고 인증은 OAuth로 둔다(메뉴 이름은 버전·요금제에 따라 다를 수 있다). 검색·구조 확인·미리보기(1단계)는 되고, 활용신청·본인 키 조회·전체 다운로드(2단계)는 안 된다. 필요하면 AI가 알려 주는 data.go.kr 페이지에서 직접 한다.

### Claude 데스크탑 (Windows·Mac)

1·2단계 모두 된다. 파일 하나로 이 컴퓨터에 검색·조회·활용신청·다운로드 도구를 설치한다. 최신 Claude 데스크탑 앱과 인터넷 연결이 필요하다.

1. [Releases](https://github.com/datagokr-dev/datagokr/releases/latest)에서 **datagokr.mcpb**를 받는다. [확장 파일 바로 받기](https://github.com/datagokr-dev/datagokr/releases/latest/download/datagokr.mcpb).
2. 받은 파일을 **더블클릭**하고 Claude 데스크탑에서 설치한다. Python과 필요한 패키지는 앱이 준비한다.
3. 설정 창에 본인의 **API 키·포털 아이디·비밀번호**를 입력한다. 모두 선택 사항이라 검색부터 하려면 비워 두어도 된다. API 키는 data.go.kr에 로그인 → 마이페이지 첫 화면의 "개인 API 인증키" 칸에서 **인증키 복사(Decoding)** 를 눌러 복사한 값이다(메뉴: 마이페이지 → 데이터 활용 → Open API → 인증키 발급현황).
4. 새 대화에서 “전국 주차장 데이터를 검색해줘”라고 말한다. 포털 로그인이 필요하면 “공공데이터포털에 로그인해줘”라고 말하고, 표시된 보안문자를 직접 읽어 입력한다. 비밀번호는 대화에 쓰지 않는다.
5. 활용신청·다운로드는 필요한 데이터셋을 확인한 뒤 대화로 요청한다. 받은 파일은 이 컴퓨터의 `~/datagokr/<dataset_id>/`에 저장한다.

API 키·로그인 정보는 사용자 컴퓨터에서 공식 서비스로 직접 전송한다. Linux VPS에서 번들 기동과 도구 목록을 확인했으며, Windows/macOS 앱 설치와 실제 포털 로그인은 실기 검증 전이다.

기존 수동 등록도 가능하다. 설치한 실행파일을 `claude_desktop_config.json`의 `mcpServers`에 `"datagokr-local": {"command": "/absolute/path/to/.venv/bin/datagokr-mcp"}`로 추가한다. 확장으로 설치했다면 같은 로컬 서버를 중복 등록할 필요가 없다.

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

search = datagokr.search("전국 주차장", n=5)
print(search["summary"])
datasets = search["results"]
details = datagokr.show("15012896")
result = datagokr.get("15012896", n=3, api_key="")
print(result["data"]["columns"])
print(result["data"]["rows"])
files = datagokr.download("15012896", out="./downloads")
```

`search`와 `fields`는 `{"summary": {...}, "results": [...]}` dict를 반환한다. 같은 주제의 지자체 자료는 대표 한 줄로 접힌다. 다음은 필드 의미를 보여 주는 축약 예시이며 건수·순위는 실제 검색에 따라 달라진다.

```json
{
  "summary": {
    "total_groups": 1,
    "total_datasets": 2,
    "by_dtype": {"FILE": 2},
    "by_access_kind": {"PORTAL_FILE": 2},
    "by_org_level": {"national": 0, "local": 2},
    "region_hint": null,
    "dtype_hint": null,
    "note": "지자체별로 나뉜 주제를 접었습니다. group_ids의 id를 show로 펼쳐 보세요."
  },
  "results": [{
    "id": "<대표 id>",
    "title": "부산광역시 북구_재난문자 발송 현황",
    "group_count": 2,
    "group_ids": ["<대표 id>", "<다른 지자체 id>"],
    "group_orgs": ["부산광역시 북구", "제주특별자치도"],
    "group_kinds": {"PORTAL_FILE": 2},
    "desc_short": "재난문자 발송 현황입니다.",
    "top_columns": ["발송일시", "내용"],
    "portal_updated": "2026-09-10",
    "org_level": "local"
  }]
}
```

`summary`는 `n`개로 자르기 전 **검색 후보**의 개요이며 전체 카탈로그 건수가 아니다. `group_count`는 대표를 포함한 후보 멤버 수, `group_ids`는 순위순 최대 60개 id다. 각 id를 `datagokr.show(dataset_id)`에 넣어 펼쳐 본다. `desc_short`는 설명 앞 120자에서 개행을 뺀 값, `top_columns`는 등록순 컬럼명 최대 5개, `portal_updated`는 ISO 날짜 또는 `null`, `org_level`은 `national` 또는 `local`이다. 지역·API/파일 의도는 서버가 추출하지만 `dtype`·`org` 인자를 주면 더 정확하다.

최상위 공개 함수는 `search`, `show`, `fields`, `preview`, `fetch`, `get`, `apply`, `download`다. `fields`에는 컬럼명 리스트, `apply`에는 id 리스트를 전달한다. 원격 주소는 `remote_url=`, 키를 사용하는 함수에는 `api_key=`로 설정을 덮어쓸 수 있다. `get`의 `no_apply`(기본 `True`, 신청 안 함)·`probe=True`와 `download`의 `probe=True`는 CLI와 같은 의미다. 반환값은 dict 또는 list이고 Python API는 동기 호출이다.

## 보안과 데이터 전송

### 원격 서버로 전송되는 것 / 안 되는 것

| 작업 | 원격 MCP 서버로 전송되는 것 | 원격 MCP 서버로 전송되지 않는 것 |
| --- | --- | --- |
| `search`·`show`·`fields`·`record`·`download_url` | 질의·필드 조건·식별자·건수 등 조회 인자만 | API 키·로그인 쿠키·로컬 파일 |
| `preview` (원격 `get_preview`) | 조회 인자만 | API 키·로그인 정보·쿠키·로컬 파일 |
| `get`·`fetch`·`apply`·`download` | `record`로 카탈로그 식별자 조회만 | 키·쿠키·신청 본문: 사용자 컴퓨터에서 포털/odcloud로 직접 전송; 파일은 로컬 저장 |

`record`·`download_url`은 원격 툴이며 최상위 Python API나 CLI 명령은 아니다. 로그인 쿠키는 어떤 경우에도 원격 MCP 서버로 보내지 않는다. AI 클라이언트에 반환한 데이터의 처리는 해당 클라이언트의 정책을 따른다.

- 검색어·필드 조건·데이터셋 id는 설정한 원격 MCP 서버로 전달된다. 서버는 검색·메타·원격 미리보기를 제공하며 원격 서버 자체는 활용신청이나 사용자 파일 저장을 하지 않는다.
- `preview`는 초기화·툴 목록 요청을 포함해 API 키를 보내지 않는다. 기존 `api_key=`·`--api-key` 인자는 호환성을 위해 받지만 미리보기에서는 사용하지 않는다. 키가 필요한 조회는 로컬 `get`/`fetch`를 사용한다.
- `get`/`fetch`의 API 키는 로컬에서 odcloud로 전달된다. 포털 로그인 쿠키는 사용자 세션 파일에 저장하고 포털 접속에 사용하며 원격 검색 MCP에는 보내지 않는다. 다운로드는 MCP 서버 프로세스가 실행되는 컴퓨터에 저장된다.
- CLI/MCP는 키·쿠키를 출력하거나 오류 메시지에 포함하지 않도록 처리한다. 하지만 사용자가 직접 인쇄하거나 HTTP 디버그 로깅을 켜거나 명령줄 인자에 비밀값을 넣으면 노출될 수 있다. 키·쿠키를 AI 대화, 버그 보고, 커밋에 붙여 넣지 않는다.
- 포털 로그인 아이디·비밀번호는 이 컴퓨터에서 `auth.data.go.kr`로 직접 전송한다. 로그인 이동은 `auth.data.go.kr`·`www.data.go.kr`의 HTTPS만 허용하고, 포털 계정 페이지와 저장할 쿠키의 재사용을 확인한 뒤 성공을 반환한다. 보안문자 이미지는 AI 클라이언트에 표시하므로 사용자가 직접 읽어 입력한다.
- 세션은 macOS/Linux에서 `0600` 파일, Windows에서 Credential Manager에 저장한다. `.env`·개인 설정 파일도 접근 권한을 제한하고 버전 관리에서 제외한다. 원격 주소를 변경하면 그 서버가 검색 입력을 받으므로 신뢰하는 HTTPS 주소를 사용한다.
- `get`은 기본적으로 자동 활용신청을 하지 않으며 파일 저장으로 폴백할 수 있다. `get --apply`로 신청을 허용할 수 있고, `apply`는 신청 제출, `download`는 파일 저장을 수행한다. `get`/`download`는 같은 파일을 덮어쓸 수 있다. 조회만 원하면 `probe` 옵션을 사용한다.

## 데이터 출처와 이용조건

데이터 출처는 [공공데이터포털(data.go.kr)](https://www.data.go.kr/)과 각 제공기관이다. 데이터셋별 이용허락(공공누리 유형, 출처표시 등)은 검색 결과의 `page_url`에 표시된 조건을 따른다. 이 패키지와 원격 서버는 카탈로그 색인과 접근 안내를 제공하며, 미리보기·조회·다운로드로 받은 데이터의 별도 이용권을 부여하지 않는다. 패키지의 [MIT 라이선스](LICENSE)는 코드에 적용되고 데이터셋의 이용조건을 대체하지 않는다.

## 레이트리밋

공개 원격 서버는 **IP당 최근 60초 30회, UTC 날짜당 2,000회** HTTP 요청을 허용한다. 초기화·툴 목록 요청도 포함되며 `/health`는 제외된다. 전체 IP 합계 제한(최근 60초 120회·최근 24시간 10,000회)도 적용된다. HTTP 429를 받으면 `Retry-After`만큼 기다린다. 패키지는 이를 읽어 한 번 재시도한다. 자체 호스팅 서버의 한도는 운영 설정에 따라 달라질 수 있다.

## 문제 신고

오류·문서 수정·서비스 문의는 [GitHub Issues](https://github.com/datagokr-dev/datagokr/issues)에 남긴다. 패키지 버전과 재현 명령, 비밀값을 제거한 오류를 함께 적고 API 키·로그인 쿠키·개인 설정 파일은 첨부하지 않는다.

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
