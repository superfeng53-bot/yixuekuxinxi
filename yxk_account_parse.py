# -*- coding: utf-8 -*-
"""账号密码合并字段解析与登录变体生成。"""

from __future__ import annotations

import re
from typing import Iterable

# 空格、逗号、分号、竖线、斜杠、冒号、顿号、制表符、换行等
SEPARATOR_PATTERN = re.compile(r"[\s,，;；|/\\:：、]+")

FULLWIDTH_PUNCT_MAP = str.maketrans(
    {
        "，": ",",
        "。": ".",
        "；": ";",
        "：": ":",
        "　": " ",
        "／": "/",
        "＼": "\\",
        "｜": "|",
        "、": ",",
        "＠": "@",
    }
)

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
ID_CARD_PATTERN = re.compile(r"^\d{17}[\dXx]$")

ACCOUNT_LABEL = r"(?:账号|帐号|用户名|账户|帐户|user(?:name)?|account)"
PASSWORD_LABEL = r"(?:密码|口令|pass(?:word)?|pwd)"
VALUE_TRIM_PATTERN = re.compile(r"^[\s,，;；|/\\:：、]+|[\s,，;；|/\\:：、]+$")

LABELED_ACCOUNT_FIRST = re.compile(
    rf"{ACCOUNT_LABEL}\s*[:：]?\s*(?P<user>.+?)\s*{PASSWORD_LABEL}\s*[:：]?\s*(?P<pwd>.+)",
    re.IGNORECASE,
)
LABELED_PASSWORD_FIRST = re.compile(
    rf"{PASSWORD_LABEL}\s*[:：]?\s*(?P<pwd>.+?)\s*{ACCOUNT_LABEL}\s*[:：]?\s*(?P<user>.+)",
    re.IGNORECASE,
)
LABELED_ACCOUNT_ONLY = re.compile(
    rf"{ACCOUNT_LABEL}\s*[:：]\s*(?P<user>.+)",
    re.IGNORECASE,
)
LABELED_PASSWORD_ONLY = re.compile(
    rf"{PASSWORD_LABEL}\s*[:：]\s*(?P<pwd>.+)",
    re.IGNORECASE,
)


def normalize_symbols(text: str) -> str:
    """全角字符、中英文标点归一化为半角常用形式。"""
    if not text:
        return ""
    result: list[str] = []
    for ch in text:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif code == 0x3000:
            result.append(" ")
        else:
            result.append(ch)
    return "".join(result).translate(FULLWIDTH_PUNCT_MAP).strip()


def _clean_credential_value(value: str) -> str:
    text = normalize_symbols(value).strip()
    return VALUE_TRIM_PATTERN.sub("", text).strip()


def _parse_labeled_credentials(text: str) -> tuple[str, str] | None:
    """解析带“账号/密码”字样的文本，如 账号：2345密码ddd123。"""
    normalized = normalize_symbols(text)
    if not normalized:
        return None

    match = LABELED_ACCOUNT_FIRST.search(normalized)
    if match:
        user = _clean_credential_value(match.group("user"))
        pwd = _clean_credential_value(match.group("pwd"))
        if user and pwd:
            return user, pwd

    match = LABELED_PASSWORD_FIRST.search(normalized)
    if match:
        user = _clean_credential_value(match.group("user"))
        pwd = _clean_credential_value(match.group("pwd"))
        if user and pwd:
            return user, pwd

    account_match = LABELED_ACCOUNT_ONLY.search(normalized)
    password_match = LABELED_PASSWORD_ONLY.search(normalized)
    if account_match and password_match:
        user = _clean_credential_value(account_match.group("user"))
        pwd = _clean_credential_value(password_match.group("pwd"))
        if user and pwd:
            return user, pwd

    return None


