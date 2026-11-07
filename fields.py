"""A1 · 基础字段校验：金额统一转换为整数分，禁止悄悄舍入。

本文件只由 A1 成员维护；A2 的结构校验（schema.py）和业务层都从这里导入。
"""
import re
from datetime import date
from decimal import Decimal

MAX_CENTS = 9_999_999_999


def valid_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("日期须为 YYYY-MM-DD 格式")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("请输入有效的日期") from None
    return value


def cents(value, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("金额须为数字")
    value = str(value).strip()
    if not re.fullmatch(r"\d{1,8}(?:\.\d{1,2})?", value):
        raise ValueError("金额最多 8 位整数、2 位小数")
    result = int(Decimal(value) * 100)
    if result < (0 if allow_zero else 1) or result > MAX_CENTS:
        raise ValueError("金额须大于 0，且不超过 99,999,999.99 元")
    return result


def text_field(value, name, maximum, required=False):
    if not isinstance(value, str):
        raise ValueError(name + "须为文字")
    value = value.strip()
    if (required and not value) or len(value) > maximum or any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
        raise ValueError(name + "不能为空或超出长度限制" if required else name + "过长或含无效字符")
    return value
