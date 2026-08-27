#!/usr/bin/env python3
"""
build.py — Generate the log in every language: index, entry pages, RSS feed.

Usage:  python3 log/build.py          (run from anywhere)

To add an entry, drop a file in log/entries/<lang>/<slug>.html shaped like this:

    date: 2026-08-27
    kind: Note
    title: What I learned
    dek: One sentence that earns the click. Optional for short notes.
    rank: 0
    ---
    <p>The body, as plain HTML paragraphs.</p>

`rank` is optional and only breaks ties within one date — higher shows first.

English lives at /log/<slug>/, the other languages at /log/<lang>/<slug>/.
A slug that exists in several languages is linked between them automatically;
one that exists in only one language simply has no counterpart, and the
language buttons fall back to that language's index.
"""

import html
import re
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://jakubkornafel.com"
AUTHOR = "Jakub Kornafel"
ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "log"
ENTRIES_DIR = LOG_DIR / "entries"

# The first language is the default and lives at the root of /log/.
LANGS = {
    "en": {
        "label": "EN",
        "html_lang": "en",
        "path": "/log/",
        "title": f"Log — {AUTHOR}",
        "kicker": "Working log · started August 2026",
        "heading": "Log",
        "intro": "What I am building, what broke, and what the evidence actually supports. "
        "Entries are dated and finished when they are useful, not when they are polished. "
        "There is no schedule, and I would rather write nothing than write filler.",
        "description": "A working log: what I am building, what broke, and what the evidence "
        "actually supports. Dated entries, no schedule.",
        "more": "Read this entry &rarr;",
        "back": "&larr; Log",
        "feed_description": "What I am building, what broke, and what the evidence actually supports.",
    },
    "pl": {
        "label": "PL",
        "html_lang": "pl",
        "path": "/log/pl/",
        "title": f"Log — {AUTHOR}",
        "kicker": "Dziennik pracy · od sierpnia 2026",
        "heading": "Log",
        "intro": "Co buduję, co się zepsuło i co z tego naprawdę wynika z dowodów. Wpisy mają "
        "datę i powstają wtedy, kiedy są przydatne, a nie kiedy są dopieszczone. Nie ma "
        "harmonogramu — wolę nie napisać nic niż napisać wypełniacz.",
        "description": "Dziennik pracy: co buduję, co się zepsuło i co z tego wynika. "
        "Datowane wpisy, bez harmonogramu.",
        "more": "Czytaj wpis &rarr;",
        "back": "&larr; Log",
        "feed_description": "Co buduję, co się zepsuło i co z tego naprawdę wynika z dowodów.",
    },
    "es": {
        "label": "ES",
        "html_lang": "es",
        "path": "/log/es/",
        "title": f"Log — {AUTHOR}",
        "kicker": "Diario de trabajo · desde agosto de 2026",
        "heading": "Log",
        "intro": "Qué estoy construyendo, qué se rompió y qué sostienen realmente las pruebas. "
        "Las entradas llevan fecha y se terminan cuando son útiles, no cuando están pulidas. "
        "No hay calendario: prefiero no escribir nada antes que escribir relleno.",
        "description": "Diario de trabajo: qué construyo, qué se rompió y qué sostienen las "
        "pruebas. Entradas con fecha, sin calendario.",
        "more": "Leer la entrada &rarr;",
        "back": "&larr; Log",
        "feed_description": "Qué estoy construyendo, qué se rompió y qué sostienen realmente las pruebas.",
    },
    "ru": {
        "label": "RU",
        "html_lang": "ru",
        "path": "/log/ru/",
        "title": f"Log — {AUTHOR}",
        "kicker": "Рабочий дневник · с августа 2026",
        "heading": "Log",
        "intro": "Что я строю, что сломалось и что из этого выдерживает проверку фактами. "
        "У записей есть дата, и я дописываю их, когда от них появляется польза, а не когда "
        "они становятся гладкими. Расписания нет — лучше промолчать, чем написать наполнитель.",
        "description": "Рабочий дневник: что я строю, что сломалось и что из этого выдерживает "
        "проверку. Записи с датами, без расписания.",
        "more": "Читать запись &rarr;",
        "back": "&larr; Log",
        "feed_description": "Что я строю, что сломалось и что из этого выдерживает проверку фактами.",
    },
    "it": {
        "label": "IT",
        "html_lang": "it",
        "path": "/log/it/",
        "title": f"Log — {AUTHOR}",
        "kicker": "Diario di lavoro · da agosto 2026",
        "heading": "Log",
        "intro": "Cosa sto costruendo, cosa si è rotto e cosa reggono davvero i fatti. Le voci "
        "hanno una data e le chiudo quando servono a qualcosa, non quando sono levigate. "
        "Non c'è un calendario: preferisco non scrivere niente che scrivere riempitivo.",
        "description": "Diario di lavoro: cosa costruisco, cosa si è rotto e cosa reggono i fatti. "
        "Voci datate, senza calendario.",
        "more": "Leggi la voce &rarr;",
        "back": "&larr; Log",
        "feed_description": "Cosa sto costruendo, cosa si è rotto e cosa reggono davvero i fatti.",
    },
}