def _username_score(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    if PHONE_PATTERN.fullmatch(text):
        return 100
    if ID_CARD_PATTERN.fullmatch(text):
        return 95
    if text.isdigit() and len(text) >= 11:
        return 80
    if "@" in text and "." in text:
        return 70
    if text.isdigit():
        return 50
    if any(ch.isalpha() for ch in text) and any(ch.isdigit() for ch in text):
        return 30
    if text.isalpha():
        return 20
    return 10


def _assign_username_password(first: str, second: str) -> tuple[str, str]:
    first = first.strip()
    second = second.strip()
    if not first and not second:
        return "", ""
    if not first:
        return second, ""
    if not second:
        return first, ""

    first_score = _username_score(first)
    second_score = _username_score(second)
    if second_score > first_score:
        return second, first
    return first, second


def _split_parts(text: str, pattern: re.Pattern[str] = SEPARATOR_PATTERN) -> list[str]:
    return [part.strip() for part in pattern.split(text.strip()) if part.strip()]


def _guess_from_parts(parts: list[str]) -> tuple[str, str]:
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""

    best_idx = 0
    best_score = _username_score(parts[0])
    for idx, part in enumerate(parts[1:], start=1):
        score = _username_score(part)
        if score > best_score:
            best_score = score
            best_idx = idx

    username = parts[best_idx]
    password_parts = [part for idx, part in enumerate(parts) if idx != best_idx]
    password = password_parts[0] if len(password_parts) == 1 else "".join(password_parts)
    return username, password


def split_credential_field(text: str) -> tuple[str, str]:
    """从合并字段中识别账号与密码。"""
    raw = "" if text is None else str(text).strip()
    if not raw:
        return "", ""

    labeled = _parse_labeled_credentials(raw)
    if labeled:
        return labeled

    normalized = normalize_symbols(raw)
    parts = _split_parts(normalized)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    if len(parts) == 2:
        return _assign_username_password(parts[0], parts[1])
    return _guess_from_parts(parts)


def _parse_with_pattern(raw: str, pattern: re.Pattern[str], label: str) -> Iterable[tuple[str, str, str]]:
    parts = _split_parts(normalize_symbols(raw), pattern)
    if len(parts) < 2:
        return
    if len(parts) == 2:
        user, pwd = _assign_username_password(parts[0], parts[1])
        yield user, pwd, label
        yield pwd, user, f"{label}-互换"
        return

    user, pwd = _guess_from_parts(parts)
    yield user, pwd, label
    if pwd:
        yield pwd, user, f"{label}-互换"


def parse_credential_alternatives(raw: str) -> list[tuple[str, str, str]]:
    """基于原始文本生成多种拆分候选。"""
    if not raw or not str(raw).strip():
        return []

    text = str(raw).strip()
    candidates: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(user: str, pwd: str, desc: str) -> None:
        u = user.strip()
        p = pwd.strip()
        if not u or not p:
            return
        key = (u, p)
        if key in seen:
            return
        seen.add(key)
        candidates.append((u, p, desc))

    labeled = _parse_labeled_credentials(text)
    if labeled:
        user, pwd = labeled
        add(user, pwd, "标签识别")
        add(pwd, user, "标签识别-互换")

    for user, pwd, desc in _parse_with_pattern(text, SEPARATOR_PATTERN, "标准分隔识别"):
        add(user, pwd, desc)
    for user, pwd, desc in _parse_with_pattern(text, re.compile(r"[\n\r]+"), "换行分隔识别"):
        add(user, pwd, desc)
    for user, pwd, desc in _parse_with_pattern(text, re.compile(r"[,，]+"), "逗号分隔识别"):
        add(user, pwd, desc)
    for user, pwd, desc in _parse_with_pattern(text, re.compile(r"[\s]+"), "空格分隔识别"):
        add(user, pwd, desc)

    return candidates


def generate_login_variants(
    username: str,
    password: str,
    *,
    raw: str = "",
) -> list[tuple[str, str, str]]:
    """生成待尝试的 (账号, 密码, 说明) 列表，按优先级排序。"""
    variants: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(user: str, pwd: str, desc: str) -> None:
        u = normalize_symbols(user)
        p = normalize_symbols(pwd)
        if not u or not p:
            return
        key = (u, p)
        if key in seen:
            return
        seen.add(key)
        variants.append((u, p, desc))

    add(username, password, "初始识别")
    add(password, username, "账号密码互换")

    norm_user = normalize_symbols(username)
    norm_pwd = normalize_symbols(password)
    if norm_user != username or norm_pwd != password:
        add(norm_user, norm_pwd, "符号归一化")
        add(norm_pwd, norm_user, "符号归一化+互换")

    if raw:
        for user, pwd, desc in parse_credential_alternatives(raw):
            add(user, pwd, desc)

    return variants
