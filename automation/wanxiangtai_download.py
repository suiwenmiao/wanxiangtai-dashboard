#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万相台商品报表自动下载脚本（完整版）

功能：
  - 首次扫码登录并保存登录态（cookie）
  - 自动下载包含前一天数据的商品/计划报表到本地报表目录
  - 写入大表前只保留前一天数据，避免多日报表误覆盖历史数据
  - 支持断点续传：文件已存在则跳过
  - 支持登录态过期检测

完整下载流程（异步任务模式）：
  1. 访问商品报表页（item_promotion）
  2. 切换到计划/场景明细维度
  3. 点击"下载报表"按钮并记录弹窗里的精确任务名
  4. 点击"确定"创建下载任务
  5. 跳转到下载任务管理页
  6. 轮询等待任务"生成成功"
  7. 点击任务的"下载"按钮，下载文件
  8. 移动文件到报表目录并重命名

用法：
  python wanxiangtai_download.py login      # 首次扫码登录
  python wanxiangtai_download.py download   # 下载前一天商品报表
  python wanxiangtai_download.py            # 默认执行 download
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from config import (
    BASE_TABLE_PATH,
    BIG_TABLE_PATH,
    DOWNLOAD_DIR,
    DOWNLOAD_LOG_FILE,
    REPORT_DIR,
    SCREENSHOT_DIR,
    SHEET_NAME,
    STATE_FILE,
)

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("[ERROR] 未安装 playwright，请先安装")
    sys.exit(1)

# ======================== 路径配置 ========================
REPORT_DIR_PRIMARY = REPORT_DIR  # 不再使用 Documents，避免沙盒拦截
LOG_FILE = DOWNLOAD_LOG_FILE

# ======================== URL 配置 ========================
HOME_URL = "https://one.alimama.com/"
ITEM_REPORT_URL = "https://one.alimama.com/index.html#!/report/item_promotion?rptType=item_promotion"
DOWNLOAD_LIST_URL = "https://one.alimama.com/index.html#!/report/download-list"

# 关键文本
BTN_DOWNLOAD_REPORT = "下载报表"
BTN_CONFIRM = "确定"
REQUIRED_DETAIL_COLUMNS = ["日期", "主体ID", "场景名字", "计划ID", "计划名字"]


def log(msg):
    """打印并记录日志"""
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()  # 强制刷盘，确保日志实时写入
    except Exception:
        pass


def acquire_lock(lock_path: Path):
    """Prevent overlapping download jobs from corrupting local files."""
    try:
        import fcntl

        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(lock_path, "w", encoding="utf-8")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            log(f"[ERROR] 已有下载任务在运行，跳过本次执行: {lock_path}")
            return None
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(f"{os.getpid()}\n")
        lock_file.flush()
        return lock_file
    except Exception as e:
        log(f"[WARN] 获取下载锁失败，将继续执行: {e}")
        return True


def get_report_date():
    """获取报表日期（昨天）"""
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


async def get_dialog_task_name(page) -> str | None:
    """Read the exact task/file name from the download dialog before confirm."""
    try:
        task_name = await page.evaluate(
            """
() => {
    const roots = Array.from(document.querySelectorAll('.ant-modal, [role="dialog"], body')).reverse();
    for (const root of roots) {
        const text = root.textContent || '';
        if (!text.includes('下载报表') && root.tagName !== 'BODY') continue;
        const inputs = Array.from(root.querySelectorAll('input'));
        for (const input of inputs) {
            const value = (input.value || input.getAttribute('value') || '').trim();
            const match = value.match(/[\\u4e00-\\u9fffA-Za-z]*报表_\\d{8}_\\d{6}/);
            if (match) return match[0];
        }
        const match = text.match(/[\\u4e00-\\u9fffA-Za-z]*报表_\\d{8}_\\d{6}/);
        if (match) return match[0];
    }
    return null;
}
"""
        )
        return task_name.strip() if task_name else None
    except Exception as e:
        log(f"[WARN] 读取弹窗任务名失败: {e}")
        return None


async def task_snapshot(page) -> list[str]:
    """Return a short task-list snapshot for diagnostics."""
    try:
        rows = await page.evaluate(
            """
() => Array.from(document.querySelectorAll('tr'))
    .map(row => (row.textContent || '').replace(/\\s+/g, ' ').trim())
    .filter(text => text.includes('报表_'))
    .slice(0, 8)
"""
        )
        return rows or []
    except Exception:
        return []