DEFAULT_LANG = "en"

FAVICON = (
    "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<rect width='32' height='32' fill='%2312161D'/><text y='23' x='16' text-anchor='middle' "
    "font-family='monospace' font-size='17' fill='%23F4F5F7'>jk</text></svg>"
)


def entry_url(lang, slug=None):
    base = LANGS[lang]["path"]
    return f"{base}{slug}/" if slug else base


def output_dir(lang):
    return LOG_DIR if lang == DEFAULT_LANG else LOG_DIR / lang


def read_entries(lang):
    directory = ENTRIES_DIR / lang
    entries = []
    for path in sorted(directory.glob("*.html")):
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


def available(slug):
    """Languages this slug has been written in."""
    return [lang for lang in LANGS if (ENTRIES_DIR / lang / f"{slug}.html").exists()]


def lang_switch(current, slug=None):
    """Buttons that stay on the same entry where a translation exists."""
    langs_with_slug = available(slug) if slug else list(LANGS)
    buttons = []
    for lang, conf in LANGS.items():
        target = entry_url(lang, slug) if slug and lang in langs_with_slug else entry_url(lang)
        current_attr = ' aria-current="true"' if lang == current else ""
        buttons.append(f'<a href="{target}" hreflang="{lang}"{current_attr}>{conf["label"]}</a>')
    return (
        '<div class="wrap"><nav class="langs" aria-label="Language">'
        + "".join(buttons)
        + "</nav></div>\n"
    )


def alternates(slug=None):
    langs = available(slug) if slug else list(LANGS)
    return "\n".join(
        f'<link rel="alternate" hreflang="{lang}" href="{SITE}{entry_url(lang, slug)}">'
        for lang in langs
    )


def head(lang, title, description, url, slug=None, depth=1):
    conf = LANGS[lang]
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="{conf['html_lang']}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE}{url}">
<meta property="og:image" content="{SITE}/assets/og-log.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{conf['html_lang']}">
<meta name="twitter:card" content="summary_large_image">
{alternates(slug)}
<link rel="alternate" type="application/rss+xml" title="{AUTHOR} — Log ({conf['label']})" href="{SITE}{conf['path']}feed.xml">
<link rel="icon" href="{FAVICON}">
<link rel="preload" as="font" type="font/woff2" crossorigin href="{up}assets/fonts/archivo.woff2">
<link rel="preload" as="font" type="font/woff2" crossorigin href="{up}assets/fonts/sourceserif4.woff2">
<link rel="stylesheet" href="{up}assets/log.css">
</head>
<body>
"""


def masthead(lang, on_index):
    mark = ' aria-current="page"' if on_index else ""
    return f"""<div class="wrap topbar">
  <header class="masthead">
    <a class="mark" href="/">{AUTHOR}</a>
    <nav>
      <a href="/#systems">Systems</a>
      <a href="/#community">Community</a>
      <a href="/#record">Record</a>
      <a href="{entry_url(lang)}"{mark}>Log</a>
      <a href="/research/who-checks-the-agent/">Research</a>
      <a href="/#work">Work together</a>
    </nav>
  </header>
