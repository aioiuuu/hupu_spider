#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
虎扑世界杯评论爬虫

功能：
  1. 搜索虎扑"世界杯"相关帖子
  2. 提取每篇帖子的所有评论（回帖）
  3. 保存为 JSON + CSV 格式

使用：
  cd项目目录
  .venv/Scripts/activate
  python hupu_worldcup_spider.py
"""

import requests
import json
import re
import time
import random
import csv
import os
import sys
from datetime import datetime
from urllib.parse import quote

# ======================== 配置参数 ========================
CONFIG = {
    "keyword": "世界杯",
    "max_search_pages": 4,
    "max_posts": 20,
    "max_comments_per_post": 50,
    "delay_min": 1.5,
    "delay_max": 3.0,
    "timeout": 15,
    "retries": 3,
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.hupu.com/",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

session = requests.Session()
session.headers.update(HEADERS)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def clean_html(html_text):
    text = re.sub(r"<br\s*/?>", "\n", html_text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_request(url, retries=None):
    retries = retries or CONFIG["retries"]
    for attempt in range(1, retries + 1):
        try:
            time.sleep(random.uniform(CONFIG["delay_min"], CONFIG["delay_max"]))
            headers = HEADERS.copy()
            headers["User-Agent"] = random.choice(USER_AGENTS)
            resp = session.get(url, headers=headers, timeout=CONFIG["timeout"])
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                return resp
            log(f"HTTP {resp.status_code} -> {url}")
        except requests.RequestException as e:
            if attempt < retries:
                log(f"请求失败 ({attempt}/{retries}): {e}")
                time.sleep(3)
            else:
                log(f"请求失败 (重试{retries}次后放弃): {e}")
    return None


def extract_search_json(html):
    marker = "window.$$data="
    start = html.find(marker)
    if start == -1:
        return None
    pos = start + len(marker)
    if html[pos] != "{":
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(pos, len(html)):
        ch = html[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if not in_str:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(html[pos:i+1])
    return None


def extract_next_data(html):
    m = re.search(
        r'<script id="__NEXT_DATA__"[^>]*type="application/json">(.*?)</script>',
        html, re.DOTALL,
    )
    return json.loads(m.group(1)) if m else None


def search_posts(page=1):
    url = f"https://bbs.hupu.com/search?q={quote(CONFIG['keyword'])}&page={page}"
    log(f"搜索第 {page} 页...")

    resp = safe_request(url)
    if not resp:
        return [], 0

    data = extract_search_json(resp.text)
    if not data or "searchRes" not in data:
        log("无法解析搜索数据")
        return [], 0

    total = int(data["searchRes"].get("count", 0))
    posts = []
    for item in data["searchRes"].get("data", []):
        title = clean_html(item.get("title", ""))
        if not title:
            continue
        posts.append({
            "id": item.get("id", ""),
            "title": title,
            "url": f"https://bbs.hupu.com/{item['id']}.html",
            "replies": int(item.get("replies", 0)),
            "forum": item.get("forum_name", ""),
            "author": item.get("username", ""),
            "time_display": item.get("addTimeDisplay", ""),
        })

    log(f"  本页 {len(posts)} 个帖子")
    return posts, total


def get_replies(post_url):
    resp = safe_request(post_url)
    if not resp:
        return []

    data = extract_next_data(resp.text)
    if not data:
        return []

    try:
        replies_data = data["props"]["pageProps"]["detail"]["replies"]
    except (KeyError, TypeError):
        return []

    total_replies = replies_data.get("count", 0)
    total_pages = replies_data.get("total", 1)
    current_page = replies_data.get("current", 1)
    page_size = replies_data.get("size", 20)
    base_url = replies_data.get("baseUrl", "")

    post_id = None
    m = re.search(r"/bbs/(\d+)", post_url)
    if m:
        post_id = m.group(1)
    if not post_id:
        m = re.search(r"/(\d+)", base_url)
        if m:
            post_id = m.group(1)

    replies = []
    for idx, item in enumerate(replies_data.get("list", [])):
        content = clean_html(item.get("content", ""))
        if not content:
            continue

        floor = (current_page - 1) * page_size + idx + 1
        author = item.get("author", {})

        reply = {
            "floor": floor,
            "username": author.get("puname", "匿名"),
            "user_id": author.get("puid", ""),
            "content": content,
            "likes": item.get("count", 0),
            "time": item.get("createdAtFormat", ""),
            "location": item.get("location", ""),
            "quote": "",
        }

        if item.get("quote"):
            q = item["quote"]
            q_author = q.get("author", {}).get("puname", "")
            q_content = clean_html(q.get("content", ""))
            if q_content:
                reply["quote"] = f"回复 @{q_author}: {q_content[:100]}"

        replies.append(reply)

    log(f"  {len(replies)}/{total_replies} 条评论")

    if current_page < total_pages and len(replies) < CONFIG["max_comments_per_post"]:
        if post_id:
            next_page = current_page + 1
            next_url = f"https://bbs.hupu.com/{post_id}-{next_page}.html"
            log(f"  翻到第 {next_page}/{total_pages} 页...")
            more = get_replies(next_url)
            replies.extend(more)

    if CONFIG["max_comments_per_post"] and len(replies) > CONFIG["max_comments_per_post"]:
        replies = replies[:CONFIG["max_comments_per_post"]]

    return replies


CSV_FIELDS = [
    "post_id", "post_title", "post_forum",
    "floor", "username", "user_id", "content",
    "likes", "time", "location", "quote",
]

def save_results(all_comments):
    base_name = f"hupu_{CONFIG['keyword']}_comments"
    json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")
    csv_path = os.path.join(OUTPUT_DIR, f"{base_name}.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)
    log(f"JSON -> {json_path}")

    if all_comments:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_comments)
        log(f"CSV  -> {csv_path}")


def main():
    print()
    log("=" * 55)
    log("虎扑世界杯评论爬虫")
    log("=" * 55)
    print()

    all_posts = []
    for page in range(1, CONFIG["max_search_pages"] + 1):
        posts, _ = search_posts(page)
        all_posts.extend(posts)
        if CONFIG["max_posts"] and len(all_posts) >= CONFIG["max_posts"]:
            all_posts = all_posts[:CONFIG["max_posts"]]
            break

    if not all_posts:
        log("未找到任何帖子，退出")
        return

    log(f"\n共 {len(all_posts)} 个帖子，开始爬取评论\n")

    all_comments = []
    for i, post in enumerate(all_posts, 1):
        log(f"[{i}/{len(all_posts)}] {post['title'][:60]}")
        replies = get_replies(post["url"])

        for r in replies:
            r["post_title"] = post["title"]
            r["post_url"] = post["url"]
            r["post_forum"] = post["forum"]
            r["post_id"] = post["id"]
            all_comments.append(r)

        if i % 5 == 0 or i == len(all_posts):
            save_results(all_comments)
        print()

    save_results(all_comments)

    print()
    log("=" * 55)
    log(f"完成! {len(all_posts)} 个帖子, {len(all_comments)} 条评论")
    log(f"文件位置: {OUTPUT_DIR}")
    log("=" * 55)
    print()


if __name__ == "__main__":
    main()
