#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每天上午9点自动运行万相台报表下载
使用方法：
  python3 run_daily.py &
  或设置系统cron：
  0 9 * * * cd /full/path && python3 wanxiangtai_download.py download >> /tmp/alimama_cron.log 2>&1
"""

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
    log("开始运行下载任务...")
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


def run_deploy():
    """生成静态站点并推送到 GitHub，触发 GitHub Pages 部署"""
    if not AUTO_DEPLOY:
        log("AUTO_DEPLOY 未开启，跳过线上部署。需要自动部署时使用: AUTO_DEPLOY=1 python3 automation/run_daily.py")
        return

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
    except Exception as e:
        log(f"运行部署脚本失败: {e}")


def seconds_until_next_9am():
    """计算距离明天上午9点还有多少秒"""
    now = datetime.now()
    # 今天的9点
    today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    # 如果现在还没到今天9点，就今天9点运行
    if now < today_9am:
        target = today_9am
    else:
        # 否则明天9点运行
        target = today_9am + timedelta(days=1)
    seconds = (target - now).total_seconds()
    return seconds, target


def main():
    log("=== 万相台报表每日下载服务启动 ===")
    log(f"脚本目录: {SCRIPT_DIR}")
    log(f"下次运行时间将显示在日志中")

    # 先运行一次
    if run_download():
        run_deploy()

    # 然后每天9点运行
    while True:
        seconds, target = seconds_until_next_9am()
        log(f"下次运行时间: {target.strftime('%Y-%m-%d %H:%M:%S')} (约{int(seconds/60)}分钟后)")
        time.sleep(seconds)
        if run_download():
            run_deploy()


if __name__ == "__main__":
    main()
