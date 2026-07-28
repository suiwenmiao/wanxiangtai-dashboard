#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每天上午7:30自动运行万相台报表下载
使用方法：
  python3 automation/run_daily.py once
  python3 automation/run_daily.py loop
  或设置系统cron：
  30 7 * * * cd /full/path && AUTO_DEPLOY=1 python3 automation/run_daily.py once >> /tmp/alimama_cron.log 2>&1
"""

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

from config import AUTO_DEPLOY, AUTOMATION_DIR, DAILY_LOG_FILE


SCRIPT_DIR = AUTOMATION_DIR
PYTHON = sys.executable
DOWNLOAD_SCRIPT = SCRIPT_DIR / "wanxiangtai_download.py"
CREATIVE_REPORT_SCRIPT = SCRIPT_DIR / "creative_report_probe.py"
CREATIVE_MERGE_SCRIPT = SCRIPT_DIR / "merge_creative_reports.py"
CREATIVE_DATA_SCRIPT = SCRIPT_DIR / "generate_creative_data.py"
CREATIVE_DEDUP_SCRIPT = SCRIPT_DIR / "dedupe_creative_images.py"
DEPLOY_SCRIPT = SCRIPT_DIR / "deploy_static.py"
LOG_FILE = DAILY_LOG_FILE
RUN_HOUR = 7
RUN_MINUTE = 30
DOWNLOAD_TIMEOUT = int(os.environ.get("WORKBUDDY_DOWNLOAD_TIMEOUT", "1200"))
CREATIVE_DOWNLOAD_TIMEOUT = int(os.environ.get("WORKBUDDY_CREATIVE_DOWNLOAD_TIMEOUT", "1200"))
CREATIVE_DEDUP_TIMEOUT = int(os.environ.get("WORKBUDDY_CREATIVE_DEDUP_TIMEOUT", "600"))
DEPLOY_TIMEOUT = int(os.environ.get("WORKBUDDY_DEPLOY_TIMEOUT", "600"))
DOWNLOAD_ATTEMPTS = int(os.environ.get("WORKBUDDY_DOWNLOAD_ATTEMPTS", "6"))
DOWNLOAD_RETRY_DELAY = int(os.environ.get("WORKBUDDY_DOWNLOAD_RETRY_DELAY", "1800"))


def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def acquire_lock():
    """Prevent overlapping daily pipelines."""
    try:
        import fcntl

        lock_path = LOG_FILE.with_name("wanxiangtai_daily.lock")
        lock_file = open(lock_path, "w", encoding="utf-8")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            log(f"[ERROR] 已有每日任务在运行，跳过本次执行: {lock_path}")
            return None
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(f"{os.getpid()}\n")
        lock_file.flush()
        return lock_file
    except Exception as e:
        log(f"[WARN] 获取每日任务锁失败，将继续执行: {e}")
        return True


def run_download(attempt: int = 1, report_date: str | None = None, force_download: bool = False):
    """运行下载脚本，可指定历史日期以回补延迟归因数据。"""
    date_label = f" · {report_date}" if report_date else ""
    log(f"[步骤1] 开始下载并更新大表（第 {attempt}/{DOWNLOAD_ATTEMPTS} 次{date_label}）")
    try:
        env = os.environ.copy()
        if report_date:
            env["WORKBUDDY_REPORT_DATE"] = report_date
        if attempt > 1 or force_download:
            env["FORCE_DOWNLOAD"] = "1"
        result = subprocess.run(
            [PYTHON, str(DOWNLOAD_SCRIPT), "download"],
            cwd=SCRIPT_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=DOWNLOAD_TIMEOUT,
        )
        log(f"下载脚本退出码: {result.returncode}")
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-30:]:
                log(f"  [stdout] {line}")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-10:]:
                log(f"  [stderr] {line}")
        return result.returncode == 0
    except subprocess.TimeoutExpired as e:
        log(f"运行下载脚本超时: {DOWNLOAD_TIMEOUT} 秒")
        stdout = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else e.stdout
        stderr = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else e.stderr
        if stdout:
            for line in stdout.strip().split("\n")[-30:]:
                log(f"  [stdout] {line}")
        if stderr:
            for line in stderr.strip().split("\n")[-10:]:
                log(f"  [stderr] {line}")
        return False
    except Exception as e:
        log(f"运行下载脚本失败: {e}")
        return False


def run_creative_pipeline() -> bool:
    """Download yesterday's creative report and rebuild the full material history."""
    log("[步骤2] 开始更新创意素材看板...")
    download_env = os.environ.copy()
    history_env = os.environ.copy()
    history_start = history_env.get("WORKBUDDY_CREATIVE_HISTORY_START", "2026-07-01")
    history_end = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    history_env["WORKBUDDY_REPORT_START"] = history_start
    history_env["WORKBUDDY_REPORT_END"] = history_end
    history_env.pop("WORKBUDDY_CREATIVE_REPORT_FILE", None)
    log(f"  创意数据范围: {history_start} 至 {history_end}")
    steps = [
        ("下载创意报表", [PYTHON, str(CREATIVE_REPORT_SCRIPT)], CREATIVE_DOWNLOAD_TIMEOUT, download_env),
        ("合并创意历史报表", [PYTHON, str(CREATIVE_MERGE_SCRIPT)], DOWNLOAD_TIMEOUT, history_env),
        ("生成创意看板数据", [PYTHON, str(CREATIVE_DATA_SCRIPT)], DOWNLOAD_TIMEOUT, history_env),
        (
            "主图视觉去重",
            [
                os.environ.get(
                    "WORKBUDDY_IMAGE_PYTHON",
                    "/Users/suiwenmiao/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
                ),
                str(CREATIVE_DEDUP_SCRIPT),
            ],
            CREATIVE_DEDUP_TIMEOUT,
            history_env,
        ),
        ("写入去重后的创意数据", [PYTHON, str(CREATIVE_DATA_SCRIPT)], DOWNLOAD_TIMEOUT, history_env),
    ]
    try:
        for label, command, timeout, env in steps:
            result = subprocess.run(
                command,
                cwd=SCRIPT_DIR,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            log(f"  创意步骤 {label} 退出码: {result.returncode}")
            if result.stdout:
                for line in result.stdout.strip().split("\n")[-15:]:
                    log(f"    [creative stdout] {line}")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-8:]:
                    log(f"    [creative stderr] {line}")
            if result.returncode != 0:
                return False
        return True
    except subprocess.TimeoutExpired as exc:
        log(f"[ERROR] 创意素材看板步骤超时: {exc.cmd}")
        return False
    except Exception as exc:
        log(f"[ERROR] 创意素材看板更新失败: {exc}")
        return False


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
            timeout=DEPLOY_TIMEOUT,
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


