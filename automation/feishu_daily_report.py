#!/usr/bin/env python3
"""Render category daily reports as JPG and deliver them through a Feishu bot."""

from __future__ import annotations

import argparse
import glob
import json
import mimetypes
import os
import threading
import time
import urllib.request
import uuid
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import PROJECT_DIR, SITE_DIR


CATEGORIES = ("手机", "DT", "显示器")
OUTPUT_DIR = PROJECT_DIR / "data" / "daily-reports"
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
IMAGE_URL = "https://open.feishu.cn/open-apis/im/v1/images"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def start_site_server() -> tuple[ThreadingHTTPServer, threading.Thread]:
    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(SITE_DIR), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def chromium_path() -> str | None:
    configured = os.environ.get("WORKBUDDY_REPORT_CHROMIUM")
    if configured:
        return configured
    pattern = str(Path.home() / "Library" / "Caches" / "ms-playwright" / "chromium-*" / "chrome-mac-arm64" / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing")
    candidates = sorted(glob.glob(pattern), reverse=True)
    return candidates[0] if candidates else None


def render_reports(report_date: str | None = None) -> list[Path]:
    password = os.environ.get("WORKBUDDY_CREATIVE_PASSWORD")
    if not password:
        raise RuntimeError("缺少 WORKBUDDY_CREATIVE_PASSWORD，无法解锁本地日报页面。")
    if not (SITE_DIR / "index.html").exists():
        raise RuntimeError("未找到 site/index.html，请先构建看板。")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server, _ = start_site_server()
    base_url = f"http://127.0.0.1:{server.server_port}/#/daily"
    generated: list[Path] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, executable_path=chromium_path())
            page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
            page.goto(base_url, wait_until="networkidle")
            page.locator("#dashboard-password").fill(password)
            page.get_by_role("button", name="进入看板").click()
            page.locator(".daily-report").wait_for(state="visible", timeout=30000)
            if report_date:
                page.locator(".daily-report-filters input[type=date]").fill(report_date)
            for category in CATEGORIES:
                selector = page.locator(".daily-report-filters select")
                selector.select_option(label=category)
                page.locator(".daily-report h2").wait_for(state="visible")
                output = OUTPUT_DIR / f"{category}品类投放日报_{report_date or datetime.now().strftime('%Y-%m-%d')}.jpg"
                page.locator(".daily-report").screenshot(path=str(output), type="jpeg", quality=88)
                generated.append(output)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    return generated


def request_json(url: str, data: bytes, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("code") not in (None, 0):
        raise RuntimeError(f"飞书接口失败: {payload.get('msg', payload)}")
    return payload


def tenant_token() -> str:
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise RuntimeError("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET。")
    result = request_json(TOKEN_URL, json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(), {"Content-Type": "application/json"})
    return result["tenant_access_token"]


def upload_image(path: Path, token: str) -> str:
    boundary = f"----Workbuddy{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image_type\"\r\n\r\nmessage\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\nContent-Type: {content_type}\r\n\r\n".encode(),
        path.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode(),
    ])
    result = request_json(IMAGE_URL, body, {"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    return result["data"]["image_key"]


def send_image(image_key: str, token: str, chat_id: str) -> None:
    payload = {"receive_id": chat_id, "msg_type": "image", "content": json.dumps({"image_key": image_key})}
    request_json(MESSAGE_URL, json.dumps(payload).encode(), {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})


def send_reports(paths: list[Path]) -> None:
    chat_id = os.environ.get("FEISHU_CHAT_ID")
    if not chat_id:
        raise RuntimeError("缺少 FEISHU_CHAT_ID。")
    token = tenant_token()
    for path in paths:
        send_image(upload_image(path, token), token, chat_id)
        print(f"已发送: {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("render", "send", "all"))
    parser.add_argument("--date", dest="report_date")
    args = parser.parse_args()
    paths = render_reports(args.report_date)
    for path in paths:
        print(f"已生成: {path}")
    if args.mode in ("send", "all"):
        send_reports(paths)


if __name__ == "__main__":
    main()
