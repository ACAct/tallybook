"""仅供本机使用的 HTTP 适配层。"""
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .schema import CATEGORIES
from .service import Ledger
from .storage import StorageError

STATIC = Path(__file__).resolve().parent.parent / "static"
ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/styles.css": ("styles.css", "text/css; charset=utf-8"),
          "/favicon.svg": ("favicon.svg", "image/svg+xml")}
MAX_BODY = 64 * 1024 * 1024


def create_server(data_path, port=8765):
    ledger = Ledger(data_path)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # 不把个人账目和筛选词写入访问日志。

        def send(self, status, body, content_type="application/json; charset=utf-8", filename=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:
                self.send_header("Content-Disposition", 'attachment; filename="' + filename + '"')
            self.end_headers()
            self.wfile.write(body)

        def body(self):
            if self.headers.get_content_type() != "application/json":
                raise ValueError("请求须为 JSON 格式")
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ValueError("请求长度无效") from None
            if not 0 < size <= MAX_BODY:
                raise ValueError("文件为空或超过 64 MB")
            try:
                return json.loads(self.rfile.read(size).decode("utf-8-sig"))
            except (ValueError, UnicodeError):
                raise ValueError("JSON 文件无法解析，请检查文件格式") from None

        def dispatch(self):
            self.connection.settimeout(15)
            port = self.server.server_port
            allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
            origin = self.headers.get("Origin")
            if self.headers.get("Host") not in allowed or (origin and origin not in {"http://" + host for host in allowed}):
                return self.send(403, {"error": "只允许从本机记账页面访问"})
            parts = urlsplit(self.path)
            path = parts.path
            filters = {key: values[-1] for key, values in parse_qs(parts.query).items()}
            try:
                if self.command == "GET" and path in ASSETS:
                    name, mime = ASSETS[path]
                    return self.send(200, (STATIC / name).read_bytes(), mime)
                if self.command == "GET" and path == "/api/dashboard":
                    with ledger.store.transaction():
                        rows = ledger.query(filters)
                        all_rows = ledger.store.read()
                    categories = sorted(set(sum(CATEGORIES.values(), []) + [r["category"] for r in all_rows]))
                    return self.send(200, {"records": rows, "summary": ledger.summarize(rows),
                                           "categories": categories, "defaults": CATEGORIES, "total_count": len(all_rows)})
                if self.command == "POST" and path == "/api/records":
                    return self.send(201, ledger.add(self.body()))
                if path.startswith("/api/records/") and self.command in ("PUT", "DELETE"):
                    rid = path.rsplit("/", 1)[-1]
                    if self.command == "PUT":
                        return self.send(200, ledger.update(rid, self.body()))
                    ledger.delete(rid)
                    return self.send(200, {"ok": True})
                if self.command == "POST" and path == "/api/import":
                    return self.send(200, ledger.import_json(self.body()))
                if self.command == "GET" and path == "/api/export":
                    if filters.get("format", "json") == "json":
                        return self.send(200, ledger.export_json(), filename="qingji-backup.json")
                    if filters["format"] == "csv":
                        return self.send(200, ledger.export_csv(filters), "text/csv; charset=utf-8", "qingji-records.csv")
                    raise ValueError("导出格式须为 JSON 或 CSV")
                return self.send(404, {"error": "页面或接口不存在"})
            except ValueError as exc:
                self.send(400, {"error": str(exc)})
            except KeyError as exc:
                self.send(404, {"error": str(exc.args[0])})
            except StorageError as exc:
                self.send(500, {"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                logging.exception("请求处理失败")
                self.send(500, {"error": "服务暂时无法完成操作，请查看运行窗口并重试"})

        do_GET = dispatch
        do_POST = dispatch
        do_PUT = dispatch
        do_DELETE = dispatch

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
