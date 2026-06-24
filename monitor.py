#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wiesn-Monitor — überwacht Oktoberfest-Tischreservierungen 2026 und schickt
einen Telegram-Push, sobald eine neue freie Reservierung auftaucht
(z. B. eine Stornierung, die wieder frei wird).

Läuft kostenlos 24/7 in GitHub Actions (cron alle ~10 Min).
Kein WhatsApp-Abo, kein externer Dienst — alles in deiner Hand.

Funktionsweise:
- Holt für jede Quelle den sichtbaren Text der Seite.
  * Normale Seiten         -> per einfachem Abruf (requests).
  * "portal_spa"-Seiten    -> per echtem Browser (Playwright), weil die
    Favoriten (Schützen, Schottenhamel, Paulaner, Fischer-Vroni) JavaScript-
    Apps von "Festzelt OS" sind. Deren Datums-Dropdown listet GENAU die
    aktuell freien Tage -> unser Signal.
- Filtert aus dem Text nur "echte" Slot-/Datumszeilen heraus (Marketing wird
  ignoriert -> keine Fehlalarme).
- Vergleicht set-basiert mit dem letzten Stand (state.json) und meldet nur
  NEUE Einträge.

Aufruf:
  python monitor.py          -> ein Durchlauf (so läuft es in GitHub Actions)
  python monitor.py --test   -> nur eine Telegram-Testnachricht senden
"""

import os
import re
import sys
import json
import html
import pathlib

import requests
from bs4 import BeautifulSoup

HERE = pathlib.Path(__file__).parent
TENTS_FILE = HERE / "tents.json"
STATE_FILE = HERE / "state.json"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

HTTP_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept-Language": "de-DE,de;q=0.9",
}
TIMEOUT = 25

# Eine Zeile zählt nur als "echter Slot", wenn sie eine Zeitspanne, eine Uhrzeit
# oder ein konkretes Datum enthält -> reiner Marketing-/Menütext fällt raus.
SLOT = re.compile(
    r"\d{1,2}[:.]\d{2}\s*[-–—]\s*\d{1,2}[:.]\d{2}"   # Zeitspanne  09:00 - 16:15
    r"|\b\d{1,2}\.\d{1,2}\.\d{2,4}"                    # Datum       20.09.2026
    r"|\b\d{1,2}\.\d{1,2}\.(?!\d)"                     # Datum       25.9.
    r"|\b\d{1,2}:\d{2}\b"                              # Uhrzeit     17:00
)
# Langes deutsches Datum aus den Festzelt-OS-Dropdowns: "Freitag, 2. Oktober 2026"
LONGDATE = re.compile(
    r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),?\s+"
    r"\d{1,2}\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|"
    r"September|Oktober|November|Dezember)\s+\d{4}"
)


def slot_lines(text):
    """Aus rohem Text die Menge der echten Slot-/Datumszeilen ziehen."""
    out = set()
    for raw in text.splitlines():
        s = " ".join(raw.split())
        if s and (SLOT.search(s) or LONGDATE.search(s)):
            out.add(s)
    return out


def text_via_requests(url):
    """Sichtbaren Text per einfachem HTTP-Abruf (für normale Seiten)."""
    r = requests.get(url, headers=HTTP_HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    # r.content (Bytes) -> BeautifulSoup erkennt Encoding selbst (Marstall-Fix).
    soup = BeautifulSoup(r.content, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "head"]):
        tag.decompose()
    return soup.get_text("\n")


def render_spa(urls):
    """Sichtbaren Text der SPA-Portale per echtem Browser (Playwright) holen.
    Gibt {url: text} zurück. Fehlt Playwright, bleibt das Dict leer und die
    Portale werden später per requests (ungenau) geprüft."""
    out = {}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[i] Playwright nicht installiert — SPA-Portale nur per "
              "einfachem Abruf (ungenau). Für slot-genaue Favoriten: "
              "pip install playwright && python -m playwright install chromium")
        return out
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for url in urls:
            try:
                page = browser.new_page(locale="de-DE")
                page.goto(url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(3000)        # SPA fertig rendern lassen
                out[url] = page.inner_text("body")
                page.close()
            except Exception as e:
                print(f"[WARN] Browser {url}: {e}")
        browser.close()
    return out


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def send_telegram(text):
    """Schickt eine Nachricht; ohne Konfiguration nur Ausgabe in der Konsole."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[i] Telegram nicht konfiguriert — Nachricht nur in der Konsole:\n")
        print(text)
        return
    api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(api, timeout=20, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        })
        if r.status_code != 200:
            print(f"[WARN] Telegram-Fehler {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[WARN] Telegram-Exception: {e}")


def format_alerts(alerts):
    label = {
        "aggregator": "📋 Storno-Liste",
        "portal_spa": "🎯 Portal (live)",
        "portal_static": "🍺 Zelt",
    }
    parts = ["🚨 <b>Wiesn — neue freie Reservierung(en)!</b>"]
    for a in alerts:
        parts.append("")
        parts.append(f"{label.get(a['kind'], '🍺')}: <b>{html.escape(a['name'])}</b>")
        for line in a["new"][:8]:
            parts.append(f"• {html.escape(line)[:120]}")
        parts.append(f"➡️ {a['url']}")
    return "\n".join(parts)[:3900]


def main():
    tents = load_json(TENTS_FILE, [])
    state = load_json(STATE_FILE, {})
    first_run = not state.get("_initialized")

    # SPA-Portale gesammelt per Browser rendern (ein Browserstart für alle).
    spa_urls = [t["url"] for t in tents if t.get("kind") == "portal_spa"]
    spa_text = render_spa(spa_urls) if spa_urls else {}

    alerts = []
    checked = 0
    for t in tents:
        name, url, kind = t["name"], t["url"], t.get("kind", "portal_static")
        try:
            if kind == "portal_spa" and url in spa_text:
                text = spa_text[url]               # vom Browser gerendert
            else:
                text = text_via_requests(url)      # normaler Abruf
        except Exception as e:
            print(f"[WARN] {name}: {e}")
            continue
        checked += 1

        slots = slot_lines(text)
        prev = set(state.get(url, []))
        new = sorted(slots - prev)

        if prev and new and not first_run:
            alerts.append({"name": name, "url": url, "kind": kind, "new": new})
            print(f"[!] {name}: {len(new)} neue Slot-/Datumszeile(n)")

        state[url] = sorted(slots)

    state["_initialized"] = True
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    if first_run:
        send_telegram(
            "🍺 <b>Wiesn-Monitor ist live.</b>\n"
            f"Beobachte {checked} Quellen rund um die Uhr (inkl. Schützen & "
            "Schottenhamel live). Du bekommst eine Nachricht, sobald eine neue "
            "freie Reservierung auftaucht.\nProst! 🥨"
        )
        print(f"[ok] Erster Lauf — Basis von {checked} Quellen gespeichert.")
    elif alerts:
        send_telegram(format_alerts(alerts))
        print(f"[ok] {len(alerts)} Zelt(e) mit neuen Slots gemeldet.")
    else:
        print(f"[ok] {checked} Quellen geprüft, nichts Neues.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        send_telegram("✅ Test vom Wiesn-Monitor — wenn du das liest, passt Telegram.")
    else:
        main()
