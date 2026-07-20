#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe Wanxiangtai creative report download and inspect fields.

This script is intentionally local-only:
  - it does not update the dashboard JSON
  - it does not append to the big workbook
  - it does not commit or deploy anything
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
import zipfile

import pandas as pd

from config import BASE_TABLE_PATH, DOWNLOAD_DIR, REPORT_DIR, SCREENSHOT_DIR, STATE_FILE
from wanxiangtai_download import (
    BTN_CONFIRM,
    DOWNLOAD_LIST_URL,
    HOME_URL,
    async_playwright,
    click_download_report_button,
    close_modal,
    get_dialog_task_name,
    is_logged_in,
    log,
    open_dialog_date_picker,
    select_dialog_date_range,
    set_dialog_date_to_report_date,
    task_snapshot,
)


CREATIVE_PREFIX = "创意报表_"
CREATIVE_REPORT_URL = "https://one.alimama.com/index.html#!/report/creative?rptType=creative"


def report_range() -> tuple[str, str]:
    start = os.environ.get("WORKBUDDY_REPORT_START", "").strip()
    end = os.environ.get("WORKBUDDY_REPORT_END", "").strip()
    if start or end:
        if not start or not end:
            raise ValueError("WORKBUDDY_REPORT_START 和 WORKBUDDY_REPORT_END 必须同时设置")
        start_date = datetime.strptime(start, "%Y-%m-%d").strftime("%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d").strftime("%Y-%m-%d")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")
        return start_date, end_date
    override = os.environ.get("WORKBUDDY_REPORT_DATE", "").strip()
    if override:
        date = datetime.strptime(override, "%Y-%m-%d").strftime("%Y-%m-%d")
        return date, date
    date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return date, date


