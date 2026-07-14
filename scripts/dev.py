#!/usr/bin/env python3
"""Cross-platform developer task runner.

Use this instead of shell-specific Makefile targets when switching between
Windows and macOS:

    python scripts/dev.py setup
    python scripts/dev.py check
    python scripts/dev.py daily-once
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
AUTOMATION_DIR = PROJECT_DIR / "automation"
PYTHON = sys.executable


def node_bin_dir() -> str | None:
    cmd = shutil.which("node") or shutil.which("node.exe")
    if cmd:
        return str(Path(cmd).resolve().parent)

    candidates = [
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "node"
        / "bin",
    ]
    for candidate in candidates:
        if (candidate / "node.exe").exists() or (candidate / "node").exists():
            return str(candidate)
    return None


def pnpm_cmd() -> str:
    cmd = shutil.which("pnpm") or shutil.which("pnpm.cmd")
    if not cmd:
        raise SystemExit(
            "[ERROR] pnpm was not found. Install it with Node/Corepack, then run setup again."
        )
    return cmd


def run(
    cmd: list[str],
    *,
    cwd: Path = PROJECT_DIR,
    env: dict[str, str] | None = None,
) -> None:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    node_dir = node_bin_dir()
    if node_dir:
        run_env["PATH"] = node_dir + os.pathsep + run_env.get("PATH", "")
    print(f"$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, env=run_env, check=True)


def setup(_: argparse.Namespace) -> None:
    run([PYTHON, "-m", "pip", "install", "-r", "requirements.txt"])
    run([PYTHON, "-m", "playwright", "install", "chromium"])
    run([pnpm_cmd(), "install"], cwd=FRONTEND_DIR)


def check(_: argparse.Namespace) -> None:
    run([PYTHON, "scripts/check_syntax.py"])
    run([pnpm_cmd(), "build"], cwd=FRONTEND_DIR, env={"CI": "true", "CHECK_BUILD": "1"})


def login(_: argparse.Namespace) -> None:
    run([PYTHON, "automation/wanxiangtai_download.py", "login"])


def download(_: argparse.Namespace) -> None:
    run([PYTHON, "automation/wanxiangtai_download.py", "download"])


def data(_: argparse.Namespace) -> None:
    run([PYTHON, "automation/generate_dashboard_data.py"])


def dev(_: argparse.Namespace) -> None:
    data(_)
    run([pnpm_cmd(), "dev"], cwd=FRONTEND_DIR)


def build(_: argparse.Namespace) -> None:
    data(_)
    run([pnpm_cmd(), "build"], cwd=FRONTEND_DIR, env={"CI": "true"})


def package(_: argparse.Namespace) -> None:
    run([PYTHON, "automation/deploy_static.py"])


def deploy(_: argparse.Namespace) -> None:
    run([PYTHON, "automation/deploy_static.py", "--commit", "--push"])


def daily_once(_: argparse.Namespace) -> None:
    run([PYTHON, "automation/run_daily.py", "once"], env={"AUTO_DEPLOY": "1"})


def daily_loop(_: argparse.Namespace) -> None:
    run([PYTHON, "automation/run_daily.py", "loop"], env={"AUTO_DEPLOY": "1"})


def preview(_: argparse.Namespace) -> None:
    run([pnpm_cmd(), "preview"], cwd=FRONTEND_DIR, env={"CI": "true"})


def clean(_: argparse.Namespace) -> None:
    run([PYTHON, "scripts/clean_project.py"])


TASKS = {
    "setup": setup,
    "check": check,
    "login": login,
    "download": download,
    "data": data,
    "dev": dev,
    "build": build,
    "package": package,
    "deploy": deploy,
    "daily-once": daily_once,
    "daily-loop": daily_loop,
    "preview": preview,
    "clean": clean,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run project tasks on Windows or macOS.")
    parser.add_argument("task", choices=sorted(TASKS))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    TASKS[args.task](args)


if __name__ == "__main__":
    main()
