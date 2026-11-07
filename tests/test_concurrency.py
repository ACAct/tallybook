import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ConcurrentWritesTests(unittest.TestCase):
    def test_separate_processes_never_lose_successful_writes(self):
        # 每个进程故意延迟读取后的返回，扩大丢失更新窗口。
        program = '''
import sys, time
from ledger.service import Ledger
book = Ledger(sys.argv[1])
original = book.store.read
def slow_read():
    result = original()
    time.sleep(0.015)
    return result
book.store.read = slow_read
for i in range(8):
    book.add(dict(date="2026-11-07", type="expense", amount="1.23", category="测试", note="并发验证"))
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "book.json"
            jobs = [subprocess.Popen([sys.executable, "-c", program, str(path)], cwd=Path(__file__).resolve().parent.parent) for _ in range(3)]
            for job in jobs:
                self.assertEqual(job.wait(timeout=20), 0)
            document = json.loads(path.read_text())
            self.assertEqual(len(document["records"]), 24)


if __name__ == "__main__":
    unittest.main()
