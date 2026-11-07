#!/usr/bin/env python3
"""运行：python3 app.py；所有路径均相对于项目而非终端当前目录。"""
import argparse
import sys
import threading
import webbrowser
from pathlib import Path

from ledger.server import create_server
from ledger.service import Ledger
from ledger.storage import StorageError


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="轻记 · 本地个人记账本")
    parser.add_argument("--port", type=int, default=8765, help="本机端口，默认 8765")
    parser.add_argument("--data", type=Path, default=root / "data" / "ledger.json", help="JSON 数据文件路径")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口须在 1 至 65535 之间")
    try:
        Ledger(args.data).query({})
        server = create_server(args.data, args.port)
    except (OSError, StorageError) as exc:
        print("启动失败：" + str(exc), file=sys.stderr)
        print("若端口被占用，可使用 --port 8766；若账本损坏，请先保留原文件再恢复备份。", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{args.port}"
    print(f"轻记已启动：{url}\n数据文件：{args.data.resolve()}\n按 Ctrl+C 停止服务。", flush=True)
    if not args.no_browser:
        timer = threading.Timer(0.5, lambda: webbrowser.open(url))
        timer.daemon = True
        timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n轻记已停止，已保存的记录仍保留在本地。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
