# 🍺 Wiesn-Monitor — Oktoberfest-Tischreservierung 2026

Überwacht **alle großen Festzelte + die Storno-Sammelliste** rund um die Uhr und schickt dir einen **Telegram-Push aufs Handy**, sobald sich an einer Reservierung etwas tut. Läuft **kostenlos 24/7 in GitHub Actions** — dein Mac darf aus sein.

**Oktoberfest 2026: Sa 19. September – So 4. Oktober**

Zwei Spuren, beide nutzen:
1. **Teil A — jetzt selbst buchen:** Als flexibler Werktags-Geher hast du gute Chancen. Sofort machbar.
2. **Teil B — Monitor laufen lassen:** Fängt die Stornos ab, die oft nur Minuten frei sind.

---

## Teil A — Jetzt direkt buchen (die realistische Spur)

Abende & Wochenenden bei Schützen/Schottenhamel gehen fast nur an Stammgäste. **Aber** werktags + mittags/tags ist oft direkt buchbar — genau dein Fall.

1. **Gruppengröße klären.** Die meisten Zelte reservieren **ganze Tische = 8–10 Personen**. Für kleinere Gruppen: halben Tisch (oft ab 4–6) anfragen oder dazusetzen lassen; zur Not einfach **vormittags früh hingehen** — da kriegt man auch ohne Reservierung gut Plätze.
2. **Bei den Favoriten anfragen — „Werktag" + „Mittag" wählen:**
   - Schützen-Festzelt → https://reservierung.schuetzenfestzelt.com/reservation
   - Schottenhamel → https://reservierung.festhalle-schottenhamel.de/reservation/
3. **Kosten:** Reservierung ist gratis, aber du zahlst **Verzehrgutscheine vorab** (meist 2 Maß + ½ Hendl pro Person, mittags ~45–55 €/Person). Die Reservierung gilt erst nach Überweisung.

Alle Portale stehen in `tents.json`.

---

## Teil B — Monitor einrichten (einmalig ~15 Min)

### Schritt 1 — Telegram-Bot anlegen
1. In Telegram **@BotFather** öffnen → `/newbot` → Namen vergeben.
2. Du bekommst einen **Token** (`8123456789:AAH...`). Aufheben.
3. **Schreib deinem neuen Bot eine Nachricht** (irgendwas, z. B. „hi") — sonst darf er dir nicht antworten.

### Schritt 2 — chat_id holen
Im Terminal, in diesem Ordner:
```bash
python3 get_chat_id.py DEIN_BOT_TOKEN
```
→ zeigt deine **chat_id** (eine Zahl). Aufheben.

### Schritt 3 — GitHub-Repo anlegen
1. Konto auf **github.com** (falls noch keins).
2. **New repository** → Name z. B. `wiesn-monitor` → **Public** (Public = unbegrenzte kostenlose Action-Minuten) → **Create**.
3. **Add file → Upload files** → diese Dateien hochladen:
   `monitor.py`, `tents.json`, `requirements.txt`, `get_chat_id.py`, `.gitignore`
   und den Ordner **`.github`** (mit `workflows/wiesn.yml`).
   → **`state.json` NICHT hochladen** — die legt der Monitor selbst an.
4. **Commit changes**.

### Schritt 4 — Secrets eintragen (Token bleibt geheim)
Im Repo: **Settings → Secrets and variables → Actions → New repository secret**. Zwei Stück:

| Name | Wert |
|---|---|
| `TELEGRAM_TOKEN` | dein Bot-Token |
| `TELEGRAM_CHAT_ID` | deine chat_id |

### Schritt 5 — starten & testen
1. Reiter **Actions** → ggf. „I understand my workflows, go ahead and enable them".
2. Links **Wiesn-Monitor** → **Run workflow** (manueller Start).
3. Nach ~1 Min kommt eine Telegram-Nachricht „**Wiesn-Monitor ist live**". ✅
4. Ab jetzt läuft er **alle ~10 Min automatisch** und meldet jede Änderung.

Fertig. 🎉

---

## Wie's funktioniert & wo die Grenzen sind (ehrlich)

- Der Monitor liest den sichtbaren Text jeder Seite und vergleicht ihn mit dem letzten Stand. Ändert sich was, bekommst du **Zelt + Link + was neu ist**.
- **Beste Quelle:** die **Storno-Sammelliste** (wiesnkini) — listet frei werdende Slots **aller** Zelte präzise mit Tag & Uhrzeit.
- **Favoriten live (v2):** Schützen & Schottenhamel laufen über die JavaScript-App „Festzelt OS". Dafür rendert der Monitor diese Portale mit einem **echten Browser** (Playwright, in `tents.json` als `"kind": "portal_spa"` markiert) und liest die **aktuell freien Tage** direkt aus dem Datums-Dropdown. Wird ein Tag durch Storno frei, kommt sofort ein Push mit genau diesem Tag. ✅
- **Noch offen:** Paulaner & Fischer-Vroni (auch Festzelt OS) zeigen auf der Startseite keine direkte Datumsliste — sie werden mitgerendert, lösen aber aktuell keine Tag-genaue Meldung aus. Lässt sich bei Bedarf nachziehen.
- **Browser in der Cloud:** GitHub Actions installiert Chromium automatisch (gecacht). Jeder Lauf dauert dadurch ~1–2 Min — bei 10-Min-Takt völlig unkritisch und weiter kostenlos.

## Lokal testen (optional, am Mac)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium   # einmalig: Browser für die Favoriten
export TELEGRAM_TOKEN=...    # optional
export TELEGRAM_CHAT_ID=...  # optional
python monitor.py --test     # schickt nur eine Testnachricht
python monitor.py            # ein echter Durchlauf
```

## Anpassen
- **Zelte hinzufügen/entfernen:** `tents.json` bearbeiten.
- **Takt ändern:** in `.github/workflows/wiesn.yml` die Zeile `cron: "*/10 * * * *"`.
- **Ab 1.9.2026:** offizielles Resale-Portal `oktoberfest-booking.com` als weitere Quelle aufnehmen.

## Kosten & Datenschutz
- **0 €** bei öffentlichem Repo. Dein Token liegt verschlüsselt in den GitHub Secrets, nie im Code.
- Nur lesende Zugriffe auf öffentlich erreichbare Seiten.
