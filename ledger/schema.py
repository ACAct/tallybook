"""A2 · 记录结构、分类与备份文档校验。

本文件只由 A2 成员维护；基础字段校验在 fields.py（A1）。
"""
import re
from datetime import datetime, timezone
from uuid import uuid4

from .fields import MAX_CENTS, cents, text_field, valid_date

MAX_RECORDS = 20_000
CATEGORIES = {
    "expense": ["餐饮", "交通", "购物", "居住", "娱乐", "医疗", "学习", "其他支出"],
    "income": ["工资", "奖金", "兼职", "理财", "礼金", "其他收入"],
}


def validate_entry(data, existing=None):
    if not isinstance(data, dict):
        raise ValueError("记录格式无效")
    kind = data.get("type")
    if kind not in ("income", "expense"):
        raise ValueError("请选择收入或支出")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": existing["id"] if existing else uuid4().hex,
        "date": valid_date(data.get("date")),
        "type": kind,
        "amount_cents": cents(data.get("amount")),
        "category": text_field(data.get("category"), "类别", 30, True),
        "note": text_field(data.get("note", ""), "备注", 500),
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }


def validate_document(document):
    if not isinstance(document, dict) or type(document.get("version")) is not int or document["version"] != 1:
        raise ValueError("不支持的账本格式，请选择轻记导出的 JSON 文件")
    records = document.get("records")
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError("记录列表无效或超过 20,000 笔上限")
    clean, seen = [], set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("记录格式无效")
        rid, amount = row.get("id"), row.get("amount_cents")
        if not isinstance(rid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", rid) or rid in seen:
            raise ValueError("记录编号无效或重复")
        if type(amount) is not int or not 1 <= amount <= MAX_CENTS:
            raise ValueError("备份中的金额须为有效的整数分")
        for field in ("created_at", "updated_at"):
            if not isinstance(row.get(field), str) or len(row[field]) > 64:
                raise ValueError("备份缺少时间信息")
            try:
                stamp = datetime.fromisoformat(row[field].replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    raise ValueError()
            except ValueError:
                raise ValueError("备份中的时间信息无效") from None
        result = validate_entry(dict(row, amount=f"{amount // 100}.{amount % 100:02d}"), row)
        result["updated_at"] = row["updated_at"]
        clean.append(result)
        seen.add(rid)
    return clean