def big_table_has_date(report_date: str) -> bool:
    """Return whether the accumulated workbook already contains report_date."""
    try:
        import pandas as pd

        if not BIG_TABLE_PATH.exists():
            return False
        df_dates = pd.read_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME, usecols=["日期"])
        dates = pd.to_datetime(df_dates["日期"], errors="coerce").dt.strftime("%Y-%m-%d")
        return bool((dates == report_date).any())
    except Exception as e:
        log(f"[WARN] 检查大表日期失败: {e}")
        return False


def is_login_page(url, title=""):
    """判断当前是否在登录页"""
    u = url.lower()
    t = title.lower()
    if "login.taobao" in u or "login.tmall" in u:
        return True
    if "login" in u and ("alimama" not in u and "1bp.taobao" not in u):
        return True
    if "login" in t and "alimama" not in t and "万相台" not in t:
        return True
    return False


def is_logged_in(url, title=""):
    """判断是否已登录"""
    u = url.lower()
    if is_login_page(url, title):
        return False
    if ("alimama" in u or "1bp.taobao" in u) and "login" not in u:
        return True
    return False


async def close_modal(page):
    """尝试关闭页面弹窗"""
    for sel in ['.ant-modal-close', '[class*="close-icon"]', '[class*="modal-close"]',
                'button[aria-label="Close"]', '[class*="close"]']:
        try:
            btns = await page.query_selector_all(sel)
            for b in btns:
                try:
                    if await b.is_visible(timeout=1500):
                        await b.click(timeout=2000, force=True)
                        await asyncio.sleep(1)
                except Exception:
                    pass
        except Exception:
            pass


