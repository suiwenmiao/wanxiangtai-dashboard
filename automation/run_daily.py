#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每天上午8:30自动运行万相台报表下载
使用方法：
  python3 automation/run_daily.py once
  python3 automation/run_daily.py loop
  或设置系统cron：
  30 8 * * * cd /full/path && AUTO_DEPLOY=1 python3 automation/run_daily.py once >> /tmp/alimama_cron.log 2>&1
"""

import subprocess
import sys
import time
from datetime import datetime, timedelta

from config import AUTO_DEPLOY, AUTOMATION_DIR, BIG_TABLE_PATH, DAILY_LOG_FILE, REPORT_DIR, SHEET_NAME


SCRIPT_DIR = AUTOMATION_DIR
PYTHON = sys.executable
DOWNLOAD_SCRIPT = SCRIPT_DIR / "wanxiangtai_download.py"
MATCH_SCRIPT = SCRIPT_DIR / "match_category.py"
DEPLOY_SCRIPT = SCRIPT_DIR / "deploy_static.py"
LOG_FILE = DAILY_LOG_FILE
RUN_HOUR = 8
RUN_MINUTE = 30


def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run_download():
    """运行下载脚本"""
    log("[SKILL-步骤1] 开始运行下载：必须按计划/场景维度导出79列格式")
    try:
        result = subprocess.run(
            [PYTHON, str(DOWNLOAD_SCRIPT), "download"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=600,
        )
        log(f"下载脚本退出码: {result.returncode}")
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-10:]:
                log(f"  [stdout] {line}")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-5:]:
                log(f"  [stderr] {line}")
        return result.returncode == 0
    except Exception as e:
        log(f"运行下载脚本失败: {e}")
        return False




def run_match_and_append():
    """Run match_category.py and append matched data to big table."""
    import pandas as pd
    log("[SKILL-步骤2] 开始匹配品类/细类：用商品ID基础表补充品类和细类")
    result = subprocess.run(
        [PYTHON, str(MATCH_SCRIPT)],
        cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=300,
    )
    log(f"匹配脚本退出码: {result.returncode}")
    for line in result.stdout.strip().split("
")[-10:]:
        log(f"  [match] {line}")

    matched_files = sorted(REPORT_DIR.rglob("已匹配品类.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matched_files:
        log("[ERROR] 未找到已匹配品类.xlsx，跳过追加")
        return False

    matched_path = matched_files[0]
    log(f"已匹配文件: {matched_path}")
    try:
        df_new = pd.read_excel(matched_path, sheet_name=SHEET_NAME)
    except Exception:
        df_new = pd.read_excel(matched_path)
    log(f"  新数据行数: {len(df_new)}")
    # SKILL-验证：检查是否包含场景名字列
    if "场景名字" not in df_new.columns:
        log(f"[SKILL-ERROR] 严重：下载的CSV缺少[场景名字]列！格式不符合79列标准")
    elif df_new["场景名字"].isna().all() or (df_new["场景名字"] == "").all():
        log(f"[SKILL-ERROR] 严重：场景名字列全部为空！格式不符合79列标准")
    else:
        log(f"[SKILL] ✓ CSV格式验证通过，场景名字列正常")

    if BIG_TABLE_PATH.exists():
        try:
            df_big = pd.read_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME)
        except Exception:
            df_big = pd.read_excel(BIG_TABLE_PATH)
        log(f"  大表原有行数: {len(df_big)}")
        df_combined = pd.concat([df_big, df_new], ignore_index=True)
        dedup_cols = [c for c in ["日期", "主体ID", "计划ID"] if c in df_combined.columns]
        if dedup_cols:
            before = len(df_combined)
            df_combined = df_combined.drop_duplicates(subset=dedup_cols, keep="last")
            log(f"  去重: {before} → {len(df_combined)}")
    else:
        df_combined = df_new

    df_combined.to_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME, index=False, engine="openpyxl")
    log(f"大表已更新: {BIG_TABLE_PATH} ({len(df_combined)} 行)")
    return True


def run_deploy():
    """生成静态站点并推送到 GitHub，触发 GitHub Pages 部署"""
    if not AUTO_DEPLOY:
        log("AUTO_DEPLOY 未开启，跳过线上部署。需要自动部署时使用: AUTO_DEPLOY=1 python3 automation/run_daily.py")
        return True

    log("开始生成并发布静态看板...")
    try:
        result = subprocess.run(
            [PYTHON, str(DEPLOY_SCRIPT), "--commit", "--push"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        log(f"部署脚本退出码: {result.returncode}")
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-20:]:
                log(f"  [deploy stdout] {line}")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-10:]:
                log(f"  [deploy stderr] {line}")
        return result.returncode == 0
    except Exception as e:
        log(f"运行部署脚本失败: {e}")
        return False


def seconds_until_next_run():
    """计算距离下次自动运行时间还有多少秒"""
    now = datetime.now()
    today_run_at = now.replace(hour=RUN_HOUR, minute=RUN_MINUTE, second=0, microsecond=0)
    if now < today_run_at:
        target = today_run_at
    else:
        target = today_run_at + timedelta(days=1)
    seconds = (target - now).total_seconds()
    return seconds, target


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "once"
    log("=== 万相台报表每日下载服务启动 ===")
    log(f"运行模式: {mode}")
    log(f"脚本目录: {SCRIPT_DIR}")

    download_ok = run_download()
    match_ok = True
    if download_ok:
        match_ok = run_match_and_append()
    deploy_ok = True
    if match_ok:
        deploy_ok = run_deploy()

    if mode == "once":
        log("单次任务完成，退出。")
        sys.exit(0 if download_ok and match_ok and deploy_ok else 1)
        return

    if mode != "loop":
        log(f"未知运行模式: {mode}，可用模式: once | loop")
        return

    log("进入常驻循环模式，下次运行时间将显示在日志中")
    # 然后每天 8:30 运行
    while True:
        seconds, target = seconds_until_next_run()
        log(f"下次运行时间: {target.strftime('%Y-%m-%d %H:%M:%S')} (约{int(seconds/60)}分钟后)")
        time.sleep(seconds)
        if run_download() and run_match_and_append():
            run_deploy()


if __name__ == "__main__":
    main()
