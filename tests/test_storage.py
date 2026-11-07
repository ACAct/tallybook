"""A3 自己的测试：只验证存储层，不依赖业务模块和前端。

运行：python -m unittest tests.test_storage -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger.storage import StorageError, JsonStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def record(rid, amount_cents=1230):
    """构造一条符合《接口契约》的合法记录。"""
    return {
        "id": rid,
        "date": "2026-11-07",
        "type": "expense",
        "amount_cents": amount_cents,
        "category": "餐饮",
        "note": "午餐",
        "created_at": "2026-11-07T12:00:00+00:00",
        "updated_at": "2026-11-07T12:00:00+00:00",
    }


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "ledger.json"
        self.store = JsonStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_file_reads_as_empty(self):
        self.assertFalse(self.path.exists())
        self.assertEqual(self.store.read(), [])
        # 只读不写：读一个不存在的账本不应该顺手创建文件。
        self.assertFalse(self.path.exists())

    def test_write_then_read_keeps_integer_cents(self):
        self.store.write([record("r1", 10), record("r2", 20)])
        rows = JsonStore(self.path).read()
        self.assertEqual([row["amount_cents"] for row in rows], [10, 20])
        self.assertTrue(all(type(row["amount_cents"]) is int for row in rows))
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["version"], 1)

    def test_corrupt_file_is_never_overwritten(self):
        self.path.write_text("broken json", encoding="utf-8")
        with self.assertRaises(StorageError):
            self.store.read()
        with self.assertRaises(StorageError):
            with self.store.transaction():
                self.store.read()
        self.assertEqual(self.path.read_text(encoding="utf-8"), "broken json")

    def test_failed_write_keeps_original_and_leaves_no_temp(self):
        self.store.write([record("r1")])
        before = self.path.read_text(encoding="utf-8")
        with mock.patch("ledger.storage.json.dump", side_effect=OSError("磁盘已满")):
            with self.assertRaises(StorageError):
                self.store.write([record("r1"), record("r2", 999)])
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)
        self.assertEqual(sorted(p.name for p in Path(self.temp.name).iterdir()), ["ledger.json"])

    def test_transaction_holds_lock_for_whole_read_modify_write(self):
        self.store.write([record("r0")])
        with self.store.transaction():
            rows = self.store.read()
            rows.append(record("r1"))
            self.store.write(rows)
        self.assertEqual(len(self.store.read()), 2)
        # 事务结束必须解锁，否则第二次事务会一直等到超时。
        with self.store.transaction():
            pass

    def test_separate_processes_never_lose_successful_writes(self):
        program = (
            "import sys\n"
            "from ledger.storage import JsonStore\n"
            "store = JsonStore(sys.argv[1])\n"
            "for i in range(8):\n"
            "    with store.transaction():\n"
            "        rows = store.read()\n"
            "        rows.append({'id': 'p%s-%s' % (sys.argv[2], i), 'date': '2026-11-07',"
            " 'type': 'expense', 'amount_cents': 123, 'category': '测试', 'note': '',"
            " 'created_at': '2026-11-07T12:00:00+00:00', 'updated_at': '2026-11-07T12:00:00+00:00'})\n"
            "        store.write(rows)\n"
        )
        jobs = [
            subprocess.Popen([sys.executable, "-c", program, str(self.path), str(n)], cwd=str(PROJECT_ROOT))
            for n in range(3)
        ]
        for job in jobs:
            self.assertEqual(job.wait(timeout=60), 0)
        rows = self.store.read()
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({row["id"] for row in rows}), 24)

    def test_lock_file_sits_next_to_data(self):
        with self.store.transaction():
            self.assertTrue(Path(str(self.path) + ".lock").exists())


if __name__ == "__main__":
    unittest.main()