</div>
"""


def footer(lang):
    return f"""<div class="wrap">
  <footer>
    <span>Jakub Kornafel · Málaga, Spain · Warsaw, Poland</span>
    <span><a href="{LANGS[lang]['path']}feed.xml">RSS</a> · jakubkornafel@gmail.com</span>
  </footer>
</div>

</body>
</html>
"""


def build_index(lang, entries):
    conf = LANGS[lang]
    items = []
    for entry in entries:
        url = entry_url(lang, entry["slug"])
        items.append(
            f"""      <article class="item">
        <p class="entry-meta"><span class="date">{entry['date']}</span>"""
            f"""<span class="kind {entry['kind'].lower()}">{entry['kind']}</span></p>
        <h2><a href="{url}">{entry['title']}</a></h2>
        <p>{entry['excerpt']}</p>
        <a class="more" href="{url}">{conf['more']}</a>
      </article>"""
        )

    depth = 1 if lang == DEFAULT_LANG else 2
    page = (
        head(lang, conf["title"], conf["description"], conf["path"], depth=depth)
        + masthead(lang, on_index=True)
        + lang_switch(lang)
        + f"""
<main>
  <div class="wrap">
    <section class="hero">
      <p class="kicker">{conf['kicker']}</p>
      <h1>{conf['heading']}</h1>
      <p>{conf['intro']}</p>
    </section>

    <section class="list">
{chr(10).join(items)}
    </section>
  </div>
</main>

"""
        + footer(lang)
    )

    directory = output_dir(lang)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.html").write_text(page, encoding="utf-8")


def build_entry_pages(lang, entries):
    conf = LANGS[lang]
    depth = 2 if lang == DEFAULT_LANG else 3
    for entry in entries:
        directory = output_dir(lang) / entry["slug"]
        directory.mkdir(parents=True, exist_ok=True)
        dek = f'      <p class="dek">{entry["dek"]}</p>\n' if entry["dek"] else ""
        url = entry_url(lang, entry["slug"])
        page = (
            head(
                lang,
                f"{entry['title']} — {AUTHOR}",
                entry["excerpt"] or entry["title"],
                url,
                slug=entry["slug"],
                depth=depth,
            )
            + masthead(lang, on_index=False)
            + lang_switch(lang, entry["slug"])
            + f"""
<main>
  <div class="wrap">
    <article class="post">
      <a class="back" href="{entry_url(lang)}">{conf['back']}</a>
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
            + footer(lang)
        )
        (directory / "index.html").write_text(page, encoding="utf-8")


def rfc822(date_string):
    try:
        stamp = datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        stamp = datetime.now(timezone.utc)
    return stamp.strftime("%a, %d %b %Y %H:%M:%S +0000")


def build_feed(lang, entries):
    conf = LANGS[lang]
    items = []
    for entry in entries:
        link = f"{SITE}{entry_url(lang, entry['slug'])}"
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
    <title>{AUTHOR} — Log ({conf['label']})</title>
    <link>{SITE}{conf['path']}</link>
    <atom:link href="{SITE}{conf['path']}feed.xml" rel="self" type="application/rss+xml"/>
    <description>{html.escape(conf['feed_description'])}</description>
    <language>{conf['html_lang']}</language>
    <lastBuildDate>{newest}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (output_dir(lang) / "feed.xml").write_text(feed, encoding="utf-8")


def main():
    total = 0
    for lang in LANGS:
        entries = read_entries(lang)
        if not entries:
            print(f"{lang}: no entries, skipped")
            continue
        build_index(lang, entries)
        build_entry_pages(lang, entries)
        build_feed(lang, entries)
        total += len(entries)
        print(f"{lang}: {len(entries)} entries at {LANGS[lang]['path']}")
        for entry in entries:
            print(f"   {entry_url(lang, entry['slug'])}  {entry['date']}  {entry['title']}")
    if not total:
        raise SystemExit(f"error: no entries found under {ENTRIES_DIR}")


if __name__ == "__main__":
    main()
