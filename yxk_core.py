# -*- coding: utf-8 -*-
"""易学酷平台公共逻辑。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

import requests

GATEWAY = "https://gwssl.cmnt.cn"
SITE = "https://yxk.cmnt.cn"
HEADERS = {
    "Origin": SITE,
    "Referer": f"{SITE}/login",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

CODE_SUCCESS = "000000"
CODE_PASSWORD_ERROR = "10013"

# 登录接口中可能因服务端瞬时故障而可重试的业务码
RETRIABLE_API_CODES = {"500", "503", "504", "9999", "99999"}


class LoginStatus(str, Enum):
    SUCCESS = "成功"
    PASSWORD_ERROR = "账号密码错误"
    CAPTCHA_ERROR = "验证码失败"
    EMPTY = "账号或密码为空"
    OTHER_ERROR = "其他错误"


@dataclass
class AccountRow:
    username: str
    password: str
    remark: str = ""
    row_no: int = 0


@dataclass
class QueryResult:
    username: str
    password: str
    remark: str = ""
    row_no: int = 0
    status: LoginStatus = LoginStatus.OTHER_ERROR
    real_name: str = ""
    id_card: str = ""
    org_name: str = ""
    title_name: str = ""
    title_code: str = ""
    error_msg: str = ""
    login_mode: str = "API直连登录"
    retry_count: int = 0
    retriable: bool = False

    @property
    def is_problem(self) -> bool:
        return self.status != LoginStatus.SUCCESS

    @property
    def problem_label(self) -> str:
        if self.status == LoginStatus.PASSWORD_ERROR:
            return "⚠ 账号密码有问题"
        if self.is_problem:
            return "⚠ 需处理"
        return ""

    @property
    def sort_key(self) -> tuple[int, int]:
        priority = {
            LoginStatus.PASSWORD_ERROR: 0,
            LoginStatus.EMPTY: 1,
            LoginStatus.CAPTCHA_ERROR: 2,
            LoginStatus.OTHER_ERROR: 3,
            LoginStatus.SUCCESS: 9,
        }
        return priority.get(self.status, 8), self.row_no


def md5_password(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def load_title_dict(token: str | None = None) -> dict[str, list[dict[str, Any]]]:
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = token
    resp = requests.get(
        f"{GATEWAY}/system/v1/open/dictionary/cache",
        headers=headers,
        timeout=20,
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get("data") or {}


def load_title_dict_with_retry(
    token: str | None = None,
    *,
    max_attempts: int = 3,
    on_retry: Callable[[int, str], None] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    from yxk_retry import calc_backoff, is_retriable_exception
    import time

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return load_title_dict(token)
        except Exception as exc:
            last_exc = exc
            if not is_retriable_exception(exc) or attempt >= max_attempts:
                raise
            if on_retry:
                on_retry(attempt, str(exc))
            time.sleep(calc_backoff(attempt))
    raise last_exc  # pragma: no cover


def resolve_title_name(title_code: str, title_dict: dict[str, list[dict[str, Any]]]) -> str:
    for item in title_dict.get("ID_TITLE", []):
        if item.get("itemCode") == title_code:
            return str(item.get("itemName") or title_code)
    return title_code


def is_retriable_api_response(code: str, msg: str) -> bool:
    if code in RETRIABLE_API_CODES:
        return True
    lowered = msg.lower()
    transient_words = ("维护", "繁忙", "超时", "稍后", "系统异常", "服务不可用", "503", "502", "504")
    return any(word in lowered for word in transient_words)


def build_result_from_login(
    account: AccountRow,
    login_body: dict[str, Any],
    title_dict: dict[str, list[dict[str, Any]]],
) -> QueryResult:
    code = str(login_body.get("code", ""))
    msg = str(login_body.get("msg") or "")

    if code == CODE_PASSWORD_ERROR:
        return QueryResult(
            username=account.username,
            password=account.password,
            remark=account.remark,
            row_no=account.row_no,
            status=LoginStatus.PASSWORD_ERROR,
            error_msg=msg or "用户名或密码错误，请重新登录",
            retriable=False,
        )

    if code != CODE_SUCCESS:
        return QueryResult(
            username=account.username,
            password=account.password,
            remark=account.remark,
            row_no=account.row_no,
            status=LoginStatus.OTHER_ERROR,
            error_msg=msg or f"登录失败(code={code})",
            retriable=is_retriable_api_response(code, msg),
        )

    data = login_body.get("data") or {}
    user = data.get("user") or {}
    title_code = str(user.get("title") or "")
    return QueryResult(
        username=account.username,
        password=account.password,
        remark=account.remark,
        row_no=account.row_no,
        status=LoginStatus.SUCCESS,
        real_name=str(user.get("realName") or ""),
        id_card=str(user.get("cardNo") or ""),
        org_name=str(user.get("unitName") or ""),
        title_code=title_code,
        title_name=resolve_title_name(title_code, title_dict),
    )