# ======================== 模式：login ========================
async def do_login():
    """首次扫码登录，自动检测登录成功后保存登录态"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome", args=["--start-maximized"])
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        log("正在打开万相台登录页...")
        try:
            await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            log(f"导航失败: {e}")

        log("请在弹出的浏览器窗口中扫码登录万相台")
        log("脚本将自动检测登录状态，登录成功后自动保存...")

        # 轮询检测登录成功（最多等待10分钟）
        logged_in = False
        wait_seconds = 600
        check_interval = 2
        for i in range(wait_seconds // check_interval):
            await asyncio.sleep(check_interval)
            try:
                url = page.url
                title = await page.title()
                if is_logged_in(url, title):
                    log(f"检测到登录成功！URL: {url}")
                    logged_in = True
                    break
            except Exception:
                pass
            elapsed = (i + 1) * check_interval
            if elapsed % 30 == 0:
                log(f"等待扫码登录中... 已等待 {elapsed} 秒")

        if not logged_in:
            log("[ERROR] 登录超时（10分钟），请重新运行 login 模式")
            await browser.close()
            return

        await asyncio.sleep(5)
        await context.storage_state(path=str(STATE_FILE))
        log(f"登录态已保存到: {STATE_FILE}")
        log(f"下一步: 运行 download 模式下载报表")
        await browser.close()


# ======================== 模式：download ========================
async def do_download():
    """下载报表并把目标日期数据写入大表（异步任务流程）"""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # 使用报表目录（已直接设置为可写路径）
    REPORT_DIR = REPORT_DIR_PRIMARY
    log(f"使用报表目录: {REPORT_DIR}")

    report_date = get_report_date()
    # 万相台下载的文件是 .zip，里面是 .xlsx
    desktop_filename = f"万相台商品报表_{report_date}.zip"
    desktop_path = REPORT_DIR / desktop_filename
    csv_path = REPORT_DIR / f"万相台商品报表_{report_date}.csv"
    force_download = os.environ.get("FORCE_DOWNLOAD", "0") == "1"

    if desktop_path.exists() and not force_download:
        if csv_path.exists():
            log(f"目标文件已存在，重新校验并写入目标日期数据: {csv_path}")
            return append_to_big_table(str(csv_path), report_date)
        if big_table_has_date(report_date):
            log(f"目标ZIP已存在且大表已包含 {report_date}: {desktop_filename}，跳过下载")
            return True
        log(f"目标文件已存在，但大表尚未包含 {report_date}，删除后重新下载: {desktop_filename}")
        try:
            desktop_path.unlink()
            for stale in REPORT_DIR.glob(f"万相台商品报表_{report_date}.*"):
                if stale.exists():
                    stale.unlink()
        except Exception as e:
            log(f"[WARN] 清理旧报表文件失败: {e}")
    elif force_download and desktop_path.exists():
        log(f"FORCE_DOWNLOAD=1，清理已有报表后重新下载: {desktop_filename}")
        try:
            for stale in REPORT_DIR.glob(f"万相台商品报表_{report_date}.*"):
                if stale.exists():
                    stale.unlink()
        except Exception as e:
            log(f"[WARN] 清理旧报表文件失败: {e}")

    if not STATE_FILE.exists():
        log("[ERROR] 未找到登录态，请先运行 login 模式扫码登录")
        return False

    headed = os.environ.get("HEADED", "0") == "1"
    log(f"报表日期: {report_date}")
    log(f"目标文件: {desktop_path}")
    log(f"浏览器模式: {'有头' if headed else '无头'}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not headed, channel="chrome", args=["--start-maximized"]
        )
        context = await browser.new_context(
            storage_state=str(STATE_FILE),
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = await context.new_page()

        try:
            # ========== 步骤1: 进入商品报表页 ==========
            log(f"\n[步骤1] 访问商品报表页: {ITEM_REPORT_URL}")
            await page.goto(ITEM_REPORT_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(10)
            await close_modal(page)

            url = page.url
            title = await page.title()
            if not is_logged_in(url, title):
                log("[ERROR] 登录态已过期！请重新运行 login 模式扫码登录")
                await page.screenshot(path=str(SCREENSHOT_DIR / "login_expired.png"))
                await browser.close()
                return False
            log(f"已登录 | URL: {url} | 标题: {title}")

            await page.screenshot(path=str(SCREENSHOT_DIR / "01_item_report.png"))

            # ========== 步骤2: 日期范围 ==========
            # 万相台常把下载弹窗默认为最近多日；写入大表前会强制过滤为 report_date。
            log(f"\n[步骤2] 下载日期以页面默认范围创建，写入大表时只保留 {report_date}")

            # ========== 步骤3: 切换报表维度为"按计划/场景" ==========
            log(f"\n[步骤3] 切换报表维度确保含场景/计划明细列...")
            for dim_name in ["按计划", "按场景", "计划", "场景"]:
                try:
                    dim_btn = page.get_by_text(dim_name, exact=False).first
                    if await dim_btn.is_visible(timeout=2000):
                        await dim_btn.click(timeout=3000)
                        log(f"已选中维度 [{dim_name}]，导出应包含 场景ID/场景名字/计划ID/计划名字")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
            else:
                log("[WARN] 未找到维度选择项，导出可能缺场景/计划列，请检查")

            # ========== 步骤4: 点击"下载报表"按钮 ==========
            log(f"\n[步骤4] 点击'下载报表'按钮...")
            download_btn = page.get_by_text(BTN_DOWNLOAD_REPORT, exact=True).first
            try:
                await download_btn.scroll_into_view_if_needed(timeout=5000)
                log(f"按钮位置: {await download_btn.bounding_box()}")
                await download_btn.click(timeout=5000)
                log("已点击'下载报表'")
            except Exception as e:
                log(f"点击失败: {e}")
                # 备用方案：通过 role 查找
                try:
                    await page.get_by_role("button", name=BTN_DOWNLOAD_REPORT).first.click(timeout=5000)
                    log("已点击(通过 role)")
                except Exception as e2:
                    log(f"[ERROR] 无法找到'下载报表'按钮: {e2}")
                    await page.screenshot(path=str(SCREENSHOT_DIR / "no_download_btn.png"))
                    await browser.close()
                    return False

            await asyncio.sleep(5)
            await page.screenshot(path=str(SCREENSHOT_DIR / "02_dialog.png"))
            target_task_name = await get_dialog_task_name(page)
            if target_task_name:
                log(f"目标任务名: {target_task_name}")
            else:
                log("[WARN] 未能从弹窗读取精确任务名，将使用当天报表前缀兜底")

            # ========== 步骤5: 在弹窗中点击"确定" ==========
            log(f"\n[步骤5] 在弹窗中点击'确定'...")
            confirm_clicked = False
            for sel_text in [BTN_CONFIRM, "确认", "提交", "开始下载"]:
                try:
                    btn = page.get_by_role("button", name=sel_text).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click(timeout=5000)
                        log(f"已点击按钮(role): {sel_text}")
                        confirm_clicked = True
                        break
                except Exception:
                    try:
                        btn = page.get_by_text(sel_text, exact=True).first
                        if await btn.is_visible(timeout=2000):
                            await btn.click(timeout=5000)
                            log(f"已点击按钮(文本): {sel_text}")
                            confirm_clicked = True
                            break
                    except Exception:
                        continue

            if not confirm_clicked:
                log("[ERROR] 未找到'确定'按钮")
                await page.screenshot(path=str(SCREENSHOT_DIR / "no_confirm_btn.png"))
                await browser.close()
                return False

            await asyncio.sleep(3)
            log("步骤4完成，准备截图...")
            await page.screenshot(path=str(SCREENSHOT_DIR / "03_after_confirm.png"))
            log("任务已提交（截图完成）")

            # 记录刚创建的任务标识（万相台任务名格式：商品报表_YYYYMMDD_HHMMSS）
            # 注意：任务名中的日期是创建日期（今天），不是报表日期。
            # 优先使用弹窗里的精确任务名，避免误下载列表里的旧任务。
            today_str = datetime.now().strftime("%Y%m%d")
            fallback_prefixes = [f"计划报表_{today_str}", f"商品报表_{today_str}", f"人群报表_{today_str}"]
            log(f"兜底任务名前缀: {fallback_prefixes}")

            # ========== 步骤5: 跳转到下载任务管理页 ==========
            log(f"\n[步骤5] 跳转到下载任务管理页...")
            try:
                # 方式1: 点击左侧"下载任务管理"链接
                dl_link = page.get_by_text("下载任务管理", exact=True).first
                if await dl_link.is_visible(timeout=3000):
                    await dl_link.click(timeout=5000)
                    log("通过菜单跳转")
            except Exception:
                pass

            try:
                # 方式2: 直接导航
                if "download-list" not in page.url:
                    await page.goto(DOWNLOAD_LIST_URL, wait_until="domcontentloaded", timeout=60000)
                    log("通过URL跳转")
            except Exception as e:
                log(f"跳转失败: {e}")

            await asyncio.sleep(8)
            await close_modal(page)
            log(f"当前URL: {page.url}")
            await page.screenshot(path=str(SCREENSHOT_DIR / "04_dl_list.png"))

            # ========== 步骤6: 等待目标任务"生成成功" ==========
            # 任务名包含当天日期（创建日期），格式通常为 商品报表_YYYYMMDD_HHMMSS。
            # 只检查目标任务行，避免误判旧任务已生成成功。
            log(f"\n[步骤6] 等待任务生成（最多5分钟）...")
            task_ready = False
            max_wait = 300  # 5分钟
            check_interval = 5
            for i in range(max_wait // check_interval):
                try:
                    status_result = await page.evaluate("""
