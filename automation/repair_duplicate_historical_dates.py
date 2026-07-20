#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replace duplicated July 2-5 rows with their verified historical source rows."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import BASE_TABLE_PATH, BIG_TABLE_PATH, PROJECT_DIR, SHEET_NAME


TARGET_DATES = ["2026-07-02", "2026-07-03", "2026-07-04", "2026-07-05"]
HISTORY_FILE = PROJECT_DIR / "data" / "reports" / "1月-7.5数据.xlsx"
BACKUP_DIR = PROJECT_DIR / "data" / "backups"


def normalize_dates(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["日期"] = pd.to_datetime(result["日期"], errors="coerce").dt.strftime("%Y-%m-%d")
    return result


def cost_by_date(frame: pd.DataFrame) -> pd.Series:
    values = pd.to_numeric(frame["花费"], errors="coerce").fillna(0)
    return values.groupby(frame["日期"]).sum()


def apply_category_mapping(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.drop(columns=[name for name in ["品类", "细类"] if name in frame.columns]).copy()
    if not BASE_TABLE_PATH.exists():
        result["品类"] = "其他"
        result["细类"] = "其他"
        return result
    mapping = pd.read_excel(BASE_TABLE_PATH, usecols=["主体ID", "品类", "细类"])
    mapping["主体ID"] = pd.to_numeric(mapping["主体ID"], errors="coerce").astype("Int64")
    mapping = mapping.dropna(subset=["主体ID"]).drop_duplicates(subset="主体ID")
    result["主体ID"] = pd.to_numeric(result["主体ID"], errors="coerce").astype("Int64")
    result = result.merge(mapping, on="主体ID", how="left")
    result["品类"] = result["品类"].fillna("其他")
    result["细类"] = result["细类"].fillna("其他")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair duplicated historical dashboard dates.")
    parser.add_argument("--apply", action="store_true", help="写入修复后的大表；默认只校验")
    args = parser.parse_args()

    if not HISTORY_FILE.exists():
        raise SystemExit(f"[ERROR] 未找到历史源表: {HISTORY_FILE}")

    current = normalize_dates(pd.read_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME))
    history = normalize_dates(pd.read_excel(HISTORY_FILE, sheet_name=SHEET_NAME))
    current_target = current[current["日期"].isin(TARGET_DATES)].copy()
    history_target = history[history["日期"].isin(TARGET_DATES)].copy()
    if set(history_target["日期"].dropna()) != set(TARGET_DATES):
        raise SystemExit("[ERROR] 历史源表未完整覆盖 2026-07-02 至 2026-07-05")

    current_cost = cost_by_date(current_target)
    history_cost = cost_by_date(history_target)
    audit = pd.DataFrame({"current": current_cost, "historical": history_cost}).reindex(TARGET_DATES)
    audit["ratio"] = audit["current"] / audit["historical"]
    print("修复前校验:")
    print(audit.round(2).to_string())
    if not (audit["ratio"].round(8) == 2).all():
        raise SystemExit("[ERROR] 当前数据不再是历史源表的精确两倍，已停止以避免误修复")

    print(f"当前重复行: {len(current_target)}；历史正确行: {len(history_target)}")
    if not args.apply:
        print("校验通过。传入 --apply 才会备份并写入修复。")
        return

    repaired_rows = apply_category_mapping(history_target)
    remaining = current[~current["日期"].isin(TARGET_DATES)].copy()
    repaired = pd.concat([remaining, repaired_rows.reindex(columns=current.columns)], ignore_index=True)
    repaired = repaired.sort_values("日期", kind="stable").reset_index(drop=True)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"万相台数据表_before_july2-5_repair_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    shutil.copy2(BIG_TABLE_PATH, backup)
    temp = BIG_TABLE_PATH.with_name(f"{BIG_TABLE_PATH.stem}.repair.tmp{BIG_TABLE_PATH.suffix}")
    repaired.to_excel(temp, sheet_name=SHEET_NAME, index=False)
    temp.replace(BIG_TABLE_PATH)
    print(f"已备份: {backup}")
    print(f"已修复: {BIG_TABLE_PATH}")
    print(f"修复后目标行: {len(repaired_rows)}；花费: {cost_by_date(repaired_rows).round(2).to_dict()}")


if __name__ == "__main__":
    main()
