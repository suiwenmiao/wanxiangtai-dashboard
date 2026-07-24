#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build and optionally publish the Vue dashboard to GitHub Pages."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config import AUTOMATION_DIR, FRONTEND_DIR, PROJECT_DIR, SITE_DIR


BUILD_META = SITE_DIR / "build-meta.json"
DEPENDENCIES_DIR = Path("/Users/suiwenmiao/.cache/codex-runtimes/codex-primary-runtime/dependencies")


def run(
    cmd: list[str],
    *,
    cwd: Path = PROJECT_DIR,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    result = subprocess.run(cmd, cwd=cwd, env=run_env, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def generate_data() -> None:
    print("[1/3] 生成前端数据 JSON...")
    run([sys.executable, str(AUTOMATION_DIR / "generate_dashboard_data.py")])


def encrypt_creative_data() -> None:
    print("[2/4] 加密创意看板数据...")
    node = shutil.which("node") or "/opt/homebrew/bin/node"
    if not Path(node).exists():
        raise SystemExit("[ERROR] 未找到 node，无法加密创意看板数据。")
    run([node, str(AUTOMATION_DIR / "encrypt_creative_data.mjs")])


def resolve_pnpm_command() -> list[str]:
    configured = os.environ.get("PNPM_BIN")
    if configured:
        pnpm_path = Path(configured).expanduser()
        if pnpm_path.suffix == ".mjs":
            node = shutil.which("node") or "/opt/homebrew/bin/node"
            return [node, str(pnpm_path)]
        return [str(pnpm_path)]

    found = shutil.which("pnpm")
    if found:
        return [found]

    fallback_bins = [
        DEPENDENCIES_DIR / "bin" / "fallback" / "pnpm",
        DEPENDENCIES_DIR / "bin" / "pnpm",
    ]
    for pnpm_path in fallback_bins:
        if pnpm_path.exists():
            return [str(pnpm_path)]

    pnpm_mjs = DEPENDENCIES_DIR / "node" / "node_modules" / "pnpm" / "bin" / "pnpm.mjs"
    node_candidates = [
        shutil.which("node"),
        "/opt/homebrew/bin/node",
        str(DEPENDENCIES_DIR / "node" / "bin" / "node"),
    ]
    for node in node_candidates:
        if node and Path(node).exists() and pnpm_mjs.exists():
            return [node, str(pnpm_mjs)]

    raise SystemExit("[ERROR] 未找到 pnpm。请安装 pnpm，或设置 PNPM_BIN 指向 pnpm 可执行文件。")


def build_frontend() -> None:
    print("[3/4] 构建 Vue 前端到 site/ ...")
    vite = FRONTEND_DIR / "node_modules" / ".bin" / "vite"
    if vite.exists():
        # LaunchAgent may resolve a different pnpm version than the one which
        # installed node_modules. The local Vite binary is version-stable.
        run([str(vite), "build"], cwd=FRONTEND_DIR, env={"CI": "true"})
    else:
        pnpm = resolve_pnpm_command()
        print("未检测到 frontend/node_modules，先执行 pnpm install...")
        run([*pnpm, "install"], cwd=FRONTEND_DIR, env={"CI": "true"})
        run([*pnpm, "build"], cwd=FRONTEND_DIR, env={"CI": "true"})

    index_file = SITE_DIR / "index.html"
    if not index_file.exists():
        raise SystemExit(f"[ERROR] 前端构建失败，未找到: {index_file}")
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")

    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "frontend",
        "entry": "index.html",
    }
    BUILD_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成: {index_file}")


def ensure_git_repo() -> None:
    result = run(["git", "rev-parse", "--is-inside-work-tree"], check=False)
    if result.returncode != 0:
        raise SystemExit("[ERROR] 当前目录还不是 Git 仓库。请先运行: git init && git remote add origin <你的仓库地址>")


def commit_site(message: str) -> bool:
    print("[4/4] 提交 site/ 发布产物...")
    ensure_git_repo()
    run(["git", "add", "site"])
    # The project ignores raw data/ downloads, but the static site's JSON must publish.
    site_data = SITE_DIR / "data"
    if site_data.exists():
        run(["git", "add", "-f", str(site_data)])
    diff = run(["git", "diff", "--cached", "--quiet"], check=False)
    if diff.returncode == 0:
        print("site/ 没有变化，无需提交。")
        return False

    run(["git", "commit", "-m", message])
    return True


def push_site() -> None:
    ensure_git_repo()
    remote = run(["git", "remote"], check=False)
    remotes = {line.strip() for line in remote.stdout.splitlines() if line.strip()}
    if "origin" not in remotes:
        raise SystemExit("[ERROR] 未配置 origin 远程仓库，请先运行: git remote add origin <你的仓库地址>")

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False).stdout.strip()
    if not branch or branch == "HEAD":
        raise SystemExit("[ERROR] 当前不在普通分支上，无法自动 push。")

    print(f"推送到 origin/{branch}，GitHub Pages 会在 push 后自动部署...")
    run(["git", "push", "origin", branch])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and deploy the Wanxiangtai Vue dashboard.")
    parser.add_argument("--skip-data", action="store_true", help="跳过生成 dashboard-data.json")
    parser.add_argument("--skip-build", action="store_true", help="跳过前端构建")
    parser.add_argument("--commit", action="store_true", help="提交 site/ 产物到 Git")
    parser.add_argument("--push", action="store_true", help="提交后推送到 origin 当前分支")
    parser.add_argument(
        "--message",
        default=f"chore: update dashboard {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        help="Git commit message",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.skip_data:
        generate_data()
    encrypt_creative_data()
    if not args.skip_build:
        build_frontend()
    else:
        print("[2/3] 已跳过前端构建。")

    committed = False
    if args.commit or args.push:
        committed = commit_site(args.message)
    else:
        print("[3/3] 已跳过 Git 提交。需要发布时运行: python3 automation/deploy_static.py --commit --push")

    if args.push:
        if committed:
            push_site()
        else:
            print("没有新提交，跳过 push。")

    print("完成。")


if __name__ == "__main__":
    main()
