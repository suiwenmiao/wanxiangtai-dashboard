#!/usr/bin/env python3
"""Generate dashboard JSON — aggregates by category, sub-category, and subject."""

from __future__ import annotations
import json
from datetime import datetime
import pandas as pd
from config import BIG_TABLE_PATH, FRONTEND_DATA_FILE, SHEET_NAME

NUMERIC_COLS = [
    "花费", "总成交金额", "直接成交金额", "间接成交金额", "总成交笔数",
    "点击量", "展现量", "总购物车数", "收藏宝贝数", "总收藏加购数",
]


def load_data() -> pd.DataFrame:
    if not BIG_TABLE_PATH.exists():
        raise SystemExit(f"[ERROR] 未找到数据大表: {BIG_TABLE_PATH}")
    print(f"读取数据大表: {BIG_TABLE_PATH}")
    df = pd.read_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME)
    print(f"  原始行数: {len(df)}")

    required = {"日期", "品类", "细类", "主体ID", "花费", "总成交金额"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise SystemExit(f"[ERROR] 缺少必要字段: {', '.join(missing)}")

    df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    df["品类"] = df["品类"].fillna("其他")
    df["细类"] = df["细类"].fillna("其他")

    for col in NUMERIC_COLS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def build_records(df: pd.DataFrame) -> list[dict]:
    agg = df.groupby(["日期", "品类"], dropna=False).agg({
        "花费": "sum", "总成交金额": "sum", "直接成交金额": "sum",
        "间接成交金额": "sum", "总成交笔数": "sum", "点击量": "sum",
        "展现量": "sum", "总购物车数": "sum", "收藏宝贝数": "sum",
        "总收藏加购数": "sum",
    }).reset_index().sort_values(["日期", "品类"])
    return [
        {
            "date": r["日期"], "category": r["品类"],
            "cost": round(float(r["花费"]), 2),
            "totalSales": round(float(r["总成交金额"]), 2),
            "directSales": round(float(r["直接成交金额"]), 2),
            "indirectSales": round(float(r["间接成交金额"]), 2),
            "orders": int(r["总成交笔数"]), "clicks": int(r["点击量"]),
            "impressions": int(r["展现量"]), "carts": int(r["总购物车数"]),
            "favorites": int(r["收藏宝贝数"]), "favCart": int(r["总收藏加购数"]),
        } for _, r in agg.iterrows()
    ]


def build_sub_category_records(df: pd.DataFrame) -> list[dict]:
    agg = df.groupby(["日期", "品类", "细类"], dropna=False).agg({
        "花费": "sum", "总成交金额": "sum", "直接成交金额": "sum",
        "间接成交金额": "sum", "总成交笔数": "sum", "点击量": "sum",
        "展现量": "sum", "总购物车数": "sum", "收藏宝贝数": "sum",
        "总收藏加购数": "sum",
    }).reset_index().sort_values(["日期", "品类", "细类"])
    return [
        {
            "date": r["日期"], "category": r["品类"], "subCategory": r["细类"],
            "cost": round(float(r["花费"]), 2),
            "totalSales": round(float(r["总成交金额"]), 2),
            "directSales": round(float(r["直接成交金额"]), 2),
            "orders": int(r["总成交笔数"]), "clicks": int(r["点击量"]),
            "impressions": int(r["展现量"]), "carts": int(r["总购物车数"]),
        } for _, r in agg.iterrows()
    ]


def build_subjects(df: pd.DataFrame) -> list[dict]:
    """Aggregate by subject, include scenario/plan breakdown."""
    subjects_map = {}
    for _, r in df.iterrows():
        sid = str(r["主体ID"])
        if sid == "nan":
            continue
        if sid not in subjects_map:
            subjects_map[sid] = {
                "subjectId": sid,
                "subjectName": str(r.get("主体名称", "")),
                "category": r["品类"], "subCategory": r["细类"],
                "cost": 0, "totalSales": 0, "directSales": 0,
                "orders": 0, "clicks": 0, "impressions": 0, "carts": 0,
                "scenarios": {}
            }
        s = subjects_map[sid]
        s["cost"] += r["花费"]; s["totalSales"] += r["总成交金额"]
        s["directSales"] += r["直接成交金额"]; s["orders"] += r["总成交笔数"]
        s["clicks"] += r["点击量"]; s["impressions"] += r["展现量"]
        s["carts"] += r["总购物车数"]
        scene_name = r.get("场景名字", "")
        if pd.isna(scene_name) or not str(scene_name).strip():
            scene_name = "未分类"
        scene_key = f"{scene_name}|{r.get('计划名字','')}"
        if scene_key not in s["scenarios"]:
            s["scenarios"][scene_key] = {
                "scenario": scene_name,
                "planName": str(r.get("计划名字", "")),
                "cost": 0, "totalSales": 0, "clicks": 0, "impressions": 0,
                "orders": 0,
            }
        sc = s["scenarios"][scene_key]
        sc["cost"] += r["花费"]; sc["totalSales"] += r["总成交金额"]
        sc["clicks"] += r["点击量"]; sc["impressions"] += r["展现量"]; sc["orders"] += int(r["总成交笔数"])

    result = []
    for sid, s in subjects_map.items():
        scenarios = sorted(s["scenarios"].values(), key=lambda x: -x["cost"])
        for sc in scenarios:
            sc["cost"] = round(sc["cost"], 2)
            sc["totalSales"] = round(sc["totalSales"], 2)
        result.append({
            "subjectId": sid, "subjectName": s["subjectName"],
            "category": s["category"], "subCategory": s["subCategory"],
            "cost": round(s["cost"], 2),
            "totalSales": round(s["totalSales"], 2),
            "directSales": round(s["directSales"], 2),
            "orders": int(s["orders"]), "clicks": int(s["clicks"]),
            "impressions": int(s["impressions"]), "carts": int(s["carts"]),
            "scenarios": scenarios,
        })
    result.sort(key=lambda x: -x["cost"])
    return result


def build_subject_date_records(df: pd.DataFrame) -> list[dict]:
    """Aggregate by date + subjectId for date-filtered subject queries."""
    groups = df.groupby(["日期", "主体ID"], as_index=False).agg(
        cost=("花费", "sum"),
        totalSales=("总成交金额", "sum"),
        clicks=("点击量", "sum"),
        impressions=("展现量", "sum"),
        orders=("总成交笔数", "sum"),
    )
    result = []
    for _, r in groups.iterrows():
        sid = str(r["主体ID"])
        if sid == "nan" or pd.isna(r.get("日期")):
            continue
        result.append({
            "date": str(r["日期"]),
            "subjectId": sid,
            "cost": round(float(r["cost"]), 2),
            "totalSales": round(float(r["totalSales"]), 2),
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "orders": int(r["orders"]),
        })
    return result

def build_category_scenario_records(df: pd.DataFrame) -> list[dict]:
    """Aggregate by date + category + scenario for accurate channel summary."""
    df.loc[df["场景名字"].isna() | (df["场景名字"] == ""), "场景名字"] = "未分类"
    groups = df.groupby(["日期", "品类", "场景名字"], as_index=False).agg(
        cost=("花费", "sum"),
        totalSales=("总成交金额", "sum"),
        clicks=("点击量", "sum"),
        impressions=("展现量", "sum"),
        orders=("总成交笔数", "sum"),
    )
    result = []
    for _, r in groups.iterrows():
        result.append({
            "date": str(r["日期"]),
            "category": str(r["品类"]),
            "scenario": str(r["场景名字"]),
            "cost": round(float(r["cost"]), 2),
            "totalSales": round(float(r["totalSales"]), 2),
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "orders": int(r["orders"]),
        })
    return result


def build_subject_plan_records(df: pd.DataFrame) -> list[dict]:
    """Aggregate by date + subjectId + planId for accurate plan-level data."""
    groups = df.groupby(["日期", "主体ID", "计划ID", "计划名字", "场景名字"], as_index=False).agg(
        cost=("花费", "sum"),
        totalSales=("总成交金额", "sum"),
        clicks=("点击量", "sum"),
        impressions=("展现量", "sum"),
        orders=("总成交笔数", "sum"),
    )
    result = []
    for _, r in groups.iterrows():
        sid = str(r["主体ID"])
        scene = str(r["场景名字"]).strip()
        if sid == "nan" or not scene or pd.isna(r.get("日期")):
            continue
        result.append({
            "date": str(r["日期"]),
            "subjectId": sid,
            "planId": str(r["计划ID"]),
            "planName": str(r["计划名字"]),
            "scenario": scene,
            "cost": round(float(r["cost"]), 2),
            "totalSales": round(float(r["totalSales"]), 2),
            "clicks": int(r["clicks"]),
            "impressions": int(r["impressions"]),
            "orders": int(r["orders"]),
        })
    return result


def main() -> None:
    print("=" * 50)
    print("生成 Vue 看板数据（含细类 + 主体）")
    print("=" * 50)
    df = load_data()

    records = build_records(df)
    subCategoryRecords = build_sub_category_records(df)
    subjects = build_subjects(df)
    subjectDateRecords = build_subject_date_records(df)
    categoryScenarioRecords = build_category_scenario_records(df)
    subjectPlanRecords = build_subject_plan_records(df)

    payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "dateMin": records[0]["date"] if records else None,
        "dateMax": records[-1]["date"] if records else None,
        "categories": sorted(df["品类"].unique().tolist()),
        "records": records,
        "subCategoryRecords": subCategoryRecords,
        "subjects": subjects,
        "subjectDateRecords": subjectDateRecords,
        "categoryScenarioRecords": categoryScenarioRecords,
        "subjectPlanRecords": subjectPlanRecords,
    }

    FRONTEND_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_DATA_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    size_kb = FRONTEND_DATA_FILE.stat().st_size / 1024
    print(f"已生成: {FRONTEND_DATA_FILE}")
    print(f"  记录: {len(records)}")
    print(f"  细类记录: {len(subCategoryRecords)}")
    print(f"  主体: {len(subjects)}")
    print(f"  主体日期记录: {len(subjectDateRecords)}")
    print(f"  品类场景记录: {len(categoryScenarioRecords)}")
    print(f"  主体计划记录: {len(subjectPlanRecords)}")
    print(f"  文件大小: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
