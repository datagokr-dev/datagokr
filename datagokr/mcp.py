"""Local stdio tools for remote discovery and user-owned portal access."""

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware

import datagokr
from datagokr import session
from datagokr.apply import PURPOSE_DEFAULT


class _SafeErrors(Middleware):
    async def on_call_tool(self, context, call_next):
        try:
            return await call_next(context)
        except Exception:
            # Validation failures can contain supplied values as well as HTTP URLs.
            raise ToolError(
                "요청 실패. 인자·설정·네트워크를 확인하세요. 로그인은 datagokr login 을 사용하세요. "
                "Request failed; check arguments, configuration and connectivity. "
                "For portal login, run datagokr login."
            ) from None


mcp = FastMCP("datagokr", mask_error_details=True, middleware=[_SafeErrors()],
    instructions="공공데이터 검색 → show → preview 또는 get. 설정은 DATAGOKR_* 환경변수나 설정 파일. "
    "Search Korean public datasets, inspect with show, then preview or get. "
    "Configure credentials locally via DATAGOKR_* settings; never put keys or cookies in tool arguments. "
    "get may apply for access and save files; download saves files on this computer.")


@mcp.tool(annotations={"readOnlyHint": True})
def search(query: str, n: int = 10, dtype: str | None = None,
           org: str | None = None, fields: list[str] | None = None) -> list[dict]:
    """주제로 공공데이터를 원격 검색합니다. Search the remote catalog by topic.
    query: 자연어 / topic; n: 1~20; dtype: FILE/API/STD; org: 기관명 / provider;
    fields: 모두 필요한 컬럼 / required columns. 반환 / Returns: ranked id, title,
    org_nm, access_kind, page_url, matched_fields. 예시 / Example: query='전국 주차장'.
    """
    return datagokr.search(query, n=n, dtype=dtype, org=org, fields=fields)


@mcp.tool(annotations={"readOnlyHint": True})
def show(dataset_id: str) -> dict:
    """검색한 데이터셋의 구조·사용법을 확인합니다. Inspect dataset metadata before use.
    반환 / Returns: title, org_nm, access_kind, columns, operations, examples, page_url.
    dataset_id는 검색 결과의 id입니다. Use the id from search; use get for actual rows.
    """
    return datagokr.show(dataset_id)


@mcp.tool(annotations={"readOnlyHint": True})
def fields(names: list[str], n: int = 10, dtype: str | None = None,
           org: str | None = None) -> list[dict]:
    """지정 컬럼을 모두 가진 데이터셋을 찾습니다. Find datasets matching ALL named columns.
    names 예시 / Example: ['위도', '경도']; n: 1~20; dtype: FILE/API/STD; org: 기관명.
    반환은 search와 같은 메타데이터입니다. Returns ranked metadata as in search.
    """
    return datagokr.fields(names, n=n, dtype=dtype, org=org)


@mcp.tool(annotations={"readOnlyHint": True})
def preview(dataset_id: str, n: int = 5) -> dict:
    """원격 서버에서 첫 행·접근 안내를 조회합니다. Preview up to 20 rows remotely.
    반환 / Returns: access_kind, data.columns/rows, total or access instructions.
    설정된 본인 키는 원격 서버의 X-DataGoKr-Key 헤더로 전송됩니다. The configured API key
    is sent to the remote server in X-DataGoKr-Key. 신청·저장 없음 / No application or file saving.
    """
    return datagokr.preview(dataset_id, n=n)


@mcp.tool(annotations={"readOnlyHint": True})
def fetch(dataset_id: str, version: str | None = None, n: int = 5) -> dict:
    """본인 로컬 키로 odcloud 첫 n행을 조회합니다. Fetch rows locally with DATAGOKR_API_KEY.
    version 생략 시 최신 / latest version by default. 반환 / Returns: API data or
    request_templates; status_code=401 means access must be requested. STD_FILE은 get/download.
    활용신청·파일 저장은 하지 않습니다. Does not apply for access or save files.
    """
    return datagokr.fetch(dataset_id, version=version, n=n)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True})
def get(dataset_id: str, n: int = 5, no_apply: bool = False, probe: bool = False) -> dict:
    """접근방식에 따라 첫 행·링크·API 템플릿을 돌려줍니다. Get rows, links or API templates.
    PORTAL_FILE은 401에서 본인 세션으로 활용신청 후 재시도하며 원문 파일 저장으로 폴백할 수 있습니다.
    May apply with your saved login on 401, retry and fall back to saving a local file.
    no_apply=True는 신청만 생략(파일 저장 가능). no_apply skips applications, but may still save files.
    probe=True는 신청·파일 저장 없이 확인. probe checks access without applying or saving files.
    반환 / Returns: access_kind with data, url, request_templates or files (local paths).
    """
    return datagokr.get(dataset_id, n=n, no_apply=no_apply, probe=probe)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
def apply(ids: list[str], purpose: str = PURPOSE_DEFAULT) -> list[dict]:
    """본인의 저장된 포털 세션으로 활용신청을 제출합니다. Submit access applications with saved login.
    ids: 1~50개 데이터셋 id; purpose: 활용 목적 / intended use. 로그인: datagokr login.
    반환 / Returns: id, status, portal_status, page_url; manual means login is required.
    쿠키는 포털에만 전송됩니다. Cookies are sent only to the portal.
    """
    return datagokr.apply(ids, purpose=purpose)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True})
def download(dataset_id: str, version: str | None = None, all_versions: bool = False,
             out: str | None = None, utf8: bool = False, probe: bool = False) -> list[dict]:
    """원문을 이 컴퓨터에 저장합니다(같은 경로는 덮어씀). Save originals locally, overwriting the same path.
    version 또는 all_versions 중 하나 / choose version or all_versions; out: 이번 저장 폴더,
    기본 DATAGOKR_DOWNLOAD_DIR / destination directory; utf8: CSV UTF-8 변환본 추가.
    probe=True는 저장 없이 확인합니다. probe checks without saving. 반환 / Returns: files with
    path, version, optional utf8_path, or an external url; STD_FILE is saved as a full CSV.
    """
    return datagokr.download(dataset_id, version=version, all_versions=all_versions,
                             out=out, utf8=utf8, probe=probe)


@mcp.tool(annotations={"readOnlyHint": True})
def login_status() -> dict:
    """저장된 포털 세션의 유효성을 확인합니다. Check whether the saved portal login is valid.
    반환 / Returns: authenticated, message. 세션이 없거나 만료되면 datagokr login 안내.
    Missing or expired sessions require datagokr login. Keys and cookies are never returned.
    """
    return session.login_status()


def main():
    # Transport and validation logs may include credentials or supplied arguments.
    for name in ("fastmcp", "mcp", "httpx", "httpcore", "urllib3"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    mcp.run(transport="stdio", show_banner=False, log_level="CRITICAL")


if __name__ == "__main__":
    main()
