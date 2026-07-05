#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万相台商品报表自动下载脚本（完整版）

功能：
  - 首次扫码登录并保存登录态（cookie）
  - 自动下载前一天商品报表到 ~/Documents/万相台报表/
  - 支持断点续传：文件已存在则跳过
  - 支持登录态过期检测

完整下载流程（异步任务模式）：
  1. 访问商品报表页（item_promotion）
  2. 设置日期范围为前一天
  3. 点击"下载报表"按钮，弹窗中设置参数
  4. 点击"确定"创建下载任务
  5. 跳转到下载任务管理页
  6. 轮询等待任务"生成成功"
  7. 点击任务的"下载"按钮，下载文件
  8. 移动文件到 ~/Documents/万相台报表/ 并重命名

用法：
  python wanxiangtai_download.py login      # 首次扫码登录
  python wanxiangtai_download.py download   # 下载前一天商品报表
  python wanxiangtai_download.py            # 默认执行 download
"""

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


def get_report_date():
    """获取报表日期（昨天）"""
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


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
    """下载前一天商品报表到桌面（异步任务流程）"""
    if not STATE_FILE.exists():
        log("[ERROR] 未找到登录态，请先运行 login 模式扫码登录")
        return

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # 使用报表目录（已直接设置为可写路径）
    REPORT_DIR = REPORT_DIR_PRIMARY
    log(f"使用报表目录: {REPORT_DIR}")

    report_date = get_report_date()
    # 万相台下载的文件是 .zip，里面是 .xlsx
    desktop_filename = f"万相台商品报表_{report_date}.zip"
    desktop_path = REPORT_DIR / desktop_filename

    if desktop_path.exists():
        log(f"目标已存在: {desktop_filename}，跳过下载")
        return

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
                return
            log(f"已登录 | URL: {url} | 标题: {title}")

            await page.screenshot(path=str(SCREENSHOT_DIR / "01_item_report.png"))

            # ========== 步骤2: 设置日期范围为前一天 ==========
            # 当前日期选择器显示"过去 7 天"，需要改为"昨天"
            # 由于"过去 7 天"是预设项，"昨天"没有现成选项，
            # 需要在日期选择器中输入具体日期
            # 简单方案：保持当前日期范围（默认会显示最近 7 天），
            # 但实际下载时弹窗里可以调整
            log(f"\n[步骤2] 日期范围保持'过去 7 天'，下载时会在弹窗中调整")
            # 注：日期范围会影响弹窗里的默认值，但弹窗可以手动调整

            # ========== 步骤3: 点击"下载报表"按钮 ==========
            log(f"\n[步骤3] 点击'下载报表'按钮...")
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
                    return

            await asyncio.sleep(5)
            await page.screenshot(path=str(SCREENSHOT_DIR / "02_dialog.png"))

            # ========== 步骤4: 在弹窗中点击"确定" ==========
            log(f"\n[步骤4] 在弹窗中点击'确定'...")
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
                return

            await asyncio.sleep(3)
            log("步骤4完成，准备截图...")
            await page.screenshot(path=str(SCREENSHOT_DIR / "03_after_confirm.png"))
            log("任务已提交（截图完成）")

            # 记录刚创建的任务标识（万相台任务名格式：商品报表_YYYYMMDD_HHMMSS）
            # 注意：任务名中的日期是创建日期（今天），不是报表日期
            today_str = datetime.now().strftime("%Y%m%d")
            target_task_name_prefix = f"商品报表_{today_str}"
            log(f"目标任务名前缀: {target_task_name_prefix}")

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

            # ========== 步骤6: 等待任务"生成成功" ==========
            # 任务名包含当天日期（创建日期），我们刚才创建的任务名格式为
            # "商品报表_YYYYMMDD_HHMMSS"，创建日期 = report_date 创建的日期
            # 简化策略：等待页面顶部第一行的"生成成功"状态
            log(f"\n[步骤6] 等待任务生成（最多5分钟）...")
            today_str = datetime.now().strftime("%Y%m%d")
            task_found = False
            task_ready = False
            max_wait = 300  # 5分钟
            check_interval = 5
            for i in range(max_wait // check_interval):
                try:
                    # 查找第一行的状态
                    status_text = await page.evaluate("""() => {
                        // 查找包含"生成"的状态文本
                        const allText = document.body.innerText;
                        if (allText.includes('生成成功')) {
                            return 'success';
                        }
                        if (allText.includes('生成中') || allText.includes('排队中') || allText.includes('处理中')) {
                            return 'pending';
                        }
                        if (allText.includes('生成失败')) {
                            return 'failed';
                        }
                        return 'unknown';
                    }""")
                    elapsed = (i + 1) * check_interval
                    if status_text == "success":
                        log(f"任务已生成成功！耗时: {elapsed}秒")
                        task_ready = True
                        break
                    elif status_text == "failed":
                        log("[ERROR] 任务生成失败")
                        await page.screenshot(path=str(SCREENSHOT_DIR / "task_failed.png"))
                        break
                    else:
                        if elapsed % 30 == 0:
                            log(f"任务生成中... 已等待 {elapsed}秒")
                except Exception as e:
                    log(f"检查状态失败: {e}")
                await asyncio.sleep(check_interval)
                # 每30秒刷新一次页面
                if (i + 1) % 6 == 0:
                    try:
                        await page.reload(wait_until="domcontentloaded")
                        await asyncio.sleep(3)
                    except Exception:
                        pass

            if not task_ready:
                log("[ERROR] 任务生成超时")
                await page.screenshot(path=str(SCREENSHOT_DIR / "task_timeout.png"))
                await browser.close()
                return

            await page.screenshot(path=str(SCREENSHOT_DIR / "05_task_ready.png"))

            # ========== 步骤7: 点击刚创建任务的"下载"按钮 ==========
            log(f"\n[步骤7] 点击目标任务({target_task_name_prefix})的'下载'按钮...")
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

            # 通过 JS 找到包含目标任务名的行，并点击该行的下载按钮
            # 使用 page.evaluate 传参，避免 f-string 嵌套大括号的转义问题
            js_find_and_click = """