async def navigate_to_creative_report(page) -> bool:
    """Open the creative report page from existing report navigation."""
    log(f"[创意探针] 直达创意报表: {CREATIVE_REPORT_URL}")
    await page.goto(CREATIVE_REPORT_URL, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(12)
    await close_modal(page)
    if await wait_for_creative_report_ready(page):
        return True

    try:
        entry = page.get_by_text("创意报表", exact=True).first
        if await entry.is_visible(timeout=5000):
            await entry.click(timeout=5000)
            log("[创意探针] 已通过文本点击左侧创意报表")
            await asyncio.sleep(8)
            await close_modal(page)
            if await wait_for_creative_report_ready(page):
                return True
    except Exception as e:
        log(f"[创意探针] 文本点击创意报表失败: {e}")

    click_result = await page.evaluate(
        """
() => {
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const candidates = Array.from(document.querySelectorAll('a, button, span, div, [role="button"], [role="tab"]'))
    .filter(visible)
    .map(el => ({el, text: norm(el.textContent), rect: el.getBoundingClientRect()}))
    .filter(item => item.text === '创意报表' || item.text.includes('创意报表'))
    .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height));
  const target = candidates[0];
  if (!target) {
    const reportTexts = Array.from(document.querySelectorAll('a, button, span, div, [role="button"], [role="tab"]'))
      .filter(visible)
      .map(el => norm(el.textContent))
      .filter(text => text.includes('报表'))
      .slice(0, 80);
    return {clicked: false, reason: 'creative_entry_not_found', reportTexts};
  }
  target.el.scrollIntoView({block: 'center', inline: 'nearest'});
  target.el.click();
  return {
    clicked: true,
    text: target.text,
    rect: {
      x: Math.round(target.rect.x), y: Math.round(target.rect.y),
      width: Math.round(target.rect.width), height: Math.round(target.rect.height)
    }
  };
}
"""
    )
    log(f"[创意探针] 创意报表入口点击结果: {click_result}")
    if click_result and click_result.get("clicked"):
        await asyncio.sleep(8)
        await close_modal(page)
        return await wait_for_creative_report_ready(page)

    for url in [CREATIVE_REPORT_URL]:
        log(f"[创意探针] 尝试直达 URL: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)
        if await wait_for_creative_report_ready(page):
            return True
    return False


async def wait_for_creative_report_ready(page, timeout_seconds: int = 180) -> bool:
    log("[创意探针] 等待创意报表页面加载完成...")
    deadline = datetime.now().timestamp() + timeout_seconds
    last_state = None
    while datetime.now().timestamp() < deadline:
        try:
            state = await page.evaluate(
                """
() => {
  const text = document.body?.innerText || '';
  return {
    url: location.href,
    hasCreativeTitle: text.includes('创意报表'),
    hasCreativeDetail: text.includes('创意数据明细'),
    hasDownloadButton: text.includes('下载报表'),
    hasItemTitle: text.includes('商品报表'),
    textLength: text.length
  };
}
"""
            )
            last_state = state
            if (
                state.get("hasCreativeTitle")
                and state.get("hasCreativeDetail")
                and state.get("hasDownloadButton")
            ):
                log(f"[创意探针] 创意报表页面已就绪: {state}")
                return True
        except Exception as e:
            last_state = {"error": str(e)}
        await asyncio.sleep(3)
    log(f"[创意探针][ERROR] 创意报表页面未就绪: {last_state}")
    return False


async def dismiss_blocking_overlays(page) -> None:
    """Close campaign popups that can intercept the report download button."""
    result = await page.evaluate(
        """
() => {
  const visible = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const overlays = Array.from(document.querySelectorAll(
    '[id^="wrapper_dlg_"], [id^="mask_dlg_"], .ant-modal, [role="dialog"]'
  ))
    .filter(visible)
    .filter(el => (
      el.id.startsWith('wrapper_dlg_') ||
      el.id.startsWith('mask_dlg_') ||
      norm(el.textContent).includes('活动')
    ));
  let closed = 0;
  let suppressed = 0;
  for (const overlay of overlays) {
    const control = Array.from(overlay.querySelectorAll('button, [class*="close"], [aria-label="Close"], [aria-label="关闭"], svg, i, span, div'))
      .filter(visible)
      .find(el => {
        const text = norm(el.textContent);
        const klass = typeof el.className === 'string' ? el.className : el.getAttribute('class') || '';
        return text === '关闭' || text === '立即关闭' || text === '取消' || text === '知道了' || /close/i.test(klass);
      });
    const rect = overlay.getBoundingClientRect();
    const cornerControl = Array.from(overlay.querySelectorAll('button, [role="button"], svg, i, span, div'))
      .filter(visible)
      .map(el => ({el, rect: el.getBoundingClientRect()}))
      .filter(item => item.rect.right >= rect.right - 90 && item.rect.top <= rect.top + 90 && item.rect.width <= 80 && item.rect.height <= 80)
      .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height))[0]?.el;
    const target = overlay.id.startsWith('mask_dlg_') ? null : control || cornerControl;
    if (target) {
      target.click();
      closed += 1;
    }
    // Marketing banners occasionally keep an invisible click-capturing wrapper
    // after the close action. Do not let that wrapper block report automation.
    if (visible(overlay)) {
      overlay.style.setProperty('pointer-events', 'none', 'important');
      overlay.style.setProperty('display', 'none', 'important');
      suppressed += 1;
    }
  }
  return {closed, suppressed, overlayCount: overlays.length};
}
"""
    )
    log(f"[创意探针] 拦截浮层处理结果: {result}")
    await asyncio.sleep(1)


async def ensure_dimension_all(page) -> bool:
    """Set the current report dimension selector to all selected dimensions."""
    log("[创意探针] 设置维度为全选")
    opened = await page.evaluate(
        """
() => {
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const candidates = Array.from(document.querySelectorAll('button, div, span, [role="button"], [role="combobox"]'))
    .filter(visible)
    .map(el => ({el, rect: el.getBoundingClientRect(), text: norm(el.textContent)}))
    .filter(item => item.text.includes('维度') && !item.text.includes('数据指标'))
    .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height));
  const target = candidates[0];
  if (!target) return {opened: false, reason: 'dimension_trigger_not_found'};
  target.el.scrollIntoView({block: 'center', inline: 'nearest'});
  target.el.click();
  return {opened: true, text: target.text, rect: {
    x: Math.round(target.rect.x), y: Math.round(target.rect.y),
    width: Math.round(target.rect.width), height: Math.round(target.rect.height)
  }};
}
"""
    )
    log(f"[创意探针] 维度下拉打开结果: {opened}")
    if not opened or not opened.get("opened"):
        return False
    await asyncio.sleep(1)

    selected = await page.evaluate(
        """
() => {
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const popups = Array.from(document.querySelectorAll('.next-overlay-wrapper, .ant-popover, .ant-select-dropdown, [role="listbox"], body'))
    .filter(visible)
    .map(el => ({el, text: norm(el.textContent), rect: el.getBoundingClientRect()}))
    .filter(item => item.text.includes('全选') || item.text.includes('确定'))
    .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height));
  const popup = popups[0]?.el || document.body;
  const all = Array.from(popup.querySelectorAll('label, span, div, button, [role="checkbox"]'))
    .filter(visible)
    .map(el => ({el, text: norm(el.textContent), rect: el.getBoundingClientRect()}))
    .filter(item => item.text === '全选' || item.text.includes('全选'))
    .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height))[0];
  if (!all) return {selected: false, reason: 'select_all_not_found', popupText: norm(popup.textContent).slice(0, 200)};
  all.el.click();
  return {selected: true, text: all.text, popupText: norm(popup.textContent).slice(0, 200)};
}
"""
    )
    log(f"[创意探针] 维度全选结果: {selected}")
    if not selected or not selected.get("selected"):
        return False
    await asyncio.sleep(1)

    confirmed = await page.evaluate(
        """
() => {
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const candidates = Array.from(document.querySelectorAll('button, span, div, [role="button"]'))
    .filter(visible)
    .map(el => ({el, text: norm(el.textContent), rect: el.getBoundingClientRect()}))
    .filter(item => item.text === '确定')
    .sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height));
  const target = candidates[0];
  if (!target) return {clicked: false, reason: 'confirm_not_found'};
  target.el.click();
  return {clicked: true, text: target.text};
}
"""
    )
    log(f"[创意探针] 维度弹层确定结果: {confirmed}")
    await asyncio.sleep(4)
    return bool(confirmed and confirmed.get("clicked"))


async def confirm_dialog(page) -> bool:
    for text in [BTN_CONFIRM, "确认", "提交", "开始下载"]:
        try:
            btn = page.get_by_role("button", name=text).first
            if await btn.is_visible(timeout=2000):
                await btn.click(timeout=5000)
                log(f"[创意探针] 已点击弹窗按钮: {text}")
                return True
        except Exception:
            pass
    return False


async def _find_download_dialog(page):
    """Return the visible download dialog, without relying on framework classes."""
    return await page.evaluate(
        """
() => {
  const visible = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const title = Array.from(document.querySelectorAll('span, div'))
    .find(el => visible(el) && norm(el.textContent) === '下载报表');
  let modal = title || null;
  while (modal) {
    const rect = modal.getBoundingClientRect();
    const text = norm(modal.textContent);
    if (rect.width > 400 && text.includes('日期范围') && text.includes('文件名称')) {
      return {text, rect, className: modal.className || ''};
    }
    modal = modal.parentElement;
  }
  return null;
}
"""
    )


async def click_dialog_text(page, target_text: str) -> bool:
    """Click an exact visible option inside the download dialog."""
    result = await page.evaluate(
        """
({targetText}) => {
  const visible = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const title = Array.from(document.querySelectorAll('span, div'))
    .find(el => visible(el) && norm(el.textContent) === '下载报表');
  let modal = title || null;
  while (modal) {
    const rect = modal.getBoundingClientRect();
    if (rect.width > 400 && norm(modal.textContent).includes('日期范围') && norm(modal.textContent).includes('文件名称')) break;
    modal = modal.parentElement;
  }
  if (!modal) return {clicked: false, reason: 'download_dialog_not_found'};
  const candidates = Array.from(modal.querySelectorAll('label, button, span, div'))
    .filter(visible)
    .map(el => ({el, rect: el.getBoundingClientRect(), text: norm(el.textContent)}))
    .filter(item => item.text === targetText && item.rect.width > 8 && item.rect.height > 8)
    .sort((a,b) => a.rect.width * a.rect.height - b.rect.width * b.rect.height);
  const target = candidates[0];
  if (!target) return {clicked: false, reason: 'target_not_found', modalText: norm(modal.textContent)};
  target.el.click();
  return {clicked: true, text: target.text};
}
""",
        {"targetText": target_text},
    )
    log(f"[创意探针] 点击弹窗选项 {target_text} 结果: {result}")
    return bool(result and result.get("clicked"))


async def select_dialog_option(page, field_label: str, option_text: str) -> bool:
    """Open a named selector and choose one option from its popover."""
    opened = await click_dialog_text(page, field_label)
    if not opened:
        return False
    await asyncio.sleep(1)

    selected = await page.evaluate(
        """
({optionText}) => {
  const visible = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const candidates = Array.from(document.querySelectorAll('.mx-output-bottom.mx-output-open, .mx-output, [role="listbox"], [class*="dropdown"], [class*="menu"]'))
    .filter(visible)
    .flatMap(popup => Array.from(popup.querySelectorAll('label, li, [role="option"], button, span, div')))
    .filter(visible)
    .map(el => ({el, rect: el.getBoundingClientRect(), text: norm(el.textContent)}))
    .filter(item => item.text === optionText && item.rect.width > 15 && item.rect.height > 12)
    .sort((a,b) => a.rect.width * a.rect.height - b.rect.width * b.rect.height);
  const target = candidates[0];
  if (!target) return {selected: false, reason: 'option_not_found', optionText};
  target.el.click();
  return {selected: true, text: target.text};
}
""",
        {"optionText": option_text},
    )
    log(f"[创意探针] 选择 {field_label}={option_text} 结果: {selected}")
    await asyncio.sleep(1)
    return bool(selected and selected.get("selected"))


async def configure_creative_download_dialog(page) -> bool:
    """Configure creative-specific export dimensions after the date is confirmed."""
    # These options are radios in the download dialog. Selecting "全部数据指标"
    # preserves the metrics required by the creative dashboard (CTR, CVR, sales,
    # cost, carts, and so on), while "素材粒度报表" exposes actual material rows.
    selected = await page.evaluate(
        """
() => {
  const visible = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const norm = text => (text || '').replace(/\\s+/g, '');
  const clickRadio = text => {
    const label = Array.from(document.querySelectorAll('label'))
      .find(el => visible(el) && norm(el.textContent) === text);
    if (!label) return {ok: false, reason: 'label_not_found', text};
    const input = label.querySelector('input[type="radio"]');
    if (!input) return {ok: false, reason: 'radio_not_found', text};
    if (!input.checked) label.click();
    return {ok: input.checked, text, checked: input.checked};
  };
  const metric = clickRadio('全部数据指标');
  const granularity = clickRadio('素材粒度报表');
  const checked = Array.from(document.querySelectorAll('label input[type="radio"]'))
    .filter(input => input.checked && visible(input.closest('label')))
    .map(input => norm(input.closest('label').textContent));
  return {metric, granularity, checked};
}
"""
    )
    log(f"[创意探针] 导出选项设置结果: {selected}")
    if not selected or not selected.get("metric", {}).get("ok") or not selected.get("granularity", {}).get("ok"):
        return False
    await asyncio.sleep(1)
    checked = selected.get("checked", [])
    return "全部数据指标" in checked and "素材粒度报表" in checked


async def wait_and_download_task(page, task_name: str | None, out_zip: Path) -> bool:
    today_str = datetime.now().strftime("%Y%m%d")
    fallback_prefixes = [f"{CREATIVE_PREFIX}{today_str}"]
    await page.goto(DOWNLOAD_LIST_URL, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(8)
    await close_modal(page)
    log(f"[创意探针] 下载任务页 URL: {page.url}")

    task_ready = False
    for i in range(60):
        status = await page.evaluate(
            """
(args) => {
  const exactName = args.exactName;
  const prefixes = args.prefixes || [];
  const rows = Array.from(document.querySelectorAll('tr'));
  for (const row of rows) {
    const compact = (row.textContent || '').replace(/\\s+/g, ' ').trim();
    let matched = exactName ? compact.includes(exactName) : false;
    if (!matched) matched = prefixes.some(p => compact.includes(p));
    if (!matched) continue;
    if (compact.includes('生成成功')) return {status: 'success', text: compact.slice(0, 260)};
    if (compact.includes('生成失败')) return {status: 'failed', text: compact.slice(0, 260)};
    if (compact.includes('生成中') || compact.includes('排队中') || compact.includes('处理中')) return {status: 'pending', text: compact.slice(0, 260)};
    return {status: 'found', text: compact.slice(0, 260)};
  }
  return {status: 'not_found'};
}
""",
            {"exactName": task_name, "prefixes": fallback_prefixes if not task_name else []},
        )
        if status.get("status") == "success":
            log(f"[创意探针] 任务生成成功: {status.get('text')}")
            task_ready = True
            break
        if status.get("status") == "failed":
            log(f"[创意探针][ERROR] 任务生成失败: {status.get('text')}")
            return False
        if (i + 1) % 6 == 0:
            log(f"[创意探针] 等待任务生成中: {status}")
            await page.goto(DOWNLOAD_LIST_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
        await asyncio.sleep(5)
    if not task_ready:
        log(f"[创意探针][ERROR] 任务超时: {task_name or fallback_prefixes[0]}")
        for row in await task_snapshot(page):
            log(f"  [任务快照] {row}")
        return False

    task_key = task_name or fallback_prefixes[0]
    download_received = asyncio.Event()
    downloaded_path = [None]

    async def handle_download(d):
        log(f"[创意探针] 检测到下载: {d.suggested_filename}")
        p = DOWNLOAD_DIR / d.suggested_filename
        await d.save_as(str(p))
        downloaded_path[0] = p
        download_received.set()

    page.on("download", lambda d: asyncio.create_task(handle_download(d)))

    hover_target = await page.evaluate(
        """
(targetKey) => {
  const rows = Array.from(document.querySelectorAll('tr'));
  const row = rows.find(item => (item.textContent || '').replace(/\\s+/g, ' ').includes(targetKey));
  if (!row) return {found: false, reason: 'row_not_found'};
  row.scrollIntoView({block: 'center'});
  const rect = row.getBoundingClientRect();
  return {
    found: true,
    x: rect.left + 48,
    y: rect.top + rect.height / 2,
    top: rect.top,
    bottom: rect.bottom,
    text: (row.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 180)
  };
}
""",
        task_key,
    )
    log(f"[创意探针] 目标行悬停位置: {hover_target}")
    if hover_target and hover_target.get("found"):
        await page.mouse.move(float(hover_target["x"]), float(hover_target["y"]))
        await asyncio.sleep(1)

    clicked = await page.evaluate(
        """
(targetKey) => {
  const rows = Array.from(document.querySelectorAll('tr'));
  const rowIndex = rows.findIndex(item => (item.textContent || '').replace(/\\s+/g, ' ').includes(targetKey));
  const row = rows[rowIndex];
  if (!row) return {clicked: false, reason: 'row_not_found'};
  row.scrollIntoView({block: 'center'});
  const rect = row.getBoundingClientRect();
  const move = new MouseEvent('mousemove', {bubbles: true, clientX: rect.left + 50, clientY: rect.top + rect.height / 2});
  row.dispatchEvent(move);
  const actionRow = rows[rowIndex + 1];
  const rowButtons = actionRow ? Array.from(actionRow.querySelectorAll('button, a, [role="button"], span, div'))
    .filter(el => {
      const text = (el.textContent || '').trim();
      const r = el.getBoundingClientRect();
      return text === '下载' && r.width > 0 && r.height > 0;
    }) : [];
  if (rowButtons.length) {
    rowButtons[0].click();
    return {clicked: true, via: 'next_action_row', text: (rowButtons[0].textContent || '').trim(), actionText: (actionRow.textContent || '').replace(/\\s+/g, ' ').trim()};
  }
  if (actionRow && (actionRow.textContent || '').includes('下载')) {
    const x = rect.left + 48;
    const y = rect.bottom + 21;
    const el = document.elementFromPoint(x, y);
    if (el) {
      el.click();
      return {clicked: true, via: 'next_action_row_point', text: (el.textContent || '').trim(), actionText: (actionRow.textContent || '').replace(/\\s+/g, ' ').trim(), point: {x: Math.round(x), y: Math.round(y)}};
    }
  }
  const buttons = Array.from(document.querySelectorAll('button, a, [role="button"]'))
    .filter(el => {
      const text = (el.textContent || '').trim();
      const r = el.getBoundingClientRect();
      if (!(text === '下载' || text.startsWith('下载'))) return false;
      if (r.width <= 0 || r.height <= 0) return false;
      const y = r.top + r.height / 2;
      return y >= rect.top - 8 && y <= rect.bottom + 80;
    });
  if (!buttons.length) return {clicked: false, reason: 'download_button_not_found', rowText: (row.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 220), nextText: actionRow ? (actionRow.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120) : ''};
  buttons[0].click();
  return {clicked: true, text: (buttons[0].textContent || '').trim()};
}
""",
        task_key,
    )
    log(f"[创意探针] 下载按钮点击结果: {clicked}")
    if not clicked.get("clicked"):
        selected = await page.evaluate(
            """
(targetKey) => {
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  for (const input of Array.from(document.querySelectorAll('input[type="checkbox"]'))) {
    if (input.checked) {
      const rect = input.getBoundingClientRect();
      (document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2) || input).click();
    }
  }
  const rows = Array.from(document.querySelectorAll('tr'));
  const row = rows.find(item => (item.textContent || '').replace(/\\s+/g, ' ').includes(targetKey));
  if (!row) return {selected: false, reason: 'row_not_found'};
  row.scrollIntoView({block: 'center'});
  const rowRect = row.getBoundingClientRect();
  const checkbox = Array.from(row.querySelectorAll('input[type="checkbox"], [class*="checkbox"], [role="checkbox"]'))
    .filter(visible)[0];
  if (checkbox) {
    const rect = checkbox.getBoundingClientRect();
    (document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2) || checkbox).click();
  } else {
    const cell = row.querySelector('td') || row;
    const cellRect = cell.getBoundingClientRect();
    const x = Math.min(cellRect.left + 32, cellRect.right - 8);
    const y = rowRect.top + rowRect.height / 2;
    (document.elementFromPoint(x, y) || cell).click();
  }
  const selectedRows = Array.from(document.querySelectorAll('tr'))
    .map(item => (item.textContent || '').replace(/\\s+/g, ' ').trim())
    .filter(text => text.includes('报表_') && text.includes(targetKey));
  return {selected: true, selectedRows, rowBounds: {
    top: rowRect.top, bottom: rowRect.bottom, left: rowRect.left, right: rowRect.right
  }};
}
""",
            task_key,
        )
        log(f"[创意探针] 目标行勾选结果: {selected}")
        await asyncio.sleep(1)
        clicked = await page.evaluate(
            """
(rowBounds) => {
  const candidates = Array.from(document.querySelectorAll('button, a, [role="button"]'))
    .filter(el => {
      const text = (el.textContent || '').trim();
      const rect = el.getBoundingClientRect();
      const disabled = el.disabled || el.getAttribute('aria-disabled') === 'true' ||
        (el.className || '').toString().includes('disabled');
      return text === '下载' && rect.width > 0 && rect.height > 0 && !disabled;
    })
    .map(el => ({el, rect: el.getBoundingClientRect(), text: (el.textContent || '').trim()}))
    .filter(item => {
      const midY = item.rect.top + item.rect.height / 2;
      return !rowBounds || (midY >= rowBounds.top - 8 && midY <= rowBounds.bottom + 90);
    });
  if (!candidates.length) return {clicked: false, reason: 'target_download_not_found'};
  candidates.sort((a, b) => {
    const ay = a.rect.top + a.rect.height / 2;
    const by = b.rect.top + b.rect.height / 2;
    return Math.abs(ay - rowBounds.bottom) - Math.abs(by - rowBounds.bottom);
  });
  const btn = candidates[0];
  btn.el.click();
  return {clicked: true, text: btn.text, rect: {
    x: Math.round(btn.rect.x), y: Math.round(btn.rect.y),
    width: Math.round(btn.rect.width), height: Math.round(btn.rect.height)
  }};
}
""",
            selected.get("rowBounds") if selected else None,
        )
        log(f"[创意探针] 可见下载按钮点击结果: {clicked}")
        if False and not clicked.get("clicked") and selected and selected.get("selectedRows"):
            clicked = await page.evaluate(
                """
() => {
  const candidates = Array.from(document.querySelectorAll('button, a, [role="button"]'))
    .filter(el => {
      const text = (el.textContent || '').trim();
      const rect = el.getBoundingClientRect();
      const disabled = el.disabled || el.getAttribute('aria-disabled') === 'true' ||
        (el.className || '').toString().includes('disabled');
      return text === '下载' && rect.width > 0 && rect.height > 0 && !disabled;
    });
  if (!candidates.length) return {clicked: false, reason: 'bulk_download_not_found'};
  candidates.sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top);
  const btn = candidates[0];
  const rect = btn.getBoundingClientRect();
  btn.click();
  return {clicked: true, text: (btn.textContent || '').trim(), rect: {
    x: Math.round(rect.x), y: Math.round(rect.y),
    width: Math.round(rect.width), height: Math.round(rect.height)
  }};
}
"""
            )
            log(f"[创意探针] 批量下载按钮点击结果: {clicked}")
    if not clicked.get("clicked"):
        return False

    try:
        await asyncio.wait_for(download_received.wait(), timeout=90)
    except asyncio.TimeoutError:
        log("[创意探针][ERROR] 下载超时")
        return False
    src = downloaded_path[0]
    if not src or not src.exists():
        return False
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    out_zip.write_bytes(src.read_bytes())
    src.unlink()
    log(f"[创意探针] 已保存: {out_zip} ({out_zip.stat().st_size} bytes)")
    return True


def extract_report(zip_path: Path, date_str: str) -> Path | None:
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith((".csv", ".xlsx", ".xls")):
                suffix = Path(name).suffix
                out = zip_path.with_name(f"万相台创意报表_{date_str}{suffix}")
                with zf.open(name) as source:
                    out.write_bytes(source.read())
                log(f"[创意探针] 已解压: {out}")
                return out
    return None


def read_report(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    errors = []
    for enc in ["utf-8-sig", "utf-8", "gb18030", "gbk"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            errors.append(f"{enc}: {e}")
    raise RuntimeError("无法读取创意报表；" + "；".join(errors))


def inspect_report(path: Path, start_date: str, end_date: str) -> bool:
    df = read_report(path)
    log(f"[创意探针] 报表行列: {df.shape[0]} 行, {df.shape[1]} 列")
    if "日期" not in df.columns:
        log("[创意探针][ERROR] 创意报表缺少日期字段")
        return False
    dates = pd.to_datetime(df["日期"], errors="coerce").dt.strftime("%Y-%m-%d")
    if dates.isna().any() or dates.min() != start_date or dates.max() != end_date:
        log(f"[创意探针][ERROR] 报表日期不匹配: 实际 {dates.min()} 至 {dates.max()}，期望 {start_date} 至 {end_date}")
        return False
    log(f"[创意探针] 报表日期已验证: {start_date} 至 {end_date}")
    log("[创意探针] 字段清单:")
    for col in df.columns:
        log(f"  - {col}")

    subject_col = next((c for c in ["主体ID", "商品ID", "宝贝ID", "商品id", "主体id"] if c in df.columns), None)
    material_cols = [c for c in df.columns if any(k in str(c) for k in ["素材", "创意", "图片", "image", "url", "URL", "链接"])]
    log(f"[创意探针] 主体ID候选字段: {subject_col or '未找到'}")
    log(f"[创意探针] 素材/图片候选字段: {material_cols or '未找到'}")

    if subject_col and BASE_TABLE_PATH.exists():
        base = pd.read_excel(BASE_TABLE_PATH)
        base_id = next((c for c in ["主体ID", "商品ID", "宝贝ID", "id", "ID"] if c in base.columns), None)
        cat_col = next((c for c in ["品类", "分类", "类目"] if c in base.columns), None)
        if base_id and cat_col:
            left = df.copy()
            left[subject_col] = left[subject_col].astype(str).str.replace(r"\\.0$", "", regex=True)
            base2 = base[[base_id, cat_col]].copy()
            base2[base_id] = base2[base_id].astype(str).str.replace(r"\\.0$", "", regex=True)
            merged = left.merge(base2, how="left", left_on=subject_col, right_on=base_id)
            phone = merged[merged[cat_col] == "手机"]
            log(f"[创意探针] 基础表匹配字段: {base_id} -> {cat_col}")
            log(f"[创意探针] 手机品类行数: {len(phone)} / {len(merged)}")
            if len(phone):
                sample_cols = [c for c in ["日期", "计划名字", "计划名称", subject_col, "点击率", "展现量", "点击量", "花费"] if c in phone.columns]
                sample_cols += [c for c in material_cols if c not in sample_cols][:5]
                log("[创意探针] 手机样例前5行:")
                log(phone[sample_cols].head(5).to_string(index=False))
        else:
            log(f"[创意探针][WARN] 基础表字段不足，base_id={base_id}, cat_col={cat_col}")
    return True


async def main() -> bool:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    start_date, end_date = report_range()
    range_label = start_date if start_date == end_date else f"{start_date}_{end_date}"
    out_zip = REPORT_DIR / f"万相台创意报表_{range_label}.zip"
    if out_zip.exists():
        out_zip.unlink()
    existing_task_name = os.environ.get("WORKBUDDY_EXISTING_TASK_NAME", "").strip()
    if not STATE_FILE.exists():
        log("[创意探针][ERROR] 未找到登录态，请先运行商品报表 login")
        return False

    headed = os.environ.get("HEADED", "0") == "1"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed, channel="chrome", args=["--start-maximized"])
        context = await browser.new_context(
            storage_state=str(STATE_FILE),
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = await context.new_page()
        try:
            await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            title = await page.title()
            log(f"[创意探针] 首页状态: URL={page.url} | 标题={title}")
            if not is_logged_in(page.url, title):
                log("[创意探针][ERROR] 登录态已过期，请先重新 login")
                return False

            if existing_task_name:
                log(f"[创意探针] 使用已有下载任务恢复: {existing_task_name}")
                downloaded = await wait_and_download_task(page, existing_task_name, out_zip)
            else:
                if not await navigate_to_creative_report(page):
                    await page.screenshot(path=str(SCREENSHOT_DIR / "creative_entry_not_found.png"))
                    log("[创意探针][ERROR] 未能进入创意报表")
                    return False
                await page.screenshot(path=str(SCREENSHOT_DIR / "creative_report_page.png"))

                if not await ensure_dimension_all(page):
                    await page.screenshot(path=str(SCREENSHOT_DIR / "creative_dimension_failed.png"))
                    log("[创意探针][ERROR] 维度全选失败")
                    return False

                await dismiss_blocking_overlays(page)
                if not await click_download_report_button(page):
                    await page.screenshot(path=str(SCREENSHOT_DIR / "creative_download_button_failed.png"))
                    log("[创意探针][ERROR] 下载报表按钮点击失败")
                    return False
                await asyncio.sleep(5)
                task_name = await get_dialog_task_name(page)
                log(f"[创意探针] 弹窗任务名: {task_name}")
                if task_name and not task_name.startswith(CREATIVE_PREFIX):
                    log(f"[创意探针][WARN] 任务名不像创意报表: {task_name}")

                if start_date == end_date:
                    date_set = await set_dialog_date_to_report_date(page, start_date)
                else:
                    opened = await open_dialog_date_picker(page)
                    date_set = bool(opened and opened.get("opened")) and await select_dialog_date_range(page, start_date, end_date)
                if not date_set:
                    await page.screenshot(path=str(SCREENSHOT_DIR / "creative_date_failed.png"))
                    return False
                if os.environ.get("INSPECT_EXPORT_DIALOG") == "1":
                    await page.screenshot(path=str(SCREENSHOT_DIR / "creative_export_dialog.png"))
                    log(f"[创意探针] 已保存导出弹窗检查图: {SCREENSHOT_DIR / 'creative_export_dialog.png'}")
                    return False
                if not await configure_creative_download_dialog(page):
                    await page.screenshot(path=str(SCREENSHOT_DIR / "creative_export_options_failed.png"))
                    log("[创意探针][ERROR] 未能设置素材粒度或额外指标")
                    return False
                if not await confirm_dialog(page):
                    await page.screenshot(path=str(SCREENSHOT_DIR / "creative_confirm_failed.png"))
                    return False
                await asyncio.sleep(3)
                downloaded = await wait_and_download_task(page, task_name, out_zip)

            if not downloaded:
                await page.screenshot(path=str(SCREENSHOT_DIR / "creative_download_failed.png"))
                return False
        finally:
            await browser.close()

    extracted = extract_report(out_zip, range_label)
    if not extracted:
        log("[创意探针][ERROR] ZIP 中没有 CSV/XLSX 报表")
        return False
    return inspect_report(extracted, start_date, end_date)


if __name__ == "__main__":
    ok = asyncio.run(main())
    raise SystemExit(0 if ok else 1)
