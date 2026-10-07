# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

이 저장소는 두 부분을 기록합니다.

- **원격 서버** (`https://datagokr.dev/mcp`): 설치 없이 바로 연결해 쓰는 검색 서버입니다. 서버 코드는 공개하지 않고, 쓰는 사람이 체감하는 변경만 날짜별로 적습니다.
- **로컬 패키지** (PyPI `datagokr-mcp`, Claude 데스크탑 확장 `datagokr.mcpb`): 이 저장소의 코드입니다. 버전별로 적습니다.

## 원격 서버

### 2026-10-07

- `search` 툴 설명을 짧게 다듬었습니다(1,024자 이내). 검색 요령은 서버 안내문에 그대로 있습니다.

### 2026-10-01

- claude.ai·ChatGPT 앱에서 커스텀 커넥터로 연결할 수 있습니다(익명 연결, 로그인·개인정보 불필요).
- `https://datagokr.dev`(루트 주소)로 등록해도 MCP로 연결됩니다.
- 툴 설명에 서비스명과 동작 힌트(읽기 전용·반복 호출 안전·외부 데이터 조회)를 보강했습니다.
- 서버 안내문에 1단계(찾기·확인)와 2단계(활용신청·전체 다운로드, 로컬 패키지 필요)를 구분해 넣었습니다.

### 2026-09-30

- 검색할 때 벡터 후보를 더 넓게 훑어서, 정답이 있는데도 결과에서 빠지던 경우를 줄였습니다.
- 카탈로그를 대량으로 갱신한 직후 검색 품질이 일시적으로 떨어지던 문제를 고쳤습니다.

### 2026-09-29

- UTF-8이 아닌 요청 본문(예: 윈도우 기본 콘솔에서 한글로 보낸 curl)에 500 오류 대신 400과 인코딩 안내를 돌려줍니다.
- 같은 주제의 자료를 묶을 때, 질문에 가장 잘 맞는 자료를 대표로 보여줍니다.
- 지역·자료형 가산점이 원래 상위권 결과를 10위 밖으로 밀어내지 않도록 했습니다.
- "핫한", "맛집", "인기" 같은 평가 표현에는 공공데이터에 없는 정보라는 안내와 대신 찾을 지표(인허가 목록, 매출·유동인구 등)를 함께 줍니다.
- 구 단위 지역 자료(예: 서울 강남구)가 있는데도 "해당 지역 자료 없음"으로 안내하던 문제를 고쳤습니다.
- 자료별로 받는 방법(파일·오픈 API·외부 링크·표준데이터)을 구분해 안내합니다.

### 2026-09-28

- '율/률' 표기 차이를 같은 말로 봅니다(예: 공실율 = 공실률).
- 지역이 들어간 질문에서 지역명 때문에 엉뚱한 주제가 올라오던 경우를 줄였습니다(주제만으로 한 번 더 찾아 합칩니다).
- 지역 가산점은 기관명·제목에 그 지역 근거가 있을 때만 줍니다.
- 툴 제목, 개인정보 처리 안내(`/privacy`), 아이콘을 추가하고 공식 MCP 레지스트리에 등록했습니다.

### 2026-09-27

- 검색이 빨라졌습니다(평균 약 2.9초 → 0.6초).
- `show` 응답을 20KB 안으로 맞추고, 잘린 경우 표시와 이어 보는 방법을 함께 줍니다.
- `get_preview`의 행 형태를 통일했습니다(`columns` 순서의 값 배열).
- 지역 자료가 없을 때 대신 보여주는 전국 결과에서도 요청한 컬럼 조건을 유지합니다.
- 법령 내용을 묻는 질문에는 법령 데이터셋을 안내합니다.
- 브라우저로 `/mcp`를 열면(GET) 405와 함께 연결 방법을 안내합니다.

### 2026-09-22

- 툴 호출 기록에 툴 이름·결과·인자(검색어 등, 200자까지)를 남깁니다. API 키는 기록하지 않습니다. README의 "기록하는 것" 표에 반영했습니다.

### 2026-09-15

- 서버 안내문과 툴 설명을 "언제 쓰는지" 중심으로 다시 썼습니다.

### 2026-09-10

- 같은 자료의 연도·버전별 중복을 하나로 묶어 보여줍니다.
- 질문 의도(API인지 파일인지, 어느 지역인지)를 순위에 반영합니다.
- 동의어로 질문을 넓혀 찾습니다.
- 컬럼 이름으로 자료를 찾는 `fields`를 추가했습니다.
- 지역 자료가 없으면 그 사실을 알리고 전국 자료를 대신 찾습니다.

### 2026-09-09

- 공개 출시: `search`, `show`, `fields`, `record`, `get_preview`, `download_url`. 읽기 전용이며 키 없이 쓸 수 있습니다.

## 로컬 패키지

### [0.1.5] - 2026-10-01

- Extension settings explain where to copy the data.go.kr API key (My Page → 개인 API 인증키 → 인증키 복사(Decoding)).

### [0.1.4] - 2026-10-01

- Portal login opens the CAPTCHA image in the system viewer, since Claude Desktop folds tool output.

### [0.1.3] - 2026-10-01

- Claude Desktop extension (`datagokr.mcpb`) with a uv runtime and optional sensitive settings.
- Local two-step portal login with a user-read CAPTCHA; existing CLI login remains available.
- Remote previews no longer forward API keys; Windows sessions use Credential Manager.
- Desktop download/install instructions and matching package, CLI, and extension versions.

### [0.1.2] - 2026-09-29

- README: 로컬 패키지가 왜 필요한지·사용자 컴퓨터에서 무엇이 실행되고 무엇이 오가는지 설명 절과 표 추가
- README: PyPI·CI·라이선스·MCP 레지스트리 배지

### [0.1.0] - 2026-09-09

#### Added

- Public catalog search, dataset details, field search, and remote previews.
- Local data access with the user's own API key, portal session, and disk:
  fetch, access guidance, explicit portal applications, and downloads.
- A Python API, the `datagokr` CLI, and the `datagokr-mcp` stdio server.
- Configuration through arguments, environment variables, `.env`, and TOML.
- Python 3.11/3.12 CI, data provenance, privacy, and rate-limit documentation.

#### Security

- `get` disables automatic portal applications by default (`no_apply=True`);
  opting in requires CLI `--apply` or Python/MCP `no_apply=False`.
- Login cookies stay on the user's computer and are sent directly to the portal.
- Only remote `preview` forwards a configured API key in `X-DataGoKr-Key`;
  local access operations send keys directly to the portal/odcloud.

[0.1.5]: https://github.com/datagokr-dev/datagokr/releases/tag/v0.1.5
[0.1.4]: https://github.com/datagokr-dev/datagokr/releases/tag/v0.1.4
[0.1.3]: https://github.com/datagokr-dev/datagokr/releases/tag/v0.1.3
[0.1.0]: https://github.com/datagokr-dev/datagokr/releases/tag/v0.1.0
