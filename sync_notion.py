#!/usr/bin/env python3
"""
sync_notion.py — 从 Notion 拉取网站内容，生成 data.json
使用方法：
  pip install requests
  NOTION_TOKEN="你的token" python3 sync_notion.py
"""

import json
import os
import requests

# ── CONFIG ────────────────────────────────
NOTION_TOKEN  = os.environ.get("NOTION_TOKEN", "")
DB_EXPERIENCE = "328906e1fb75801e8c2de498ee27c1ab"
DB_AI_STACK   = "329906e1fb7580008592e353b5bdb156"
DB_PROJECTS   = "329906e1fb758010ba6ce81ff8076407"
DB_WATCHLIST  = "329906e1fb758006b109fb2ab02ea26d"
PAGE_ABOUT    = "328906e1fb75806eb964e7cef1d96b3e"
OUTPUT_PATH   = "data.json"
# ─────────────────────────────────────────

# 用 session，header 值强制 ascii 编码避免 latin-1 报错
session = requests.Session()
session.headers["Authorization"]  = "Bearer " + NOTION_TOKEN
session.headers["Notion-Version"] = "2022-06-28"
session.headers["Content-Type"]   = "application/json"

def get_text(prop):
    if not prop:
        return ""
    t = prop.get("type", "")
    if t == "title":
        return "".join(r["plain_text"] for r in prop.get("title", []))
    if t == "rich_text":
        return "".join(r["plain_text"] for r in prop.get("rich_text", []))
    if t == "select":
        s = prop.get("select")
        return s["name"] if s else ""
    if t == "url":
        return prop.get("url") or ""
    return ""

def query_database(db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    results, payload = [], {}
    while True:
        res = session.post(url, json=payload)
        res.raise_for_status()
        data = res.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results

def get_page_blocks(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = session.get(url)
    res.raise_for_status()
    return res.json().get("results", [])

def block_to_text(block):
    bt = block.get("type", "")
    rich = block.get(bt, {}).get("rich_text", [])
    return "".join(r["plain_text"] for r in rich)

def parse_experience():
    rows = query_database(DB_EXPERIENCE)
    result = []
    for row in rows:
        p = row["properties"]
        highlights_raw = get_text(p.get("highlights", {}))
        highlights = []
        for item in highlights_raw.split("|"):
            item = item.strip()
            if ":" in item:
                tag, text = item.split(":", 1)
                highlights.append({"tag": tag.strip(), "text": text.strip()})
        awards_raw = get_text(p.get("awards", {}))
        awards = [a.strip() for a in awards_raw.split(",") if a.strip()]
        result.append({
            "company":    get_text(p.get("company", {})),
            "badge":      get_text(p.get("badge", {})),
            "role":       get_text(p.get("role", {})),
            "location":   get_text(p.get("location", {})),
            "period":     get_text(p.get("period", {})),
            "type":       get_text(p.get("type", {})),
            "highlights": highlights,
            "awards":     awards if awards else None,
        })
    return result

def parse_ai_stack():
    rows = query_database(DB_AI_STACK)
    tools = []
    for row in rows:
        p = row["properties"]
        tools.append({
            "name": get_text(p.get("name", {})),
            "use":  get_text(p.get("use", {})),
        })
    return {
        "intro": "AI isn't just a tool I use — it's reshaping how I think about product velocity, user research, and decision loops.",
        "tools": tools,
    }

def parse_projects():
    rows = query_database(DB_PROJECTS)
    projects = []
    for row in rows:
        p = row["properties"]
        tags_raw = get_text(p.get("tags", {}))
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        projects.append({
            "title": get_text(p.get("title", {})),
            "desc":  get_text(p.get("desc", {})),
            "tags":  tags,
            "link":  get_text(p.get("link", {})),
            "image": get_text(p.get("image", {})),
            "color": get_text(p.get("color", {})),
            "type":  get_text(p.get("type", {})),
        })
    return {
        "intro": "Side experiments built fast with AI — half lab, half creative outlet.",
        "projects": projects,
    }

def parse_watchlist():
    rows = query_database(DB_WATCHLIST)
    watch = []
    for row in rows:
        p = row["properties"]
        watch.append({
            "title":  get_text(p.get("title", {})),
            "desc":   get_text(p.get("desc", {})),
            "url":    get_text(p.get("url", {})),
            "source": get_text(p.get("source", {})),
        })
    return watch

def parse_about():
    blocks = get_page_blocks(PAGE_ABOUT)
    sections, current_key = {}, None
    for block in blocks:
        bt = block.get("type", "")
        if bt in ("heading_1", "heading_2", "heading_3"):
            current_key = block_to_text(block).strip().lower()
        elif bt == "paragraph" and current_key:
            text = block_to_text(block).strip()
            if text:
                sections[current_key] = text
    return {
        "quote":      sections.get("quote", ""),
        "motivation": sections.get("motivation", ""),
        "story":      sections.get("story", ""),
        "aiView":     sections.get("aiview", ""),
        "now":        sections.get("now", ""),
    }

def main():
    print("🔄 Fetching from Notion...")
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN not set. Run: NOTION_TOKEN='your_token' python3 sync_notion.py")
        return

    data = {
        "meta": {
            "name":      "Mina Fang",
            "photo":     "photo.jpg",
            "role":      "AI & Data-Driven Product Manager · Northeastern University MSCS Student",
            "subtitle":  "I build products that make data make sense, and use AI to move faster, think deeper, and ship better.",
            "location":  "San Jose, CA",
            "email":     "minafang77@gmail.com",
            "linkedin":  "https://www.linkedin.com/in/minjia-mina-fang-a2871715a/",
            "github":    "https://github.com/minjiaooo",
            "resumeUrl": "resume.pdf",
        },
        "about":      parse_about(),
        "experience": parse_experience(),
        "aiStack":    parse_ai_stack(),
        "vibeCoding": parse_projects(),
        "beyond": {
            "watch":   parse_watchlist(),
            "hobbies": [
                {"emoji": "🎨", "label": "Drawing"},
                {"emoji": "🍜", "label": "Food"},
                {"emoji": "✈️", "label": "Travel"},
            ],
        },
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    line_count = sum(1 for _ in open(OUTPUT_PATH))
    print(f"✅ data.json updated — {line_count} lines")
    print("📌 Next: git add data.json && git commit -m 'update content' && git push")

if __name__ == "__main__":
    main()