(args) => {
    const exactName = args.exactName;
    const prefixes = args.prefixes || [];
    const rows = Array.from(document.querySelectorAll('tr'));
    for (const row of rows) {
        const txt = row.textContent || '';
        const compact = txt.replace(/\\s+/g, ' ').trim();
        let matched = exactName ? compact.includes(exactName) : false;
        if (!matched) {
            for (const p of prefixes) { if (compact.includes(p)) { matched = true; break; } }
        }
        if (!matched) continue;
        if (compact.includes('生成成功')) return {status: 'success', text: compact.slice(0, 240)};
        if (compact.includes('生成失败')) return {status: 'failed', text: compact.slice(0, 240)};
        if (compact.includes('生成中') || compact.includes('排队中') || compact.includes('处理中')) {
            return {status: 'pending', text: compact.slice(0, 240)};
        }
        return {status: 'found', text: compact.slice(0, 240)};
    }
    return {status: 'not_found'};
}
""", {"exactName": target_task_name, "prefixes": fallback_prefixes if not target_task_name else []})
                    elapsed = (i + 1) * check_interval
                    status_text = status_result.get("status") if status_result else "unknown"
                    if status_text == "success":
                        log(f"任务已生成成功！耗时: {elapsed}秒 | {status_result.get('text', '')}")
                        task_ready = True
                        break
                    elif status_text == "failed":
                        log(f"[ERROR] 目标任务生成失败: {status_result.get('text', '')}")
                        await page.screenshot(path=str(SCREENSHOT_DIR / "task_failed.png"))
                        break
                    else:
                        if elapsed % 30 == 0:
                            log(f"目标任务状态: {status_text}，已等待 {elapsed}秒")
                except Exception as e:
                    log(f"检查状态失败: {e}")
                await asyncio.sleep(check_interval)
                # 每30秒刷新一次页面
                if (i + 1) % 6 == 0:
                    try:
                        await page.goto(DOWNLOAD_LIST_URL, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(5)
                    except Exception:
                        pass

            if not task_ready:
                log(f"[ERROR] 目标任务({target_task_name or fallback_prefixes[0]})生成超时或未找到")
                for row_text in await task_snapshot(page):
                    log(f"  [任务快照] {row_text}")
                await page.screenshot(path=str(SCREENSHOT_DIR / "task_timeout.png"))
                await browser.close()
                return False

            await page.screenshot(path=str(SCREENSHOT_DIR / "05_task_ready.png"))

            # ========== 步骤7: 点击刚创建任务的"下载"按钮 ==========
            download_task_key = target_task_name or fallback_prefixes[0]
            log(f"\n[步骤7] 点击目标任务({download_task_key})的'下载'按钮...")
            download_received = asyncio.Event()
            download_path_holder = [None]

            async def handle_download(d):
                try:
                    log(f"检测到下载: {d.suggested_filename}")
                    p_path = DOWNLOAD_DIR / d.suggested_filename
                    await d.save_as(str(p_path))
                    download_path_holder[0] = p_path
                    download_received.set()
                except Exception as e:
                    log(f"下载处理失败: {e}")

            page.on("download", lambda d: asyncio.create_task(handle_download(d)))

            # 通过 JS 找到包含目标任务名的行。下载按钮是 hover 行后才出现的浮动按钮，
            # 所以先把目标行滚动到视窗并移动鼠标到该行，再点击同一行高度上的"下载"按钮。
            # 使用 page.evaluate 传参，避免 f-string 嵌套大括号的转义问题
            js_find_target_row = """
