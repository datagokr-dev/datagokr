"""Command-line access to the public catalog and the user's local data."""

import argparse
import json
from getpass import getpass
import sys

import datagokr
from datagokr import config, session
from datagokr.apply import PURPOSE_DEFAULT

PROMPT_COOKIE = object()


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's original message may echo a cookie or key supplied by mistake.
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 인자 형식을 확인하세요. {self.prog} --help\n")


def _positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("양의 정수가 필요합니다.")
    return number


def _parser():
    output = argparse.ArgumentParser(add_help=False)
    output.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="JSON 출력 / machine-readable JSON")
    parser = _Parser(prog="datagokr", parents=[output],
                     description="공공데이터 검색·조회·로컬 다운로드 / Korean public data")
    parser.add_argument("--version", action="version", version=datagokr.__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    descriptions = dict(search="주제 검색 / search by topic", show="구조·사용법 / dataset details",
        fields="모든 지정 컬럼으로 검색 / find datasets by columns", preview="원격 미리보기 / remote preview",
        fetch="본인 키로 odcloud 호출 / local API request", get="미리보기·신청·원문 폴백 / unified access",
        apply="저장된 로그인으로 활용신청 / apply for access", download="로컬 파일 저장 / download files",
        login="포털 로그인 / portal login", config="설정 조회 (키 숨김) / display effective settings")
    for name, description in descriptions.items():
        cmd = commands.add_parser(name, parents=[output], help=description, description=description)
        if name not in ("login", "config"):
            cmd.add_argument("--remote-url", help="원격 MCP 주소 (기본: DATAGOKR_REMOTE_URL)")
        if name in ("search", "fields"):
            cmd.add_argument("query" if name == "search" else "names", **({} if name == "search" else {"nargs": "+"}))
            cmd.add_argument("-n", type=_positive, default=10)
            cmd.add_argument("--dtype", choices=("FILE", "API", "STD"))
            cmd.add_argument("--org")
            if name == "search":
                cmd.add_argument("--field", action="append", dest="fields", help="필수 컬럼 (반복 가능)")
        elif name in ("show", "preview", "fetch", "get", "download"):
            cmd.add_argument("dataset_id")
        if name in ("preview", "fetch", "get"):
            cmd.add_argument("-n", type=_positive, default=5)
            cmd.add_argument("--api-key", help="본인 odcloud 키 (환경변수 DATAGOKR_API_KEY 권장)")
        if name == "fetch":
            cmd.add_argument("--version", help="파일 버전 식별자")
        if name == "get":
            cmd.add_argument("--apply", action="store_true", help="401이면 본인 계정으로 활용신청까지 진행 (기본은 신청 안 함)")
        if name in ("get", "download"):
            cmd.add_argument("--probe", action="store_true", help="파일 저장·신청 없이 접근 확인")
            cmd.add_argument("--download-dir", help="기본 저장 폴더 (DATAGOKR_DOWNLOAD_DIR)")
        if name in ("get", "apply", "login"):
            cmd.add_argument("--session-file", help="포털 세션 파일 (DATAGOKR_SESSION_FILE)")
        if name == "apply":
            cmd.add_argument("ids", nargs="+")
            cmd.add_argument("--purpose", default=PURPOSE_DEFAULT)
        if name == "download":
            versions = cmd.add_mutually_exclusive_group()
            versions.add_argument("--version")
            versions.add_argument("--all-versions", action="store_true")
            cmd.add_argument("--out", help="이번 다운로드 저장 폴더")
            cmd.add_argument("--utf8", action="store_true", help="CSV의 UTF-8 변환본도 저장")
        if name == "login":
            login = cmd.add_mutually_exclusive_group()
            login.add_argument("--cookie", nargs="?", const=PROMPT_COOKIE, help="로그인한 브라우저의 document.cookie 값. 값을 생략하면 숨김 입력")
            login.add_argument("--browser", choices=("chrome", "safari", "firefox"))
            cmd.epilog = session.login_instructions()
        if name == "config":
            for setting in config.KEYS:
                cmd.add_argument("--" + setting.removeprefix("DATAGOKR_").lower().replace("_", "-"))
            cmd.epilog = ("우선순위: 명령 인자 > 환경변수 > ./.env > ~/.config/datagokr/config.toml. "
                          "파일에는 DATAGOKR_* 키를 사용하세요. 이 명령은 설정을 조회합니다.")
    return parser


def _display(result, command, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, default=str))
    elif command == "login":
        print(result["message"])
    elif command == "config":
        for key, value in result.items():
            print(f"{key}={value}")
    elif command in ("search", "fields"):
        for row in result:
            print(f"{row.get('rank', '')}. {row['id']} [{row.get('dtype', '')}] "
                  f"{row.get('title', '')} | {row.get('org_nm', '')}")
            for key in ("page_url", "access_note"):
                if row.get(key):
                    print(f"  {row[key]}")
        if not result:
            print("검색 결과가 없습니다.")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main(argv=None):
    args = vars(_parser().parse_args(argv))
    command, as_json = args.pop("command"), args.pop("json", False)
    if command == "get":
        args["no_apply"] = not args.pop("apply", False)
    if command == "login" and args.get("cookie") is PROMPT_COOKIE:
        args["cookie"] = getpass("포털 쿠키 (입력 숨김): ")
    try:
        if command == "config":
            result = config.load(**args).as_dict()
        elif command == "login":
            result = session.login(**args)
        else:
            result = getattr(datagokr, command)(**args)
        _display(result, command, as_json)
    except Exception:
        # Neither HTTP exception URLs nor arbitrary response text are safe to echo.
        message = "요청 실패. 설정과 네트워크를 확인하고 잠시 후 다시 시도하세요."
        if command == "login":
            message = ("로그인 확인 또는 세션 저장 실패. datagokr login 으로 다시 로그인하세요.\n"
                       + session.login_instructions()
                       + '\n브라우저 쿠키 지원 설치: pip install "datagokr[browser]"')
        elif command == "fetch":
            message = "요청 실패. DATAGOKR_API_KEY·버전·활용신청을 확인하거나 datagokr get 으로 조회하세요."
        elif command == "config":
            message = "설정을 읽을 수 없습니다. ./.env 및 ~/.config/datagokr/config.toml 형식을 확인하세요."
        print(json.dumps(dict(error=message, command=command), ensure_ascii=False)
              if as_json else message, file=sys.stderr)
        return 1
    return 0
