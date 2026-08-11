"""Phục vụ dashboard và tự build lại từ data/logs.jsonl ở mỗi lần tải trang.

Dùng khi demo: bật incident, chạy load test, dashboard tự cập nhật mà không cần
chạy tay build_dashboard.py.

Chạy: python scripts/serve_dashboard.py --port 8090
"""
from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio  # noqa: E402
from scripts.build_dashboard import build  # noqa: E402

CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
LOGS_PATH = REPO_ROOT / "data" / "logs.jsonl"
OUTPUT_PATH = REPO_ROOT / "data" / "dashboard.html"


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - chữ ký do BaseHTTPRequestHandler quy định
        if self.path not in ("/", "/dashboard.html"):
            self.send_error(404, "Chi phuc vu / hoac /dashboard.html")
            return
        try:
            build(CONFIG_PATH, LOGS_PATH, OUTPUT_PATH)
            payload = OUTPUT_PATH.read_bytes()
        except FileNotFoundError:
            self.send_error(503, "Chua co data/logs.jsonl - hay chay load_test.py truoc")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[dashboard] {fmt % args}")


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Serve dashboard tu dong build lai")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), DashboardHandler)
    print(f"Dashboard live tai http://{args.host}:{args.port}/dashboard.html")
    print("Moi lan tai trang se build lai tu data/logs.jsonl. Ctrl+C de dung.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDa dung dashboard server.")


if __name__ == "__main__":
    main()
