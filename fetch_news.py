#!/usr/bin/env python3
"""
Build an Alexa Flash Briefing feed of kid-friendly world news.

Pulls RSS from kids' news sites, cleans the text so it sounds natural when
Alexa reads it aloud, picks the 5 freshest stories (mixing sources), and
writes docs/feed.json in the Flash Briefing JSON format.

Standard library only - no pip installs needed.
"""

import html
import json
import re
import sys
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Settings - edit these
# ---------------------------------------------------------------------------

# (spoken source name, RSS url). Order = priority when mixing stories.
SOURCES = [
    ("News for Kids", "https://newsforkids.net/feed/"),
    ("Kiwi Kids News", "https://kiwikidsnews.co.nz/feed"),
    ("BBC Newsround", "https://feeds.bbci.co.uk/newsround/home/rss.xml"),
]

MAX_ITEMS = 5            # Alexa allows 1-5 items per feed
MAX_AGE_DAYS = 4         # Alexa ignores items older than 7 days
MAX_SUMMARY_CHARS = 420  # roughly 20-25 seconds of speech per story

# Stories whose title or summary contains any of these words are skipped.
# Kids' outlets already filter heavily; this is an extra parent-controlled net.
BLOCKLIST = [
    "murder", "killed", "shooting", "stabbing", "suicide", "abuse",
    "massacre", "terror", "execution",
]

OUTPUT = Path(__file__).parent / "docs" / "feed.json"
USER_AGENT = "KidsWorldNewsBriefing/1.0 (personal Alexa flash briefing)"

# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def strip_html(raw: str) -> str:
    p = _TextExtractor()
    p.feed(raw or "")
    return html.unescape(" ".join(p.parts))


BOILERPLATE = [
    r"The post .*? appeared first on .*?\.?$",   # WordPress footer
    r"\bSource:.*$",                              # News for Kids source line
    r"\[(?:…|\.\.\.|&#8230;)\]",                  # "[…]"
    r"Continue reading.*$",
    r"Read more.*$",
]


def last_full_sentence(text: str) -> str:
    end = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
    return text[: end + 1] if end > 40 else text


def clean_summary(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    truncated = bool(re.search(r"\[(?:…|\.\.\.|&#8230;)\]|…\s*$", text))
    for pat in BOILERPLATE:
        text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s+", " ", text).rstrip(" …").strip()
    if truncated:
        text = last_full_sentence(text + " ")
    if len(text) > MAX_SUMMARY_CHARS:
        # Cut at the last full sentence that fits.
        cut = text[:MAX_SUMMARY_CHARS]
        last = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        text = cut[: last + 1] if last > 80 else cut.rsplit(" ", 1)[0] + "."
    # Drop a trailing half-sentence left by a truncated excerpt.
    if text and text[-1] not in ".!?\"'":
        last = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
        text = text[: last + 1] if last > 80 else text + "."
    return text


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse_rss(xml_bytes: bytes, source: str):
    root = ET.fromstring(xml_bytes)
    for item in root.iter("item"):
        title = strip_html(item.findtext("title", "")).strip()
        link = (item.findtext("link") or "").strip()
        desc = item.findtext("description") or ""
        pub = item.findtext("pubDate")
        if not (title and link and pub):
            continue
        try:
            date = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        yield {
            "source": source,
            "title": title,
            "link": link,
            "summary": clean_summary(strip_html(desc)),
            "date": date,
        }


def is_blocked(story) -> bool:
    text = f"{story['title']} {story['summary']}".lower()
    return any(re.search(rf"\b{re.escape(w)}", text) for w in BLOCKLIST)


def pick_stories(by_source):
    """Round-robin across sources so one site doesn't fill the whole briefing."""
    queues = [sorted(s, key=lambda x: x["date"], reverse=True) for s in by_source]
    picked = []
    while len(picked) < MAX_ITEMS and any(queues):
        for q in queues:
            if q and len(picked) < MAX_ITEMS:
                picked.append(q.pop(0))
    return sorted(picked, key=lambda x: x["date"], reverse=True)


def to_flash_briefing(story) -> dict:
    title = story["title"].rstrip(".!? ")
    spoken = f"From {story['source']}: {title}. {story['summary']}".strip()
    return {
        "uid": str(uuid.uuid5(uuid.NAMESPACE_URL, story["link"])),
        "updateDate": story["date"].strftime("%Y-%m-%dT%H:%M:%S.0Z"),
        "titleText": title,
        "mainText": spoken,
        "redirectionUrl": story["link"],
    }


def main() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    by_source, seen = [], set()
    for name, url in SOURCES:
        try:
            stories = list(parse_rss(fetch(url), name))
        except Exception as e:  # one dead feed shouldn't break the briefing
            print(f"WARN  {name}: {e}", file=sys.stderr)
            continue
        fresh = []
        for s in stories:
            if s["date"] < cutoff or s["link"] in seen or not s["summary"]:
                continue
            if is_blocked(s):
                print(f"SKIP  {name}: {s['title']}", file=sys.stderr)
                continue
            seen.add(s["link"])
            fresh.append(s)
        print(f"OK    {name}: {len(fresh)} fresh stories", file=sys.stderr)
        by_source.append(fresh)

    items = [to_flash_briefing(s) for s in pick_stories(by_source)]
    if not items:
        print("No fresh stories - keeping the previous feed.", file=sys.stderr)
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(items)} items to {OUTPUT}", file=sys.stderr)
    for i in items:
        print(f"  - {i['titleText']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
