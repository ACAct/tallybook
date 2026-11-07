"""C1 自己的测试：只验证收支汇总，不依赖业务模块和前端。

运行：python -m unittest tests.test_summary -v
"""
import unittest

from ledger.summary import LedgerSummary


def record(date, kind, amount_cents, category):
    return {"date": date, "type": kind, "amount_cents": amount_cents, "category": category}


class SummaryTests(unittest.TestCase):
    def test_totals_and_balance(self):
        rows = [
            record("2026-11-01", "income", 1000, "工资"),
            record("2026-11-02", "expense", 30, "餐饮"),
            record("2026-11-03", "expense", 70, "餐饮"),
        ]
        result = LedgerSummary.summarize(rows)
        self.assertEqual(result["income_cents"], 1000)
        self.assertEqual(result["expense_cents"], 100)
        self.assertEqual(result["balance_cents"], 900)
        self.assertEqual(result["count"], 3)

    def test_categories_aggregate_and_sort(self):
        rows = [
            record("2026-11-01", "expense", 30, "餐饮"),
            record("2026-11-02", "expense", 100, "交通"),
            record("2026-11-03", "income", 500, "工资"),
        ]
        categories = LedgerSummary.summarize(rows)["categories"]
        self.assertEqual([row["category"] for row in categories], ["工资", "交通", "餐饮"])
        dining = next(row for row in categories if row["category"] == "餐饮")
        self.assertEqual((dining["expense_cents"], dining["income_cents"], dining["count"]), (30, 0, 1))

    def test_months_ascending(self):
        rows = [
            record("2026-11-07", "expense", 30, "餐饮"),
            record("2026-10-01", "income", 1000, "工资"),
        ]
        months = LedgerSummary.summarize(rows)["months"]
        self.assertEqual([row["month"] for row in months], ["2026-10", "2026-11"])
        self.assertEqual(months[0]["income_cents"], 1000)
        self.assertEqual(months[1]["expense_cents"], 30)

    def test_empty_ledger(self):
        result = LedgerSummary.summarize([])
        self.assertEqual((result["income_cents"], result["expense_cents"],
                          result["balance_cents"], result["count"]), (0, 0, 0, 0))
        self.assertEqual(result["categories"], [])
        self.assertEqual(result["months"], [])


if __name__ == "__main__":
    unittest.main()
