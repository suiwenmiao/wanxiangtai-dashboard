#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate local creative dashboard data for the frontend."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from config import BASE_TABLE_PATH, FRONTEND_DIR, REPORT_DIR


PRIVATE_DATA_DIR = FRONTEND_DIR / "private-data"
PUBLIC_DATA_DIR = FRONTEND_DIR / "public" / "data"
INDEX_FILE = PRIVATE_DATA_DIR / "creative-index.json"
DASHBOARD_CATEGORIES = ("手机", "DT")
NUMERIC_COLS = [
    "展现量",
    "点击量",
    "花费",
    "总成交金额",
    "直接成交金额",
    "间接成交金额",
    "总成交笔数",
    "总购物车数",
    "收藏宝贝数",
    "总收藏加购数",
]


def report_range() -> tuple[str, str]:
    start = os.environ.get("WORKBUDDY_REPORT_START", "").strip()
    end = os.environ.get("WORKBUDDY_REPORT_END", "").strip()
    if start or end:
        if not start or not end:
            raise SystemExit("[ERROR] WORKBUDDY_REPORT_START 和 WORKBUDDY_REPORT_END 必须同时设置")
        start_date = datetime.strptime(start, "%Y-%m-%d").strftime("%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d").strftime("%Y-%m-%d")
        if start_date > end_date:
            raise SystemExit("[ERROR] 开始日期不能晚于结束日期")
        return start_date, end_date
    date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return date, date


