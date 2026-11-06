#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge locally downloaded creative reports into one exact date range."""

from __future__ import annotations

import os
import re
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
    reports = [path for path in sorted(REPORT_DIR.glob("万相台创意报表_*.csv")) if path != output]
    cumulative = []
    daily = []
    for path in reports:
        range_match = re.fullmatch(r"万相台创意报表_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv", path.name)
        day_match = re.fullmatch(r"万相台创意报表_(\d{4}-\d{2}-\d{2})\.csv", path.name)
        if range_match and range_match.group(1) == start and range_match.group(2) < end:
            cumulative.append((range_match.group(2), path))
        elif day_match and start <= day_match.group(1) <= end:
            daily.append((day_match.group(1), path))

    if cumulative:
        latest_end, latest_report = max(cumulative, key=lambda item: item[0])
        inputs = [latest_report] + [path for day, path in daily if day > latest_end]
        print(f"增量续接累计报表: {latest_report.name}，仅追加 {len(inputs) - 1} 份后续日报")
    else:
        inputs = [path for path in reports if re.fullmatch(r"万相台创意报表_\d{4}-\d{2}-\d{2}\.csv", path.name)]

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
