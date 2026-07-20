#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a visual-dedup map for the local creative dashboard.

The report can assign different URLs or material IDs to the same-looking image.
We use a compact perceptual hash, not the URL, to group those images.
"""

from __future__ import annotations

import io
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

from config import FRONTEND_DIR, REPORT_DIR


PRIVATE_DATA_DIR = FRONTEND_DIR / "private-data"
INDEX_FILE = PRIVATE_DATA_DIR / "creative-index.json"
STRICT_THRESHOLD = 8
MAIN_IMAGE_THRESHOLD = 24


def report_date() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def load_records() -> tuple[dict, list[dict], str]:
    if not INDEX_FILE.exists():
        raise SystemExit(f"[ERROR] 未找到素材看板索引: {INDEX_FILE}")
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    category = os.environ.get("WORKBUDDY_CREATIVE_CATEGORY", "").strip()
    categories = [category] if category else index.get("categories", [])
    records = []
    for item in categories:
        payload_file = PRIVATE_DATA_DIR / f"creative-{item}.json"
        if not payload_file.exists():
            raise SystemExit(f"[ERROR] 未找到品类素材数据: {payload_file}")
        records.extend(json.loads(payload_file.read_text(encoding="utf-8")).get("records", []))
    return index, records, category


def image_hash(url: str) -> int:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        content = response.read()
    image = Image.open(io.BytesIO(content)).convert("L").resize((16, 16))
    pixels = list(image.getdata())
    average = sum(pixels) / len(pixels)
    return sum((value >= average) << index for index, value in enumerate(pixels))


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def cluster_urls(urls: list[str], hashes: dict[str, int], clicks: dict[str, int], threshold: int) -> tuple[dict[str, str], int]:
    representatives: list[str] = []
    canonical: dict[str, str] = {}
    for url in sorted((item for item in urls if item in hashes), key=lambda item: clicks[item], reverse=True):
        match = next(
            (candidate for candidate in representatives if hamming_distance(hashes[url], hashes[candidate]) <= threshold),
            None,
        )
        if match:
            canonical[url] = match
        else:
            representatives.append(url)
            canonical[url] = url
    return canonical, len(representatives)


def main() -> None:
    data, records, category = load_records()
    image_rows = [
        row for row in records if row.get("isImage") and row.get("imageUrl")
    ]
    url_clicks: dict[str, int] = {}
    subject_urls: dict[str, set[str]] = {}
    for row in image_rows:
        url_clicks[row["imageUrl"]] = url_clicks.get(row["imageUrl"], 0) + int(row.get("clicks", 0))
        subject_key = str(row.get("subjectId", ""))
        subject_urls.setdefault(subject_key, set()).add(row["imageUrl"])

    hashes: dict[str, int] = {}
    errors: dict[str, str] = {}
    # Image CDNs have meaningful request latency. Parallel downloads keep this
    # local preprocessing fast while remaining deliberately modest in volume.
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(image_hash, url): url for url in url_clicks}
        for future in as_completed(futures):
            url = futures[future]
            try:
                hashes[url] = future.result()
            except Exception as exc:
                errors[url] = str(exc)

    # Strict groups preserve distinct creative variants. Main-image groups use
    # a wider threshold but never cross the product subject boundary.
    canonical, strict_groups = cluster_urls(list(hashes), hashes, url_clicks, STRICT_THRESHOLD)
    for url in errors:
        canonical[url] = url

    main_visual_by_subject_url: dict[str, str] = {}
    main_groups = 0
    for subject_key, urls in subject_urls.items():
        grouped, group_count = cluster_urls(list(urls), hashes, url_clicks, MAIN_IMAGE_THRESHOLD)
        main_groups += group_count
        for url in urls:
            main_visual_by_subject_url[f"{subject_key}::{url}"] = grouped.get(url, canonical.get(url, url))

    start_date = data.get("dateStart") or data.get("date") or report_date()
    end_date = data.get("dateEnd") or start_date
    range_label = start_date if start_date == end_date else f"{start_date}_{end_date}"
    output = REPORT_DIR / f"创意图片视觉去重_{range_label}.json"
    output.write_text(json.dumps({
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "threshold": STRICT_THRESHOLD,
        "mainImageThreshold": MAIN_IMAGE_THRESHOLD,
        "canonicalByUrl": canonical,
        "mainVisualBySubjectUrl": main_visual_by_subject_url,
        "summary": {
            "category": category or "全部品类",
            "sourceImages": len(url_clicks),
            "visualGroups": strict_groups + len(errors),
            "mainImageGroups": main_groups,
            "unreadableImages": len(errors),
        },
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成: {output}")
    print(f"图片链接: {len(url_clicks)} · 创意变体: {strict_groups + len(errors)} · 主图聚类: {main_groups} · 下载失败: {len(errors)}")


if __name__ == "__main__":
    main()