def read_csv(path: Path) -> pd.DataFrame:
    errors = []
    for enc in ["utf-8-sig", "utf-8", "gb18030", "gbk"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            errors.append(f"{enc}: {e}")
    raise SystemExit("[ERROR] 无法读取创意报表: " + "；".join(errors))


def normalize_id(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def load_creatives(start_date: str, end_date: str) -> pd.DataFrame:
    range_label = start_date if start_date == end_date else f"{start_date}_{end_date}"
    report_path = Path(os.environ.get("WORKBUDDY_CREATIVE_REPORT_FILE", REPORT_DIR / f"万相台创意报表_{range_label}.csv"))
    if not report_path.exists():
        raise SystemExit(f"[ERROR] 未找到创意报表: {report_path}")
    if not BASE_TABLE_PATH.exists():
        raise SystemExit(f"[ERROR] 未找到基础表: {BASE_TABLE_PATH}")

    df = read_csv(report_path)
    required = {"日期", "计划ID", "计划名字", "创意ID", "创意名字", "主体ID"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise SystemExit(f"[ERROR] 创意报表缺少字段: {', '.join(missing)}")

    df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    df = df[(df["日期"] >= start_date) & (df["日期"] <= end_date)].copy()
    for col in NUMERIC_COLS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    base = pd.read_excel(BASE_TABLE_PATH)
    base_id_column = "主体ID" if "主体ID" in base.columns else "商品ID" if "商品ID" in base.columns else None
    missing_base = ["品类"] if "品类" not in base.columns else []
    if base_id_column is None:
        missing_base.insert(0, "主体ID/商品ID")
    if missing_base:
        raise SystemExit(f"[ERROR] 基础表缺少字段: {', '.join(missing_base)}")

    keep_cols = [c for c in [base_id_column, "主体名称", "产品", "商品名称", "品类", "细类", "子类", "二级分类"] if c in base.columns]
    base = base[keep_cols].copy()
    if "主体名称" not in base.columns and "商品名称" in base.columns:
        base["主体名称"] = base["商品名称"]
    if base_id_column != "主体ID":
        base = base.rename(columns={base_id_column: "主体ID"})
    df["主体ID_key"] = normalize_id(df["主体ID"])
    base["主体ID_key"] = normalize_id(base["主体ID"])
    merged = df.merge(base.drop(columns=["主体ID"]), how="left", on="主体ID_key")
    merged["品类"] = merged["品类"].fillna("未匹配")
    return merged.copy()


def aggregate(df: pd.DataFrame) -> tuple[list[dict], list[dict], dict]:
    for col in ["素材ID", "素材名称", "素材内容", "素材尺寸", "素材类型"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    df["素材ID"] = normalize_id(df["素材ID"])
    df["imageUrl"] = df["素材内容"].where(df["素材内容"].str.startswith(("http://", "https://")), "")
    df["isImage"] = (df["素材类型"] == "图片") & df["imageUrl"].ne("")
    # A picture can be bound to several creative IDs. The image URL is the
    # visual identity, so it must win over material ID when building the matrix.
    df["materialKey"] = df["imageUrl"]
    df.loc[df["materialKey"].eq(""), "materialKey"] = df["素材ID"]
    df.loc[df["materialKey"].isin(["", "nan", "None"]), "materialKey"] = (
        df["素材名称"] + "|" + df["素材内容"]
    )

    group_cols = [
        "日期",
        "计划ID",
        "计划名字",
        "创意ID",
        "创意名字",
        "主体ID_key",
        "主体名称",
        "品类",
        "场景ID",
        "场景名字",
        "产品",
        "细类",
        "materialKey",
        "素材ID",
        "素材名称",
        "素材内容",
        "素材尺寸",
        "素材类型",
        "imageUrl",
        "isImage",
    ]
    for col in group_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    groups = df.groupby(group_cols, dropna=False).agg(
        impressions=("展现量", "sum"),
        clicks=("点击量", "sum"),
        cost=("花费", "sum"),
        totalSales=("总成交金额", "sum"),
        directSales=("直接成交金额", "sum"),
        orders=("总成交笔数", "sum"),
        carts=("总购物车数", "sum"),
        favorites=("收藏宝贝数", "sum"),
        favCart=("总收藏加购数", "sum"),
    ).reset_index()

    rows = []
    for _, r in groups.iterrows():
        impressions = float(r["impressions"])
        clicks = float(r["clicks"])
        cost = float(r["cost"])
        total_sales = float(r["totalSales"])
        orders = float(r["orders"])
        rows.append({
            "date": r["日期"],
            "planId": r["计划ID"],
            "planName": r["计划名字"] or "未命名计划",
            "creativeId": r["创意ID"],
            "creativeName": r["创意名字"] or "未命名创意",
            "subjectId": r["主体ID_key"],
            "subjectName": r["主体名称"],
            "category": r["品类"] or "未匹配",
            "scenarioId": r["场景ID"],
            "scenarioName": r["场景名字"] or "未命名场景",
            "productName": r["产品"],
            "subCategory": r["细类"] or "未分类",
            "materialId": r["素材ID"],
            "materialName": r["素材名称"] or r["创意名字"] or "未命名素材",
            "materialSize": r["素材尺寸"],
            "materialType": r["素材类型"],
            "imageUrl": r["imageUrl"],
            "isImage": r["isImage"] == "True",
            "impressions": int(impressions),
            "clicks": int(clicks),
            "cost": round(cost, 2),
            "totalSales": round(total_sales, 2),
            "directSales": round(float(r["directSales"]), 2),
            "orders": int(orders),
            "carts": int(r["carts"]),
            "favorites": int(r["favorites"]),
            "favCart": int(r["favCart"]),
            "ctr": clicks / impressions if impressions > 0 else 0,
            "cvr": orders / clicks if clicks > 0 else 0,
            "roi": total_sales / cost if cost > 0 else 0,
            "cpc": cost / clicks if clicks > 0 else 0,
        })

    rows.sort(key=lambda item: (item["clicks"], item["ctr"], item["totalSales"]), reverse=True)
    ctr_values = sorted([r["ctr"] for r in rows if r["clicks"] >= 10])
    cvr_values = sorted([r["cvr"] for r in rows if r["orders"] > 0])
    ctr_cutoff = ctr_values[int(len(ctr_values) * 0.75)] if ctr_values else 0
    cvr_cutoff = cvr_values[int(len(cvr_values) * 0.75)] if cvr_values else 0
    for r in rows:
        r["isHighClick"] = r["clicks"] >= 20 and r["ctr"] >= max(ctr_cutoff, 0.03)
        r["isHighConvert"] = r["orders"] > 0 and r["cvr"] >= max(cvr_cutoff, 0.02)

    plan_map = {}
    for r in rows:
        plan = plan_map.setdefault(r["planName"], {
            "planName": r["planName"],
            "impressions": 0,
            "clicks": 0,
            "cost": 0,
            "totalSales": 0,
            "orders": 0,
            "creativeCount": 0,
            "highClickCount": 0,
        })
        plan["impressions"] += r["impressions"]
        plan["clicks"] += r["clicks"]
        plan["cost"] += r["cost"]
        plan["totalSales"] += r["totalSales"]
        plan["orders"] += r["orders"]
        plan["creativeCount"] += 1
        plan["highClickCount"] += 1 if r["isHighClick"] else 0

    plans = []
    for p in plan_map.values():
        p["cost"] = round(p["cost"], 2)
        p["totalSales"] = round(p["totalSales"], 2)
        p["ctr"] = p["clicks"] / p["impressions"] if p["impressions"] > 0 else 0
        p["cvr"] = p["orders"] / p["clicks"] if p["clicks"] > 0 else 0
        p["roi"] = p["totalSales"] / p["cost"] if p["cost"] > 0 else 0
        plans.append(p)
    plans.sort(key=lambda item: item["cost"], reverse=True)

    totals = {
        "impressions": int(sum(r["impressions"] for r in rows)),
        "clicks": int(sum(r["clicks"] for r in rows)),
        "cost": round(sum(r["cost"] for r in rows), 2),
        "totalSales": round(sum(r["totalSales"] for r in rows), 2),
        "orders": int(sum(r["orders"] for r in rows)),
        "creativeCount": len(rows),
        "highClickCount": sum(1 for r in rows if r["isHighClick"]),
    }
    totals["ctr"] = totals["clicks"] / totals["impressions"] if totals["impressions"] > 0 else 0
    totals["cvr"] = totals["orders"] / totals["clicks"] if totals["clicks"] > 0 else 0
    totals["roi"] = totals["totalSales"] / totals["cost"] if totals["cost"] > 0 else 0
    return rows, plans, totals


def apply_visual_dedup(rows: list[dict], range_label: str) -> None:
    """Attach the visual-image identity produced by dedupe_creative_images.py."""
    mapping_path = REPORT_DIR / f"创意图片视觉去重_{range_label}.json"
    if not mapping_path.exists():
        for row in rows:
            row["visualKey"] = row["imageUrl"] or row["materialId"]
            row["mainVisualKey"] = row["visualKey"]
        return
    dedup_data = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping = dedup_data.get("canonicalByUrl", {})
    main_mapping = dedup_data.get("mainVisualBySubjectUrl", {})
    for row in rows:
        row["visualKey"] = mapping.get(row["imageUrl"], row["imageUrl"] or row["materialId"])
        main_key = f"{row['subjectId']}::{row['imageUrl']}"
        # The business subject is the most reliable product-main-image boundary.
        # Default view therefore keeps one representative image per product;
        # strict visual variants remain available through ``visualKey``.
        row["mainVisualKey"] = f"subject:{row['subjectId']}" if row["isImage"] and row["subjectId"] else main_mapping.get(main_key, row["visualKey"])


def main() -> None:
    start_date, end_date = report_range()
    range_label = start_date if start_date == end_date else f"{start_date}_{end_date}"
    df = load_creatives(start_date, end_date)
    rows, _, _ = aggregate(df)
    apply_visual_dedup(rows, range_label)
    rows = [row for row in rows if row["category"] in DASHBOARD_CATEGORIES]
    categories = [category for category in DASHBOARD_CATEGORIES if any(row["category"] == category for row in rows)]
    PRIVATE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for stale_file in PRIVATE_DATA_DIR.glob("creative-*.json"):
        if stale_file.name != INDEX_FILE.name:
            stale_file.unlink()
    for category in categories:
        category_rows = [row for row in rows if row["category"] == category]
        category_file = PRIVATE_DATA_DIR / f"creative-{category}.json"
        category_file.write_text(json.dumps({
            "dateStart": start_date,
            "dateEnd": end_date,
            "category": category,
            "records": category_rows,
        }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    index_payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "dateStart": start_date,
        "dateEnd": end_date,
        "categories": categories,
        "notes": [
            "数据来自万相台创意报表的素材粒度导出。",
            "素材看板仅保留手机和 DT 品类。",
            "素材内容为图片链接时，会在本地素材看板直接展示缩略图。",
        ],
    }
    INDEX_FILE.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成索引: {INDEX_FILE}")
    print(f"私有创意数据目录: {PRIVATE_DATA_DIR}")
    print(f"创意记录: {len(rows)}")
    print(f"计划数: {len({row['planId'] for row in rows})}")
    print(f"高点击素材: {sum(1 for row in rows if row['isHighClick'])}")


if __name__ == "__main__":
    main()
