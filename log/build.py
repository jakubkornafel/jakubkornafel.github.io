#!/usr/bin/env python3
"""
build.py — Generate the log: index, one page per entry, and the RSS feed.

Usage:  python3 log/build.py          (run from the repository root)

To add an entry, drop a file in log/entries/<slug>.html shaped like this:

    date: 2026-08-27
    kind: Note
    title: What I learned
    dek: One sentence that earns the click. Optional for short notes.
    rank: 0
    ---
    <p>The body, as plain HTML paragraphs.</p>

`rank` is optional and only breaks ties within one date — higher shows first.
The slug becomes the URL: /log/<slug>/. Nothing else needs editing —
the index, the entry pages and feed.xml are all regenerated from these files.
"""

import html
import re
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://jakubkornafel.com"
AUTHOR = "Jakub Kornafel"
ROOT = Path(__file__).resolve().parent.parent
ENTRIES_DIR = ROOT / "log" / "entries"
LOG_DIR = ROOT / "log"

FAVICON = (
    "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<rect width='32' height='32' fill='%2312161D'/><text y='23' x='16' text-anchor='middle' "
    "font-family='monospace' font-size='17' fill='%23F4F5F7'>jk</text></svg>"
)


def read_entries():
    """Parse every entry file into a dict. Newest first, stable for equal dates."""
    entries = []
    for path in sorted(ENTRIES_DIR.glob("*.html")):
        raw = path.read_text(encoding="utf-8")
        front, _, body = raw.partition("\n---\n")
        meta = {}
        for line in front.strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()

        body = body.strip()
        first_p = re.search(r"<p[^>]*>(.*?)</p>", body, re.S)
        excerpt = meta.get("dek") or (
            " ".join(re.sub(r"<[^>]+>", "", first_p.group(1)).split()) if first_p else ""
        )

        entries.append(
            {
                "slug": path.stem,
                "rank": int(meta.get("rank", 0) or 0),
                "date": meta.get("date", ""),
                "kind": meta.get("kind", "Note"),
                "title": meta.get("title", path.stem),
                "dek": meta.get("dek", ""),
                "excerpt": excerpt,
                "body": body,
            }
        )

    entries.sort(key=lambda entry: (entry["date"], entry["rank"], entry["slug"]), reverse=True)
    return entries


def head(title, description, url, og_image=f"{SITE}/assets/og-log.png", depth=1):
    """Shared <head>. depth is how many directories below the site root the page sits."""
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="{AUTHOR} — Log" href="{SITE}/log/feed.xml">
<link rel="icon" href="{FAVICON}">
<link rel="preload" as="font" type="font/woff2" crossorigin href="{up}assets/fonts/archivo.woff2">
<link rel="preload" as="font" type="font/woff2" crossorigin href="{up}assets/fonts/sourceserif4.woff2">
<link rel="stylesheet" href="{up}assets/log.css">
</head>
<body>
"""


def masthead(current_log=True):
    mark = 'aria-current="page"' if current_log else ""
    return f"""<div class="wrap">
  <header class="masthead">
    <a class="mark" href="/">{AUTHOR}</a>
    <nav>
      <a href="/#systems">Systems</a>
      <a href="/#record">Record</a>
      <a href="/log/" {mark}>Log</a>
      <a href="/#work">Work together</a>
    </nav>
  </header>
</div>
"""


FOOTER = """<div class="wrap">
  <footer>
    <span>Jakub Kornafel · Málaga, Spain · Warsaw, Poland</span>
    <span><a href="/log/feed.xml">RSS</a> · jakubkornafel@gmail.com</span>
  </footer>
</div>

</body>
</html>
"""


def build_index(entries):
    items = []
    for entry in entries:
        items.append(
            f"""      <article class="item">
        <p class="entry-meta"><span class="date">{entry['date']}</span>"""
            f"""<span class="kind {entry['kind'].lower()}">{entry['kind']}</span></p>
        <h2><a href="/log/{entry['slug']}/">{entry['title']}</a></h2>
        <p>{entry['excerpt']}</p>
        <a class="more" href="/log/{entry['slug']}/">Read this entry &rarr;</a>
      </article>"""
        )

    page = (
        head(
            f"Log — {AUTHOR}",
            "A working log: what I am building, what broke, and what the evidence actually "
            "supports. Dated entries, no schedule.",
            f"{SITE}/log/",
            depth=1,
        )
        + masthead()
        + f"""
<main>
  <div class="wrap">
    <section class="hero">
      <p class="kicker">Working log · started August 2026</p>
      <h1>Log</h1>
      <p>What I am building, what broke, and what the evidence actually supports. Entries are
      dated and finished when they are useful, not when they are polished. There is no schedule,
      and I would rather write nothing than write filler.</p>
    </section>

    <section class="list">
{chr(10).join(items)}
    </section>
  </div>
</main>

"""
        + FOOTER
    )
    (LOG_DIR / "index.html").write_text(page, encoding="utf-8")


def build_entry_pages(entries):
    for entry in entries:
        directory = LOG_DIR / entry["slug"]
        directory.mkdir(exist_ok=True)
        dek = f'      <p class="dek">{entry["dek"]}</p>\n' if entry["dek"] else ""
        page = (
            head(
                f"{entry['title']} — {AUTHOR}",
                entry["excerpt"] or entry["title"],
                f"{SITE}/log/{entry['slug']}/",
                depth=2,
            )
            + masthead(current_log=False)
            + f"""
<main>
  <div class="wrap">
    <article class="post">
      <a class="back" href="/log/">&larr; Log</a>
      <p class="entry-meta"><span class="date">{entry['date']}</span>"""
            f"""<span class="kind {entry['kind'].lower()}">{entry['kind']}</span></p>
      <h1>{entry['title']}</h1>
{dek}      <div class="body">
{entry['body']}
      </div>
    </article>
  </div>
</main>

"""
            + FOOTER
        )
        (directory / "index.html").write_text(page, encoding="utf-8")


def rfc822(date_string):
    try:
        stamp = datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        stamp = datetime.now(timezone.utc)
    return stamp.strftime("%a, %d %b %Y %H:%M:%S +0000")


def build_feed(entries):
    items = []
    for entry in entries:
        link = f"{SITE}/log/{entry['slug']}/"
        items.append(
            f"""    <item>
      <title>{html.escape(entry['title'])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{rfc822(entry['date'])}</pubDate>
      <category>{html.escape(entry['kind'])}</category>
      <description>{html.escape(entry['excerpt'])}</description>
      <content:encoded><![CDATA[{entry['body']}]]></content:encoded>
    </item>"""
        )

    newest = rfc822(entries[0]["date"]) if entries else rfc822("")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{AUTHOR} — Log</title>
    <link>{SITE}/log/</link>
    <atom:link href="{SITE}/log/feed.xml" rel="self" type="application/rss+xml"/>
    <description>What I am building, what broke, and what the evidence actually supports.</description>
    <language>en</language>
    <lastBuildDate>{newest}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (LOG_DIR / "feed.xml").write_text(feed, encoding="utf-8")


def main():
    entries = read_entries()
    if not entries:
        raise SystemExit(f"error: no entries found in {ENTRIES_DIR}")
    build_index(entries)
    build_entry_pages(entries)
    build_feed(entries)
    print(f"built {len(entries)} entries:")
    for entry in entries:
        print(f"  /log/{entry['slug']}/  {entry['date']}  {entry['kind']}  {entry['title']}")


if __name__ == "__main__":
    main()
