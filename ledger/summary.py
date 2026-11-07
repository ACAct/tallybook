"""C1 · 收支汇总。

本文件只由 C1 成员维护：收入/支出/结余/笔数、按月与按类别聚合。
"""
from collections import defaultdict


class LedgerSummary:
    def summary(self, filters):
        return self.summarize(self.query(filters))

    @staticmethod
    def summarize(records):
        income = expense = 0
        categories = defaultdict(lambda: {"income_cents": 0, "expense_cents": 0, "count": 0})
        months = defaultdict(lambda: {"income_cents": 0, "expense_cents": 0})
        for row in records:
            key = row["type"] + "_cents"
            if row["type"] == "income":
                income += row["amount_cents"]
            else:
                expense += row["amount_cents"]
            categories[row["category"]][key] += row["amount_cents"]
            categories[row["category"]]["count"] += 1
            months[row["date"][:7]][key] += row["amount_cents"]
        return {"income_cents": income, "expense_cents": expense, "balance_cents": income - expense,
                "count": len(records),
                "categories": sorted([dict(value, category=key) for key, value in categories.items()],
                                     key=lambda r: r["income_cents"] + r["expense_cents"], reverse=True),
                "months": [dict(month=key, **months[key]) for key in sorted(months)]}