def run_once() -> bool:
    report_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    download_ok = False
    for attempt in range(1, max(1, DOWNLOAD_ATTEMPTS) + 1):
        download_ok = run_download(attempt, report_date=report_date)
        if download_ok:
            break
        if attempt < DOWNLOAD_ATTEMPTS:
            log(f"下载或写入大表失败，{DOWNLOAD_RETRY_DELAY} 秒后重试。")
            time.sleep(max(0, DOWNLOAD_RETRY_DELAY))

    if not download_ok:
        log("下载或写入大表失败，已达到最大重试次数，跳过部署。")
        return False

    # 万相台的成交及订单会在归因窗口内持续回补。默认回刷最近 3 天，
    # 覆盖常见的 T+2 归因延迟，同时避免逐日重写大表导致日常任务过长。
    # 需要更长的历史核验时可显式设置 WORKBUDDY_RECONCILE_DAYS。
    reconcile_days = max(1, int(os.environ.get("WORKBUDDY_RECONCILE_DAYS", "3")))
    if reconcile_days > 1:
        log(f"[步骤1.5] 回补核验最近 {reconcile_days} 天的延迟归因数据...")
        for offset in range(2, reconcile_days + 1):
            historical_date = (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
            if not run_download(1, report_date=historical_date, force_download=True):
                log(f"[WARN] 历史回补失败: {historical_date}；下次任务会继续核验。")

    if not run_creative_pipeline():
        log("[WARN] 创意素材看板更新未完成，将继续发布商品看板与当前可用的创意数据。")

    deploy_ok = run_deploy()
    if not deploy_ok:
        log("部署失败。")
        return False
    return True


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "once"
    log("=== 万相台报表每日下载服务启动 ===")
    log(f"运行模式: {mode}")
    log(f"脚本目录: {SCRIPT_DIR}")

    lock_handle = acquire_lock()
    if lock_handle is None:
        sys.exit(1)

    try:
        if mode == "once":
            ok = run_once()
            log("单次任务完成，退出。")
            sys.exit(0 if ok else 1)

        if mode != "loop":
            log(f"未知运行模式: {mode}，可用模式: once | loop")
            sys.exit(1)

        log("进入常驻循环模式，下次运行时间将显示在日志中")
        while True:
            seconds, target = seconds_until_next_run()
            log(f"下次运行时间: {target.strftime('%Y-%m-%d %H:%M:%S')} (约{int(seconds/60)}分钟后)")
            time.sleep(max(0, seconds))
            run_once()
    finally:
        if hasattr(lock_handle, "close"):
            lock_handle.close()


if __name__ == "__main__":
    main()
