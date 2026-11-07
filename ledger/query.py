"""B3 · 组合筛选。

本文件只由 B3 成员维护：日期/类型/类别/金额区间/关键词 AND 组合筛选。
"""
from .fields import cents, valid_date


class LedgerQuery:
    def query(self, filters):
        start = valid_date(filters["start"]) if filters.get("start") else None
        end = valid_date(filters["end"]) if filters.get("end") else None
        lower = cents(filters["min"], True) if filters.get("min") not in (None, "") else None
        upper = cents(filters["max"], True) if filters.get("max") not in (None, "") else None
        kind = filters.get("type") or None
        category = filters.get("category") or None
        needle = (filters.get("q") or "").strip().casefold()
        if start and end and start > end:
            raise ValueError("开始日期不能晚于结束日期")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("最低金额不能大于最高金额")
        if kind not in (None, "income", "expense"):
            raise ValueError("收支类型无效")
        records = [r for r in self.store.read()
                   if (not start or r["date"] >= start)
                   and (not end or r["date"] <= end)
                   and (lower is None or r["amount_cents"] >= lower)
                   and (upper is None or r["amount_cents"] <= upper)
                   and (not kind or r["type"] == kind)
                   and (not category or r["category"] == category)
                   and (not needle or needle in r["note"].casefold())]
        return sorted(records, key=lambda r: (r["date"], r["created_at"], r["id"]), reverse=True)
