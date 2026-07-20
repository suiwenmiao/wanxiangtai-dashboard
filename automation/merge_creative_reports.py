#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge locally downloaded creative reports into one exact date range."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import REPORT_DIR
from generate_creative_data import read_csv


def report_range() -> tuple[str, str]:
    start = os.environ.get("WORKBUDDY_REPORT_START", "").strip()
    end = os.environ.get("WORKBUDDY_REPORT_END", "").strip()
    if not start or not end:
        raise SystemExit("[ERROR] 请同时设置 WORKBUDDY_REPORT_START 和 WORKBUDDY_REPORT_END")
    start = datetime.strptime(start, "%Y-%m-%d").strftime("%Y-%m-%d")
    end = datetime.strptime(end, "%Y-%m-%d").strftime("%Y-%m-%d")
    if start > end:
        raise SystemExit("[ERROR] 开始日期不能晚于结束日期")
    return start, end


def main() -> None:
    start, end = report_range()
    output = REPORT_DIR / f"万相台创意报表_{start}_{end}.csv"
    inputs = [path for path in sorted(REPORT_DIR.glob("万相台创意报表_*.csv")) if path != output]
    frames: list[pd.DataFrame] = []
    for path in inputs:
        frame = read_csv(path)
        if "日期" not in frame.columns:
            continue
        dates = pd.to_datetime(frame["日期"], errors="coerce").dt.strftime("%Y-%m-%d")
        frame = frame.loc[(dates >= start) & (dates <= end)].copy()
        if not frame.empty:
            frame["日期"] = dates.loc[frame.index]
            frames.append(frame)
            print(f"纳入: {path.name} · {len(frame)} 行")
    if not frames:
        raise SystemExit(f"[ERROR] 本地没有覆盖 {start} 至 {end} 的创意报表")

    merged = pd.concat(frames, ignore_index=True).drop_duplicates().reset_index(drop=True)
    dates = sorted(merged["日期"].dropna().unique())
    expected = pd.date_range(start, end, freq="D").strftime("%Y-%m-%d").tolist()
    missing = sorted(set(expected) - set(dates))
    if missing:
        raise SystemExit(f"[ERROR] 缺少日期: {', '.join(missing)}")
    merged.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"已合并: {output} · {len(merged)} 行 · {dates[0]} 至 {dates[-1]}")


if __name__ == "__main__":
    main()
