# -*- coding: utf-8 -*-
"""重试策略：仅对可恢复的 transient 错误重试。"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout

from yxk_core import LoginStatus, QueryResult

T = TypeVar("T")

# 最大尝试次数（含首次）
MAX_ATTEMPTS = 3
BACKOFF_BASE_SEC = 1.5
BACKOFF_MAX_SEC = 8.0

# 错误信息中的可重试关键词（大小写不敏感）
TRANSIENT_MSG_KEYWORDS = (
    "timeout",
    "timed out",
    "超时",
    "net::",
    "err_connection",
    "err_internet",
    "err_network",
    "connection reset",
    "connection aborted",
    "connection refused",
    "temporarily unavailable",
    "未捕获到登录接口响应",
    "未找到滑块验证码配置",
    "无法获取滑块位置",
    "无法解析登录响应",
    "target page",
    "target closed",
    "navigation failed",
    "page crashed",
    "系统维护",
    "系统异常",
    "服务不可用",
    "服务器",
    "请稍后",
    "繁忙",
    "503",
    "502",
    "504",
)

def _contains_transient_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in TRANSIENT_MSG_KEYWORDS)


def is_retriable_exception(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            TimeoutError,
            ConnectionError,
            RequestsTimeout,
            RequestsConnectionError,
        ),
    ):
        return True
    return _contains_transient_keyword(str(exc))


def is_retriable_result(result: QueryResult) -> bool:
    if result.status == LoginStatus.SUCCESS:
        return False
    if result.status in (LoginStatus.PASSWORD_ERROR, LoginStatus.EMPTY):
        return False
    if result.status == LoginStatus.CAPTCHA_ERROR:
        return True
    if result.retriable:
        return True
    if result.status == LoginStatus.OTHER_ERROR:
        return _contains_transient_keyword(result.error_msg)
    return False


def calc_backoff(attempt: int) -> float:
    """attempt 从 1 开始，表示第几次重试前的等待。"""
    delay = min(BACKOFF_BASE_SEC ** attempt, BACKOFF_MAX_SEC)
    jitter = random.uniform(0, delay * 0.25)
    return delay + jitter


def run_with_retry(
    action: Callable[[], T],
    *,
    is_retriable: Callable[[T], bool],
    max_attempts: int = MAX_ATTEMPTS,
    on_retry: Callable[[int, T], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    last: T | None = None
    for attempt in range(1, max_attempts + 1):
        last = action()
        if not is_retriable(last) or attempt >= max_attempts:
            return last
        if on_retry:
            on_retry(attempt, last)
        sleep(calc_backoff(attempt))
    assert last is not None
    return last
