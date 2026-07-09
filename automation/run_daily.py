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
DEPLOY_SCRIPT = SCRIPT_DIR / "deploy_static.py"
LOG_FILE = DAILY_LOG_FILE
RUN_HOUR = 7
RUN_MINUTE = 30
DOWNLOAD_TIMEOUT = int(os.environ.get("WORKBUDDY_DOWNLOAD_TIMEOUT", "1200"))
DEPLOY_TIMEOUT = int(os.environ.get("WORKBUDDY_DEPLOY_TIMEOUT", "600"))


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


def run_download():
    """运行下载脚本"""
    log("[步骤1] 开始下载并更新大表")
    try:
        result = subprocess.run(
            [PYTHON, str(DOWNLOAD_SCRIPT), "download"],
            cwd=SCRIPT_DIR,
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
    download_ok = run_download()
    if not download_ok:
        log("下载或写入大表失败，跳过部署。")
        return False

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
