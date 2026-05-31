# -*- coding: utf-8 -*-
"""纯 API 登录（无需浏览器，密码 MD5 后直连网关）。"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests
from requests.exceptions import RequestException

from yxk_account_parse import generate_login_variants
from yxk_core import (
    AccountRow,
    GATEWAY,
    HEADERS,
    LoginStatus,
    QueryResult,
    build_result_from_login,
    md5_password,
)
from yxk_retry import MAX_ATTEMPTS, calc_backoff, is_retriable_exception, is_retriable_result

LOGIN_URL = f"{GATEWAY}/auth/v1/open/loginValid/login"


def _login_by_api_once(
    session: requests.Session,
    account: AccountRow,
    title_dict: dict[str, Any],
) -> QueryResult:
    if not account.username.strip() or not account.password.strip():
        return QueryResult(
            username=account.username,
            password=account.password,
            remark=account.remark,
            row_no=account.row_no,
            status=LoginStatus.EMPTY,
            error_msg="账号或密码不能为空",
            login_mode="API直连登录",
            retriable=False,
        )

    payload = {
        "username": account.username.strip(),
        "password": md5_password(account.password),
    }
    resp = session.post(LOGIN_URL, json=payload, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    result = build_result_from_login(account, body, title_dict)
    result.login_mode = "API直连登录"
    return result


def login_by_api(
    account: AccountRow,
    title_dict: dict[str, Any],
    *,
    session: requests.Session | None = None,
    on_retry: Callable[[int, QueryResult | str], None] | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> QueryResult:
    """带重试的 API 登录，仅对可重试错误自动重试。"""
    sess = session or requests.Session()
    last_result: QueryResult | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            last_result = _login_by_api_once(sess, account, title_dict)
        except RequestException as exc:
            if not is_retriable_exception(exc) or attempt >= max_attempts:
                return QueryResult(
                    username=account.username,
                    password=account.password,
                    remark=account.remark,
                    row_no=account.row_no,
                    status=LoginStatus.OTHER_ERROR,
                    error_msg=str(exc),
                    login_mode="API直连登录",
                    retriable=False,
                    retry_count=attempt - 1,
                )
            if on_retry:
                on_retry(attempt, str(exc))
            time.sleep(calc_backoff(attempt))
            continue

        last_result.retry_count = attempt - 1
        if not is_retriable_result(last_result) or attempt >= max_attempts:
            return last_result

        if on_retry:
            on_retry(attempt, last_result)
        time.sleep(calc_backoff(attempt))

    assert last_result is not None
    return last_result


def login_by_api_adaptive(
    account: AccountRow,
    title_dict: dict[str, Any],
    *,
    session: requests.Session | None = None,
    on_retry: Callable[[int, QueryResult | str], None] | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> QueryResult:
    """API 登录；账号密码错误时自动尝试互换、符号纠正等识别变体。"""
    variants = generate_login_variants(
        account.username,
        account.password,
        raw=account.raw_input,
    )
    if not variants:
        return login_by_api(
            account,
            title_dict,
            session=session,
            on_retry=on_retry,
            max_attempts=max_attempts,
        )

    last_result: QueryResult | None = None
    total_variants = len(variants)

    for index, (username, password, label) in enumerate(variants):
        trial = AccountRow(
            username=username,
            password=password,
            remark=account.remark,
            row_no=account.row_no,
            raw_input=account.raw_input,
        )
        result = login_by_api(
            trial,
            title_dict,
            session=session,
            on_retry=on_retry,
            max_attempts=max_attempts,
        )
        last_result = result

        if result.status == LoginStatus.SUCCESS:
            result.username = username
            result.password = password
            if label != "初始识别":
                note = f"识别纠正: {label}"
                result.error_msg = note if not result.error_msg else f"{result.error_msg} ({note})"
            return result

        if result.status != LoginStatus.PASSWORD_ERROR:
            return result

        if index + 1 < total_variants and on_retry:
            next_label = variants[index + 1][2]
            on_retry(index + 1, f"账号密码错误，尝试{next_label}")

    assert last_result is not None
    return last_result