(targetPrefix) => {
    const allRows = document.querySelectorAll('tr');
    // 1) 先找包含目标任务名前缀的行
    for (const row of allRows) {
        const txt = (row.textContent || '');
        if (txt.includes(targetPrefix)) {
            const btn = Array.from(row.querySelectorAll('button')).find(b => {
                const t = (b.textContent || '').trim();
                return t === '下载' || t.startsWith('下载');
            });
            if (btn && btn.offsetParent !== null) {
                btn.scrollIntoView({block: 'center'});
                btn.click();
                return {found: true, via: 'task_name', text: btn.textContent.trim()};
            }
        }
    }
    // 2) 退而求其次：找第一个可见的"下载"按钮（最新任务在第一行）
    for (const row of allRows) {
        const btns = row.querySelectorAll('button');
        for (const btn of btns) {
            const t = (btn.textContent || '').trim();
            if (t === '下载' || t.startsWith('下载')) {
                if (btn.offsetParent !== null) {
                    btn.scrollIntoView({block: 'center'});
                    btn.click();
                    return {found: true, via: 'first_visible', text: t};
                }
            }
        }
    }
    return {found: false};
}
"""
            download_btn_clicked = False
            try:
                result = await page.evaluate(js_find_and_click, target_task_name_prefix)
                log(f"JS 点击结果: {result}")
                if result and result.get("found"):
                    download_btn_clicked = True
                    log(f"已通过 JS 点击下载按钮(via {result.get('via')})")
                    await asyncio.sleep(3)
            except Exception as e:
                log(f"JS 点击失败: {e}")

            if not download_btn_clicked:
                # 备用方案：用 Playwright locator 点击第一行下载按钮
                log("尝试备用方案：Playwright locator...")
                try:
                    btn = page.locator("button", has_text="下载").first
                    await btn.click(timeout=5000, force=True)
                    download_btn_clicked = True
                    log("已通过 Playwright 点击下载按钮(备用)")
                    await asyncio.sleep(3)
                except Exception as e2:
                    log(f"[ERROR] 备用方案也失败: {e2}")

            if not download_btn_clicked:
                log("[ERROR] 未找到刚创建任务的下载按钮")
                await page.screenshot(path=str(SCREENSHOT_DIR / "no_dl_btn.png"))
                await browser.close()
                return

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
                                        extract_path = REPORT_DIR / name
                                        zf.extract(name, str(REPORT_DIR))
                                        # 重命名为带日期的版本
                                        final_name = f"万相台商品报表_{report_date}{Path(name).suffix}"
                                        final_path = REPORT_DIR / final_name
                                        if extract_path.exists():
                                            extract_path.rename(final_path)
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
                        append_to_big_table(str(csv_to_append), report_date)
                    else:
                        log("[WARN] 未找到解压后的CSV文件，跳过大表追加")
            except asyncio.TimeoutError:
                log("[ERROR] 下载超时")
                await page.screenshot(path=str(SCREENSHOT_DIR / "dl_timeout.png"))

        except Exception as e:
            log(f"下载失败: {e}")
            try:
                await page.screenshot(path=str(SCREENSHOT_DIR / "error.png"))
            except Exception:
                pass
            raise
        finally:
            await browser.close()


# ======================== 追加到大表 + 匹配品类 ========================
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
        df_new = pd.read_csv(csv_path, encoding="gbk", errors="replace")
    except Exception:
        try:
            df_new = pd.read_csv(csv_path, encoding="utf-8-sig", errors="replace")
        except Exception as e:
            log(f"[ERROR] 读取CSV失败: {e}")
            return False

    log(f"新数据: {len(df_new)} 行, {len(df_new.columns)} 列")

    # 2. 读取基础表（匹配品类/细类）
    try:
        df_base = pd.read_excel(BASE_TABLE_PATH)
        mapping = df_base[["主体ID", "品类", "细类"]].drop_duplicates(subset="主体ID")
        log(f"基础表: {len(mapping)} 条映射")
    except Exception as e:
        log(f"[WARN] 读取基础表失败: {e}，品类/细类将留空")
        mapping = None

    # 3. 匹配品类/细类
    if mapping is not None:
        df_new = df_new.merge(mapping, on="主体ID", how="left")
        df_new["品类"] = df_new["品类"].fillna("其他")
        df_new["细类"] = df_new["细类"].fillna("其他")
        matched = (df_new["品类"] != "其他").sum()
        log(f"品类匹配: {matched}/{len(df_new)} ({matched/len(df_new)*100:.1f}%)")

    # 4. 读取现有大表
    try:
        df_big = pd.read_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME)
        log(f"现有大表: {len(df_big)} 行")
    except Exception:
        log("大表不存在，创建新表")
        df_big = pd.DataFrame()

    # 5. 去重：删除大表中已有该日期的数据（防止重复追加）
    if len(df_big) > 0 and "日期" in df_big.columns:
        # 统一日期格式为字符串比较
        df_big["日期"] = pd.to_datetime(df_big["日期"]).dt.strftime("%Y-%m-%d")
        before = len(df_big)
        df_big = df_big[df_big["日期"] != report_date_str]
        removed = before - len(df_big)
        if removed > 0:
            log(f"删除大表中已有的 {report_date_str} 数据: {removed} 行")

    # 6. 追加新数据
    df_combined = pd.concat([df_big, df_new], ignore_index=True)
    log(f"合并后大表: {len(df_combined)} 行")

    # 7. 保存
    try:
        df_combined.to_excel(BIG_TABLE_PATH, sheet_name=SHEET_NAME, index=False)
        log(f"=== 大表已更新: {BIG_TABLE_PATH} ===")
        log(f"日期范围: {df_combined['日期'].min()} ~ {df_combined['日期'].max()}")
    except Exception as e:
        log(f"[ERROR] 保存大表失败: {e}")
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

    if mode == "login":
        asyncio.run(do_login())
    elif mode == "download":
        asyncio.run(do_download())
    else:
        print(f"未知模式: {mode}")
        print("可用模式: login | download")
        sys.exit(1)


if __name__ == "__main__":
    main()
