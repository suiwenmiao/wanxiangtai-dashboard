#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将万相台商品报表与商品ID基础表进行匹配，补充品类和细类字段
"""

import pandas as pd

from config import BASE_TABLE_PATH, REPORT_DIR

# 找最新的UTF-8 CSV文件
csv_files = sorted(REPORT_DIR.glob("*_utf8.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
if not csv_files:
    # 如果没有UTF-8版本，尝试用GBK读取原始ZIP解压的CSV
    csv_files = sorted(REPORT_DIR.glob("商品报表_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)

if not csv_files:
    print("[ERROR] 未找到万相台报表CSV文件")
    exit(1)

CSV_PATH = csv_files[0]
OUTPUT_PATH = REPORT_DIR / CSV_PATH.stem.replace("_utf8", "") / "已匹配品类.xlsx"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

print(f"基础表: {BASE_TABLE_PATH}")
print(f"报表文件: {CSV_PATH}")
print(f"输出文件: {OUTPUT_PATH}")
print()

# ======================== 读取数据 ========================
print("正在读取商品ID基础表...")
df_base = pd.read_excel(BASE_TABLE_PATH)
print(f"  基础表行数: {len(df_base)}")
print(f"  基础表列名: {list(df_base.columns)}")

print("\n正在读取万相台报表...")
df_report = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
print(f"  报表行数: {len(df_report)}")
print(f"  报表列数: {len(df_report.columns)}")

# ======================== 数据清洗 ========================
# 确保主体ID为整数类型
df_base["主体ID"] = pd.to_numeric(df_base["主体ID"], errors="coerce").astype("Int64")
df_report["主体ID"] = pd.to_numeric(df_report["主体ID"], errors="coerce").astype("Int64")

# 去除基础表中的重复主体ID（保留第一条）
df_base_clean = df_base.drop_duplicates(subset=["主体ID"], keep="first")
print(f"\n基础表去重后行数: {len(df_base_clean)}")

# ======================== 匹配 ========================
print("\n正在匹配品类和细类...")

# 只从基础表中取需要的列
match_cols = ["主体ID", "品类", "细类"]
df_match = df_base_clean[match_cols]

# 左连接：以报表为主体，匹配基础表的品类和细类
df_result = df_report.merge(df_match, on="主体ID", how="left")

# 统计匹配结果
total = len(df_result)
matched = df_result["品类"].notna().sum()
unmatched = total - matched
match_rate = matched / total * 100

print(f"\n========== 匹配结果 ==========")
print(f"总行数: {total}")
print(f"成功匹配: {matched} ({match_rate:.1f}%)")
print(f"未匹配: {unmatched} ({100 - match_rate:.1f}%)")

# 显示未匹配的主体ID样例
if unmatched > 0:
    unmatched_ids = df_result[df_result["品类"].isna()]["主体ID"].unique()[:20]
    print(f"\n未匹配的主体ID样例（前20个）:")
    for uid in unmatched_ids:
        # 找对应的主体名称
        name = df_result[df_result["主体ID"] == uid]["主体名称"].iloc[0] if uid is not None else ""
        print(f"  {uid}: {name}")

# 品类分布
print(f"\n品类分布:")
print(df_result["品类"].value_counts(dropna=False).to_string())

print(f"\n细类分布（前20）:")
print(df_result["细类"].value_counts(dropna=False).head(20).to_string())

# ======================== 保存结果 ========================
print(f"\n正在保存到: {OUTPUT_PATH}")
df_result.to_excel(OUTPUT_PATH, index=False, engine="openpyxl")
print(f"保存完成！文件大小: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.1f} MB")
