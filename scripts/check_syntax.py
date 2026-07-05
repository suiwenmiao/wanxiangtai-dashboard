#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Syntax-check Python files without importing them or writing bytecode."""

from __future__ import annotations

import sys
from pathlib import Path


DEFAULT_FILES = [
    "automation/config.py",
    "automation/generate_dashboard_data.py",
    "automation/wanxiangtai_download.py",
    "automation/match_category.py",
    "automation/run_daily.py",
    "automation/deploy_static.py",
    "scripts/check_syntax.py",
    "scripts/clean_project.py",
]


def main() -> int:
    files = sys.argv[1:] or DEFAULT_FILES
    failed = False

    for file_name in files:
        path = Path(file_name)
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
        except Exception as exc:
            failed = True
            print(f"[FAIL] {path}: {exc}", file=sys.stderr)
        else:
            print(f"[OK] {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