(targetKey) => {
    const allRows = Array.from(document.querySelectorAll('tr'));
    for (const row of allRows) {
        const txt = (row.textContent || '').replace(/\\s+/g, ' ').trim();
        if (txt.includes(targetKey)) {
            row.scrollIntoView({block: 'center'});
            const rect = row.getBoundingClientRect();
            return {
                found: true,
                text: txt.slice(0, 200),
                x: rect.left + 50,
                y: rect.top + rect.height / 2,
                top: rect.top,
                bottom: rect.bottom
            };
        }
    }
    return {found: false};
}
"""
            js_select_target_row = """
(targetKey) => {
    const rows = Array.from(document.querySelectorAll('tr'));
    const row = rows.find(item => (item.textContent || '').replace(/\\s+/g, ' ').includes(targetKey));
    if (!row) return {selected: false, reason: 'row_not_found'};
    const checkbox = row.querySelector('input[type="checkbox"]') ||
        row.querySelector('[class*="checkbox"]') ||
        row.querySelector('[role="checkbox"]');
    if (!checkbox) return {selected: false, reason: 'checkbox_not_found'};
    checkbox.click();
    return {selected: true};
}
"""
            js_click_hover_download = """
(rowBounds) => {
    const candidates = Array.from(document.querySelectorAll('button, a, [role="button"]'))
        .filter(el => {
            const text = (el.textContent || '').trim();
            if (!(text === '下载' || text.startsWith('下载'))) return false;
            const rect = el.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return false;
            const midY = rect.top + rect.height / 2;
            return midY >= rowBounds.top - 4 && midY <= rowBounds.bottom + 64;
        });
    if (!candidates.length) {
        const visibleDownloads = Array.from(document.querySelectorAll('button, a, [role="button"]'))
            .map(el => {
                const text = (el.textContent || '').trim();
                const rect = el.getBoundingClientRect();
                return {text, x: rect.left, y: rect.top, width: rect.width, height: rect.height};
            })
            .filter(item => item.text.includes('下载') && item.width > 0 && item.height > 0);
        return {found: false, visibleDownloadCount: visibleDownloads.length, visibleDownloads};
    }
    candidates.sort((a, b) => {
        const ar = a.getBoundingClientRect();
        const br = b.getBoundingClientRect();
        return Math.abs((ar.top + ar.height / 2) - rowBounds.bottom) -
            Math.abs((br.top + br.height / 2) - rowBounds.bottom);
    });
    const btn = candidates[0];
    btn.scrollIntoView({block: 'center'});
    btn.click();
    return {found: true, text: (btn.textContent || '').trim()};
}
"""
            js_click_visible_download = """
