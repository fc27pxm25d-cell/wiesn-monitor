#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Findet deine Telegram chat_id.

Vorher: Schreib deinem Bot in Telegram irgendeine Nachricht (z. B. "hi").
Dann:   python get_chat_id.py DEIN_BOT_TOKEN
"""
import sys
import requests

token = sys.argv[1] if len(sys.argv) > 1 else input("Bot-Token: ").strip()
data = requests.get(
    f"https://api.telegram.org/bot{token}/getUpdates", timeout=20
).json()

found = {}
for upd in data.get("result", []):
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat = msg.get("chat", {})
    if chat.get("id"):
        found[chat["id"]] = chat.get("first_name") or chat.get("title") or ""

if found:
    print("\nGefundene chat_id(s):")
    for cid, who in found.items():
        print(f"  {cid}   ({who})")
    print("\n→ Diese Zahl als TELEGRAM_CHAT_ID eintragen.")
else:
    print("Keine Nachrichten gefunden. Schreib deinem Bot zuerst eine "
          "Nachricht und führ das Skript dann nochmal aus.")
