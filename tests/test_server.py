import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ledger.server import MAX_BODY, create_server
from ledger.schema import MAX_RECORDS


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = create_server(Path(self.temp.name) / "book.json", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def call(self, path, data=None, method="GET", headers=None):
        body = json.dumps(data).encode() if data is not None else None
        req = Request(self.base + path, data=body, method=method,
                      headers=headers or {"Content-Type": "application/json"})
        try:
            response = urlopen(req, timeout=3)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, response.headers, response.read()

    def test_full_api_flow_and_filters(self):
        status, _, content = self.call("/api/records", dict(date="2026-11-07", type="expense", amount="5.20", category="交通", note="地铁"), "POST")
        self.assertEqual(status, 201)
        record = json.loads(content)
        status, _, content = self.call("/api/dashboard?min=5.20&max=5.20")
        self.assertEqual(json.loads(content)["summary"]["expense_cents"], 520)
        status, _, content = self.call("/api/export?format=json")
        backup = json.loads(content)
        self.assertEqual(backup["records"][0]["id"], record["id"])
        status, _, content = self.call("/api/import", backup, "POST")
        self.assertEqual(json.loads(content)["skipped"], 1)
        status, _, _ = self.call("/api/records/" + record["id"], method="DELETE")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(self.call("/api/dashboard")[2])["summary"]["count"], 0)

    def test_bad_input_and_cross_origin_blocked(self):
        self.assertEqual(self.call("/api/records", {}, "POST")[0], 400)
        self.assertEqual(self.call("/api/dashboard?min=20&max=1")[0], 400)
        self.assertEqual(self.call("/api/records", {}, "POST", {"Origin": "https://evil.example", "Content-Type": "application/json"})[0], 403)
        self.assertEqual(self.call("/api/dashboard", headers={"Host": "evil.example"})[0], 403)

    def test_private_files_are_not_served(self):
        for path in ["/data/ledger.json", "/../app.py", "/%2e%2e/app.py", "/ledger/service.py"]:
            self.assertEqual(self.call(path)[0], 404)

    def test_largest_valid_backup_fits_import_limit(self):
        row = dict(id="x" * 64, date="2026-11-07", type="expense", amount_cents=9999999999,
                   category="😀" * 30, note="😀" * 500,
                   created_at="2026-11-07T12:34:56.123456+00:00", updated_at="2026-11-07T12:34:56.123456+00:00")
        payload = json.dumps({"version": 1, "records": [row] * MAX_RECORDS}, ensure_ascii=False, indent=2).encode("utf-8")
        self.assertLess(len(payload), MAX_BODY)


if __name__ == "__main__":
    unittest.main()
