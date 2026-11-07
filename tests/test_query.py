"""B3 自己的测试：只验证组合筛选，不依赖业务模块和前端。

运行：python -m unittest tests.test_query -v
"""
import tempfile
import unittest
from pathlib import Path

from ledger.query import LedgerQuery
from ledger.schema import validate_entry
from ledger.storage import JsonStore


class Book(LedgerQuery):
    """最小测试替身：只注入 query 需要的 store。"""

    def __init__(self, path):
        self.store = JsonStore(path)

    def add(self, data):
        record = validate_entry(data)
        with self.store.transaction():
            records = self.store.read()
            records.append(record)
            self.store.write(records)
        return record

    def save(self, rows):
        self.store.write(rows)


def entry(**changes):
    data = dict(date="2026-11-07", type="expense", amount="12.30", category="餐饮", note="午餐")
    data.update(changes)
    return data


def row(rid, created_at, date="2026-11-07", note=""):
    return {"id": rid, "date": date, "type": "expense", "amount_cents": 1230,
            "category": "餐饮", "note": note, "created_at": created_at, "updated_at": created_at}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "ledger.json"
        self.book = Book(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_combined_filters_and_latest_order(self):
        self.book.add(entry(date="2026-10-31", amount="20"))
        target = self.book.add(entry(date="2026-11-01", amount="20"))
        self.book.add(entry(date="2026-11-07", amount="30", category="交通"))
        self.book.add(entry(date="2026-11-06", amount="100", type="income", category="工资"))
        filters = dict(start="2026-11-01", end="2026-11-07", category="餐饮", min="20", max="20", type="expense", q="午餐")
        self.assertEqual([r["id"] for r in self.book.query(filters)], [target["id"]])
        self.assertEqual(self.book.query({})[0]["date"], "2026-11-07")
        for filters in [dict(start="2026-11-08", end="2026-11-01"), dict(min="20", max="10"), dict(start="bad"), dict(type="bad")]:
            with self.assertRaises(ValueError):
                self.book.query(filters)

    def test_empty_filters_do_not_limit(self):
        self.book.add(entry(date="2026-11-01", amount="1"))
        self.book.add(entry(date="2026-11-07", amount="2", type="income", category="工资", note=""))
        filters = dict(start=None, end="", type=None, category="", min=None, max="", q=None)
        self.assertEqual(len(self.book.query(filters)), 2)

    def test_keyword_matches_note_only(self):
        self.book.add(entry(category="交通", note="地铁"))
        self.book.add(entry(category="餐饮", note="快餐"))
        self.book.add(entry(category="餐饮", note="Metro"))
        self.assertEqual([r["note"] for r in self.book.query({"q": "交通"})], [])
        self.assertEqual([r["note"] for r in self.book.query({"q": "地铁"})], ["地铁"])
        self.assertEqual([r["note"] for r in self.book.query({"q": "  metro "})], ["Metro"])

    def test_amount_bounds_are_inclusive(self):
        self.book.add(entry(amount="5.20"))
        self.assertEqual(len(self.book.query({"min": "5.20", "max": "5.20"})), 1)
        self.assertEqual(self.book.query({"min": "5.21"}), [])
        with self.assertRaises(ValueError):
            self.book.query({"min": "abc"})

    def test_same_date_sorted_by_created_at_then_id(self):
        self.book.save([
            row("a", "2026-11-07T10:00:00+00:00"),
            row("c", "2026-11-07T12:00:00+00:00"),
            row("b", "2026-11-07T11:00:00+00:00"),
            row("d", "2026-11-07T12:00:00+00:00"),
        ])
        self.assertEqual([r["id"] for r in self.book.query({})], ["d", "c", "b", "a"])


if __name__ == "__main__":
    unittest.main()
