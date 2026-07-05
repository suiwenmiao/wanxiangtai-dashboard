#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project-wide configuration.

Values can be overridden with environment variables or a local `.env` file.
Keep `.env` private and commit only `.env.example`.
"""

from __future__ import annotations

import os
from pathlib import Path


AUTOMATION_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AUTOMATION_DIR.parent
PROJECT_PARENT = PROJECT_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
SITE_DIR = PROJECT_DIR / "site"
FRONTEND_DATA_FILE = FRONTEND_DIR / "src" / "data" / "dashboard-data.json"
HOME = Path.home()


def _load_dotenv() -> None:
    env_file = PROJECT_DIR / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _path_from_env(name: str, default: Path | str) -> Path:
    value = os.environ.get(name)
    if value:
        return Path(value).expanduser()
    return Path(default).expanduser()


def _default_big_table_path() -> Path:
    parent_file = PROJECT_PARENT / "万相台数据表.xlsx"
    if parent_file.exists():
        return parent_file
    return PROJECT_DIR / "data" / "万相台数据表.xlsx"


_load_dotenv()

SHEET_NAME = os.environ.get("WORKBUDDY_SHEET_NAME", "3月")

BIG_TABLE_PATH = _path_from_env("WORKBUDDY_DATA_FILE", _default_big_table_path())
BASE_TABLE_PATH = _path_from_env(
    "WORKBUDDY_BASE_TABLE",
    HOME / "Desktop" / "商品ID基础表最新6.23.xlsx",
)

REPORT_DIR = _path_from_env("WORKBUDDY_REPORT_DIR", PROJECT_DIR / "data" / "reports")

STATE_FILE = _path_from_env("WORKBUDDY_ALIMAMA_STATE", HOME / ".workbuddy" / "alimama_state.json")

DOWNLOAD_DIR = _path_from_env("WORKBUDDY_DOWNLOAD_DIR", "/tmp/alimama_downloads")
SCREENSHOT_DIR = _path_from_env("WORKBUDDY_SCREENSHOT_DIR", "/tmp/alimama_screenshots")
DOWNLOAD_LOG_FILE = _path_from_env("WORKBUDDY_DOWNLOAD_LOG", "/tmp/alimama_download.log")
DAILY_LOG_FILE = _path_from_env("WORKBUDDY_DAILY_LOG", "/tmp/alimama_cron.log")

AUTO_DEPLOY = os.environ.get("AUTO_DEPLOY", "0") == "1"
