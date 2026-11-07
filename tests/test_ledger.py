import json
import tempfile
import unittest
from pathlib import Path

from ledger.service import Ledger
from ledger.storage import StorageError


def entry(**changes):
    data = dict(date="2026-11-07", type="expense", amount="12.30", category="餐饮", note="午餐")
    data.update(changes)
    return data


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "ledger.json"
        self.book = Ledger(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_persistence_and_integer_cents(self):
        record = self.book.add(entry(amount="0.10"))
        self.assertEqual(record["amount_cents"], 10)
        self.assertEqual(Ledger(self.path).query({})[0]["id"], record["id"])
        self.assertEqual(json.loads(self.path.read_text())["records"][0]["amount_cents"], 10)

    def test_rejects_bad_inputs_without_writing(self):
        for patch in [dict(amount="0"), dict(amount="-1"), dict(amount="NaN"),
                      dict(amount="1.001"), dict(amount=True), dict(amount="1e3"),
                      dict(date="2026-02-30"), dict(date="2026-2-1"), dict(type="other"),
                      dict(category=" "), dict(note="x" * 501)]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.book.add(entry(**patch))
        self.assertEqual(self.book.query({}), [])

    def test_edit_delete_and_missing(self):
        record = self.book.add(entry())
        updated = self.book.update(record["id"], entry(amount="20", note="晚餐"))
        self.assertEqual(updated["id"], record["id"])
        self.assertEqual(updated["amount_cents"], 2000)
        self.book.delete(record["id"])
        self.assertEqual(Ledger(self.path).query({}), [])
        with self.assertRaises(KeyError):
            self.book.delete(record["id"])

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

    def test_exact_summary_and_filtered_charts(self):
        self.book.add(entry(amount="0.10"))
        self.book.add(entry(amount="0.20"))
        self.book.add(entry(type="income", amount="1", category="工资"))
        result = self.book.summary({})
        self.assertEqual((result["income_cents"], result["expense_cents"], result["balance_cents"]), (100, 30, 70))
        dining = next(row for row in result["categories"] if row["category"] == "餐饮")
        self.assertEqual(dining["expense_cents"], 30)
        self.assertEqual(result["months"][0]["expense_cents"], 30)
        self.assertEqual(self.book.summary({"type": "income"})["expense_cents"], 0)

    def test_import_is_atomic_and_duplicate_safe(self):
        self.book.add(entry())
        backup = self.book.export_json()
        self.assertEqual(self.book.import_json(backup), {"added": 0, "skipped": 1})
        other = Ledger(Path(self.temp.name) / "other.json")
        self.assertEqual(other.import_json(backup)["added"], 1)
        damaged = json.loads(json.dumps(backup))
        damaged["records"].append(dict(backup["records"][0], id="new", amount_cents=-1))
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.book.import_json(damaged)
        self.assertEqual(self.path.read_bytes(), before)
        conflict = json.loads(json.dumps(backup))
        conflict["records"][0]["note"] = "不同版本"
        with self.assertRaises(ValueError):
            self.book.import_json(conflict)

    def test_corrupt_file_is_never_overwritten(self):
        self.path.write_text("broken json", encoding="utf-8")
        with self.assertRaises(StorageError):
            self.book.add(entry())
        self.assertEqual(self.path.read_text(), "broken json")

    def test_csv_quotes_and_formula_protection(self):
        self.book.add(entry(note='=SUM(1,2)'))
        self.book.add(entry(note='他说 "你好",午餐'))
        csv = self.book.export_csv({})
        self.assertIn("'", csv)
        self.assertIn('"他说 ""你好"",午餐"', csv)
        self.assertIn("12.30", csv)


if __name__ == "__main__":
    unittest.main()
