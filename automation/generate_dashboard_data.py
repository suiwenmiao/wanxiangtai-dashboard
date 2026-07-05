#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate dashboard JSON consumed by the Vue frontend."""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from config import BIG_TABLE_PATH, FRONTEND_DATA_FILE, SHEET_NAME


NUMERIC_COLS = [
    "花费",
    "总成交金额",
    "直接成交金额",
    "间接成交金额",
    "总成交笔数",
    "点击量",
    "展现量",
    "总购物车数",
    "收藏宝贝数",
    "总收藏加购数",
]


def load_and_aggregate() -> pd.DataFrame:
    """Read the accumulated workbook and aggregate by date and category."""
    if not BIG_TABLE_PATH.exists():
        raise SystemExit(f"[ERROR] 未找到数据大表: {BIG_TABLE_PATH}")

    print(f"读取数据大表: {BIG_TABLE_PATH}")
    df = pd.read_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME)
    print(f"  原始行数: {len(df)}")

    required = {"日期", "品类", "花费", "总成交金额", "直接成交金额", "总成交笔数", "点击量", "展现量"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise SystemExit(f"[ERROR] 数据大表缺少必要字段: {', '.join(missing)}")

    df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    df["品类"] = df["品类"].fillna("其他")

    for col in NUMERIC_COLS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    agg = (
        df.groupby(["日期", "品类"], dropna=False)
        .agg(
            {
                "花费": "sum",
                "总成交金额": "sum",
                "直接成交金额": "sum",
                "间接成交金额": "sum",
                "总成交笔数": "sum",
                "点击量": "sum",
                "展现量": "sum",
                "总购物车数": "sum",
                "收藏宝贝数": "sum",
                "总收藏加购数": "sum",
            }
        )
        .reset_index()
        .sort_values(["日期", "品类"])
    )

    print(f"  聚合行数: {len(agg)}")
    print(f"  日期范围: {agg['日期'].min()} ~ {agg['日期'].max()}")
    print(f"  品类: {', '.join(sorted(agg['品类'].unique()))}")
    return agg


def to_records(agg: pd.DataFrame) -> list[dict]:
    records = []
    for _, row in agg.iterrows():
        records.append(
            {
                "date": row["日期"],
                "category": row["品类"],
                "cost": round(float(row["花费"]), 2),
                "totalSales": round(float(row["总成交金额"]), 2),
                "directSales": round(float(row["直接成交金额"]), 2),
                "indirectSales": round(float(row["间接成交金额"]), 2),
                "orders": int(row["总成交笔数"]),
                "clicks": int(row["点击量"]),
                "impressions": int(row["展现量"]),
                "carts": int(row["总购物车数"]),
                "favorites": int(row["收藏宝贝数"]),
                "favCart": int(row["总收藏加购数"]),
            }
        )
    return records


def build_payload(agg: pd.DataFrame) -> dict:
    records = to_records(agg)
    dates = sorted(agg["日期"].unique().tolist())
    categories = sorted(agg["品类"].unique().tolist())
    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "dateMin": dates[0] if dates else None,
        "dateMax": dates[-1] if dates else None,
        "categories": categories,
        "records": records,
    }


def main() -> None:
    print("=" * 50)
    print("生成 Vue 看板数据")
    print("=" * 50)
    agg = load_and_aggregate()
    payload = build_payload(agg)

    FRONTEND_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_DATA_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    size_kb = FRONTEND_DATA_FILE.stat().st_size / 1024
    print(f"已生成: {FRONTEND_DATA_FILE}")
    print(f"文件大小: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