() => {
    const candidates = Array.from(document.querySelectorAll('button, a, [role="button"]'))
        .filter(el => {
            const text = (el.textContent || '').trim();
            const rect = el.getBoundingClientRect();
            const disabled = el.disabled || el.getAttribute('aria-disabled') === 'true' ||
                (el.className || '').toString().includes('disabled');
            return text === '下载' && rect.width > 0 && rect.height > 0 && !disabled;
        });
    if (!candidates.length) return {found: false};
    candidates.sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top);
    const btn = candidates[0];
    btn.click();
    return {found: true, text: (btn.textContent || '').trim()};
}
"""
            download_btn_clicked = False
            try:
                target_row = await page.evaluate(js_find_target_row, download_task_key)
                log(f"目标行查找结果: {target_row}")
                if target_row and target_row.get("found"):
                    await page.mouse.move(float(target_row["x"]), float(target_row["y"]))
                    await asyncio.sleep(1)
                    result = await page.evaluate(js_click_hover_download, {
                        "top": target_row["top"],
                        "bottom": target_row["bottom"],
                    })
                    log(f"目标行下载按钮点击结果: {result}")
                else:
                    result = {"found": False}
                if result and result.get("found"):
                    download_btn_clicked = True
                    log("已点击目标任务的下载按钮")
                    await asyncio.sleep(3)
            except Exception as e:
                log(f"JS 点击失败: {e}")

            if not download_btn_clicked:
                try:
                    select_result = await page.evaluate(js_select_target_row, download_task_key)
                    log(f"目标行勾选结果: {select_result}")
                    await asyncio.sleep(1)
                    result = await page.evaluate(js_click_visible_download)
                    log(f"可见下载按钮点击结果: {result}")
                    if result and result.get("found"):
                        download_btn_clicked = True
                        await asyncio.sleep(3)
                except Exception as e:
                    log(f"兜底下载点击失败: {e}")

            if not download_btn_clicked:
                log("[ERROR] 未找到刚创建任务的下载按钮")
                for row_text in await task_snapshot(page):
                    log(f"  [任务快照] {row_text}")
                await page.screenshot(path=str(SCREENSHOT_DIR / "no_dl_btn.png"))
                await browser.close()
                return False

            # ========== 步骤8: 等待文件下载 ==========
            log(f"\n[步骤8] 等待文件下载...")
            try:
                await asyncio.wait_for(download_received.wait(), timeout=60)
                log(f"下载完成: {download_path_holder[0]}")

                # 移动到目标目录并重命名
                if download_path_holder[0].exists():
                    src = download_path_holder[0]
                    # 用流式读写代替 shutil.move，兼容跨设备/沙盒限制
                    with open(src, "rb") as fin, open(desktop_path, "wb") as fout:
                        while True:
                            chunk = fin.read(64 * 1024)
                            if not chunk:
                                break
                            fout.write(chunk)
                    os.remove(src)
                    log(f"=== 成功！文件已保存到: {desktop_path} ===")
                    log(f"文件大小: {desktop_path.stat().st_size} bytes")

                    # 自动解压：如果下载的是.zip，提取里面的.csv/.xlsx
                    if desktop_path.suffix.lower() == ".zip":
                        try:
                            import zipfile
                            with zipfile.ZipFile(desktop_path) as zf:
                                for name in zf.namelist():
                                    if name.endswith(('.csv', '.xlsx', '.xls')):
                                        extract_path = REPORT_DIR / Path(name).name
                                        with zf.open(name) as source, open(extract_path, "wb") as target:
                                            while True:
                                                chunk = source.read(64 * 1024)
                                                if not chunk:
                                                    break
                                                target.write(chunk)
                                        # 重命名为带日期的版本
                                        final_name = f"万相台商品报表_{report_date}{Path(name).suffix}"
                                        final_path = REPORT_DIR / final_name
                                        if extract_path.exists():
                                            if final_path.exists():
                                                final_path.unlink()
                                            extract_path.replace(final_path)
                                            log(f"已解压: {final_path}")
                        except Exception as unzip_e:
                            log(f"自动解压失败（不影响主文件）: {unzip_e}")

                    # 步骤9: 追加到万相台数据大表 + 匹配品类
                    # 找到解压后的CSV文件
                    csv_to_append = None
                    if desktop_path.suffix.lower() == ".zip":
                        csv_name = f"万相台商品报表_{report_date}.csv"
                        csv_candidate = REPORT_DIR / csv_name
                        if csv_candidate.exists():
                            csv_to_append = csv_candidate
                    elif desktop_path.suffix.lower() == ".csv":
                        csv_to_append = desktop_path

                    if csv_to_append:
                        if not append_to_big_table(str(csv_to_append), report_date):
                            raise RuntimeError("追加数据到大表失败，已停止后续流程")
                    else:
                        log("[WARN] 未找到解压后的CSV文件，跳过大表追加")
                        raise RuntimeError("未找到解压后的CSV文件，已停止后续流程")
            except asyncio.TimeoutError:
                log("[ERROR] 下载超时")
                await page.screenshot(path=str(SCREENSHOT_DIR / "dl_timeout.png"))
                return False

        except Exception as e:
            log(f"下载失败: {e}")
            try:
                await page.screenshot(path=str(SCREENSHOT_DIR / "error.png"))
            except Exception:
                pass
            raise
        finally:
            await browser.close()

    return True


# ======================== 追加到大表 + 匹配品类 ========================
def read_report_csv(csv_path):
    """Read Wanxiangtai CSV with the encodings commonly used by exports."""
    import pandas as pd

    attempts = []
    for encoding in ["utf-8-sig", "utf-8", "gb18030", "gbk"]:
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
        except Exception as e:
            attempts.append(f"{encoding}: {e}")
            continue

        missing = [col for col in REQUIRED_DETAIL_COLUMNS if col not in df.columns]
        if not missing:
            return df, encoding
        attempts.append(f"{encoding}: 缺少字段 {', '.join(missing)}")

    raise RuntimeError("无法读取包含关键字段的CSV文件；" + "；".join(attempts[-4:]))


def append_to_big_table(csv_path, report_date_str):
    """将下载的报表CSV追加到万相台数据大表，并匹配品类/细类"""
    try:
        import pandas as pd
    except ImportError:
        log("[WARN] 未安装 pandas，跳过大表追加")
        return False

    log(f"\n[步骤9] 追加数据到万相台数据大表...")

    # 1. 读取新下载的CSV（万相台CSV是GBK编码）
    try:
        df_new, encoding = read_report_csv(csv_path)
        log(f"CSV编码: {encoding}")
    except Exception as e:
        log(f"[ERROR] 读取CSV失败: {e}")
        return False

    log(f"新数据: {len(df_new)} 行, {len(df_new.columns)} 列")

    missing_detail_cols = [col for col in REQUIRED_DETAIL_COLUMNS if col not in df_new.columns]
    if missing_detail_cols:
        log(f"[ERROR] CSV 缺少关键明细字段: {', '.join(missing_detail_cols)}，跳过大表追加")
        return False
    if df_new["场景名字"].isna().all() or (df_new["场景名字"].astype(str).str.strip() == "").all():
        log("[ERROR] 场景名字列全部为空，报表维度不正确，跳过大表追加")
        return False

    df_new["日期"] = pd.to_datetime(df_new["日期"], errors="coerce").dt.strftime("%Y-%m-%d")
    csv_dates = sorted(d for d in df_new["日期"].dropna().unique().tolist())
    if report_date_str not in csv_dates:
        max_date = csv_dates[-1] if csv_dates else "无有效日期"
        log(
            f"[ERROR] 下载报表未包含目标日期 {report_date_str}，"
            f"当前报表最大日期为 {max_date}，跳过大表追加和前端更新"
        )
        return False
    log(f"报表包含日期: {', '.join(csv_dates)}")

    if csv_dates != [report_date_str]:
        before_filter = len(df_new)
        df_new = df_new[df_new["日期"] == report_date_str].copy()
        log(
            f"[WARN] 下载文件包含多日数据，已只保留目标日期 {report_date_str}: "
            f"{before_filter} → {len(df_new)} 行"
        )
    if df_new.empty:
        log(f"[ERROR] 过滤目标日期 {report_date_str} 后没有数据，跳过大表追加")
        return False

    # 2. 读取基础表（匹配品类/细类）
    try:
        df_base = pd.read_excel(BASE_TABLE_PATH)
        mapping = df_base[["主体ID", "品类", "细类"]].copy()
        mapping["主体ID"] = pd.to_numeric(mapping["主体ID"], errors="coerce").astype("Int64")
        mapping = mapping.dropna(subset=["主体ID"]).drop_duplicates(subset="主体ID")
        log(f"基础表: {len(mapping)} 条映射")
    except Exception as e:
        log(f"[WARN] 读取基础表失败: {e}，品类/细类将留空")
        mapping = None

    # 3. 匹配品类/细类
    df_new["主体ID"] = pd.to_numeric(df_new["主体ID"], errors="coerce").astype("Int64")
    df_new = df_new.drop(columns=[col for col in ["品类", "细类"] if col in df_new.columns])
    if mapping is not None:
        df_new = df_new.merge(mapping, on="主体ID", how="left")
        df_new["品类"] = df_new["品类"].fillna("其他")
        df_new["细类"] = df_new["细类"].fillna("其他")
        matched = (df_new["品类"] != "其他").sum()
        log(f"品类匹配: {matched}/{len(df_new)} ({matched/len(df_new)*100:.1f}%)")
    else:
        df_new["品类"] = "其他"
        df_new["细类"] = "其他"

    # 4. 读取现有大表
    try:
        df_big = pd.read_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME)
        log(f"现有大表: {len(df_big)} 行")
    except Exception:
        log("大表不存在，创建新表")
        df_big = pd.DataFrame()

    # 5. 去重：删除大表中本次报表覆盖日期的数据（防止重复追加）
    if len(df_big) > 0 and "日期" in df_big.columns:
        # 统一日期格式为字符串比较
        df_big["日期"] = pd.to_datetime(df_big["日期"], errors="coerce").dt.strftime("%Y-%m-%d")
        before = len(df_big)
        df_big = df_big[df_big["日期"] != report_date_str]
        removed = before - len(df_big)
        if removed > 0:
            log(f"删除大表中已有的目标日期 {report_date_str} 数据: {removed} 行")

    # 6. 追加新数据
    df_combined = pd.concat([df_big, df_new], ignore_index=True)
    log(f"合并后大表: {len(df_combined)} 行")

    # 7. 保存
    try:
        tmp_path = BIG_TABLE_PATH.with_name(f"{BIG_TABLE_PATH.stem}.tmp{BIG_TABLE_PATH.suffix}")
        df_combined.to_excel(tmp_path, sheet_name=SHEET_NAME, index=False)
        tmp_path.replace(BIG_TABLE_PATH)
        log(f"=== 大表已更新: {BIG_TABLE_PATH} ===")
        log(f"日期范围: {df_combined['日期'].min()} ~ {df_combined['日期'].max()}")
    except Exception as e:
        log(f"[ERROR] 保存大表失败: {e}")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        return False

    log("\n[步骤10] 数据大表已更新")
    log("如需生成前端数据与部署: python3 automation/deploy_static.py --commit --push")

    return True


# ======================== 主入口 ========================
def main():
    if len(sys.argv) < 2:
        mode = "download"
    else:
        mode = sys.argv[1].lower()

    log(f"运行模式: {mode}")
    lock_handle = None
    if mode == "download":
        lock_handle = acquire_lock(DOWNLOAD_DIR / "wanxiangtai_download.lock")
        if lock_handle is None:
            sys.exit(1)

    try:
        if mode == "login":
            asyncio.run(do_login())
        elif mode == "download":
            ok = asyncio.run(do_download())
            sys.exit(0 if ok else 1)
        else:
            print(f"未知模式: {mode}")
            print("可用模式: login | download")
            sys.exit(1)
    finally:
        if hasattr(lock_handle, "close"):
            lock_handle.close()


if __name__ == "__main__":
    main()
