#!/usr/bin/env python3
"""Build the site's daily AI-curated technology/news feed.

Flow:
1. Pull recent candidates from public RSS feeds.
2. Ask OpenAI GPT-5.6 Luna to select the most relevant/trending stories and write short original summaries.
3. Resolve article images from RSS media or og:image.
4. Write news-feed.js consumed by the static site.

The OpenAI API key is read only from OPENAI_API_KEY and should never be committed.
"""
from __future__ import annotations

import html
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "news-feed.js"
OPENAI_URL = "https://api.openai.com/v1/responses"
MODEL = os.getenv("OPENAI_NEWS_MODEL", "gpt-5.6-luna")

FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Engadget": "https://www.engadget.com/rss.xml",
    "TechRadar": "https://www.techradar.com/rss",
    "VentureBeat": "https://venturebeat.com/feed/",
    "Gizmodo": "https://gizmodo.com/rss",
    "Wired": "https://www.wired.com/feed/rss",
    "Mashable": "https://mashable.com/feeds/rss/all",
    "SlashGear": "https://www.slashgear.com/feed/",
    "PlayStation Blog": "https://blog.playstation.com/feed/",
    "The Next Web": "https://thenextweb.com/feed",
}

TECH_TERMS = re.compile(
    r"\b(ai|artificial intelligence|agent|agents|model|llm|robot|robotics|openai|anthropic|gemini|copilot|nvidia|apple|google|microsoft|meta|"
    r"chip|semiconductor|gpu|cloud|cybersecurity|security|quantum|wearable|vr|ar|mixed reality|startup|developer|software|hardware|"
    r"crypto|blockchain|bitcoin|ethereum|web3|privacy|zero[- ]knowledge|machine learning|automation)\b",
    re.I,
)


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = parsedate_to_datetime(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def find_text(el: ET.Element, names: tuple[str, ...]) -> str:
    for child in list(el):
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names and child.text:
            return child.text
    return ""


def find_link(el: ET.Element) -> str:
    for child in list(el):
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag == "link":
            href = child.attrib.get("href")
            if href:
                return href
            if child.text:
                return child.text.strip()
    return ""


def find_image(el: ET.Element) -> str:
    for child in el.iter():
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in {"content", "thumbnail", "enclosure"}:
            url = child.attrib.get("url") or child.attrib.get("href")
            kind = (child.attrib.get("type") or "").lower()
            if url and (tag != "enclosure" or not kind or kind.startswith("image/")):
                return url
    # Some feeds place an image URL inside media:description/content HTML.
    for child in el.iter():
        if child.text and "<img" in child.text.lower():
            m = re.search(r'<img[^>]+src=[\"\']([^\"\']+)', child.text, re.I)
            if m:
                return m.group(1)
    return ""


def fetch_feed(source: str, url: str) -> list[dict]:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "CryptoEngineerNewsBot/1.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as exc:
        print(f"[feed] {source}: skipped ({exc})")
        return []

    candidates = []
    for item in root.iter():
        tag = item.tag.rsplit("}", 1)[-1].lower()
        if tag not in {"item", "entry"}:
            continue
        title = clean_text(find_text(item, ("title",)))
        link = find_link(item)
        summary = clean_text(find_text(item, ("description", "summary", "content")))
        date_raw = find_text(item, ("pubdate", "published", "updated", "date"))
        image = find_image(item)
        if not title or not link:
            continue
        dt = parse_date(date_raw)
        age_hours = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600
        if age_hours > 96:
            continue
        # Prioritize stories clearly connected to technology/AI, but keep a few broader stories.
        relevance = 2 if TECH_TERMS.search(title + " " + summary) else 0
        candidates.append({
            "id": f"{source.lower().replace(' ', '-')}-{abs(hash(link))}",
            "source": source,
            "title": title,
            "url": link,
            "date": dt.astimezone(timezone.utc).isoformat(),
            "summary": summary[:700],
            "image": image,
            "relevance": relevance,
        })
    candidates.sort(key=lambda x: (x["relevance"], x["date"]), reverse=True)
    return candidates[:12]


def openai_text(prompt: str) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    payload = {
        "model": MODEL,
        "input": prompt,
        "max_output_tokens": 6000,
    }
    r = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if not r.ok:
        raise RuntimeError(f"OpenAI API {r.status_code}: {r.text[:500]}")
    data = r.json()
    # Responses API returns output items; collect output_text parts.
    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("No JSON array found in model response")
    return json.loads(text[start:end + 1])


def resolve_image(url: str, article_url: str) -> str:
    if url:
        return urljoin(article_url, url)
    try:
        r = requests.get(article_url, timeout=20, headers={"User-Agent": "Mozilla/5.0 CryptoEngineerNewsBot/1.0"})
        r.raise_for_status()
        head = r.text[:500000]
        for pattern in [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        ]:
            m = re.search(pattern, head, re.I)
            if m:
                return urljoin(article_url, html.unescape(m.group(1)))
    except Exception:
        pass
    return ""


def make_id(source: str, url: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-")
    # Stable enough for a daily static feed without adding dependencies.
    import hashlib
    return f"{safe}-{hashlib.sha1(url.encode()).hexdigest()[:10]}"


def main():
    all_candidates = []
    for source, feed in FEEDS.items():
        all_candidates.extend(fetch_feed(source, feed))
    # Deduplicate by URL and keep the newest 100 candidates.
    unique = {x["url"]: x for x in all_candidates}
    candidates = sorted(unique.values(), key=lambda x: (x["relevance"], x["date"]), reverse=True)[:100]
    if len(candidates) < 6:
        raise RuntimeError(f"Only {len(candidates)} usable news candidates were found")

    prompt = """
You are the editorial AI for CryptoEngineer, a technology and AI news desk.
Choose the 10 most useful, timely, diverse and genuinely interesting stories from the supplied candidates.
Prioritize AI, software, chips, cybersecurity, developer technology, robotics, major platforms, crypto/Web3 and important product launches.
Avoid duplicate stories about the same event when possible. Do not invent facts.
Use the candidate URL as the source URL and keep the source publication name.
Write an original 1-2 sentence English summary for each selected story. Do not copy source text.
Return ONLY a JSON array of exactly 10 objects with these fields:
source, title, url, date, category, summary, image
The image field should be the candidate image URL if present, otherwise an empty string.

Candidates:
""" + json.dumps(candidates, ensure_ascii=False)

    try:
        selected = extract_json(openai_text(prompt))
    except Exception as exc:
        print(f"[openai] failed: {exc}; using deterministic fallback")
        selected = [
            {**x, "category": "Technology", "summary": x["summary"] or "Latest technology and AI news from the source publication.", "image": x.get("image", "")}
            for x in candidates[:10]
        ]

    by_url = {x["url"]: x for x in candidates}
    final = []
    for item in selected[:10]:
        url = item.get("url", "").strip()
        base = by_url.get(url, {})
        if not url or not item.get("title"):
            continue
        image = resolve_image(item.get("image", "") or base.get("image", ""), url)
        final.append({
            "id": make_id(item.get("source", base.get("source", "News")), url),
            "source": item.get("source") or base.get("source", "News"),
            "category": item.get("category") or "Technology",
            "date": item.get("date") or base.get("date", datetime.now(timezone.utc).isoformat()),
            "title": item.get("title"),
            "summary": item.get("summary") or base.get("summary") or "Latest technology news.",
            "url": url,
            "image": image,
        })

    if len(final) < 6:
        raise RuntimeError(f"AI returned only {len(final)} usable stories")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    js = "// Auto-generated daily by GitHub Actions + OpenAI. Do not edit manually.\n"
    js += f"// Last update: {stamp}\nwindow.CENews = " + json.dumps(final, ensure_ascii=False, indent=2) + ";\n"
    OUT.write_text(js, encoding="utf-8")
    print(f"Wrote {len(final)} stories to {OUT}")


if __name__ == "__main__":
    main()
