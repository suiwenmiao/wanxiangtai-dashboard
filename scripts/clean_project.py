#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove local cache files that should not be part of the project."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ".check-dist",
    "__pycache__",
    "automation/__pycache__",
    "scripts/__pycache__",
    ".DS_Store",
    "frontend/.DS_Store",
    "automation/.DS_Store",
    "docs/.DS_Store",
]


def main() -> None:
    for target in TARGETS:
        path = ROOT / target
        if path.is_dir():
            shutil.rmtree(path)
            print(f"removed {path.relative_to(ROOT)}")
        elif path.exists():
            path.unlink()
            print(f"removed {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
