---
name: wiki-extract
description: Geht den aktuellen Vault oder Ordner nach CleverBrands-Wissen durch und schlägt vor, was ins Firmen-Wiki gehört. Zeigt die Liste, der Nutzer bestätigt, erst dann wird eingeworfen. Privates bleibt privat.
---

# /wiki-extract

Argument optional: ein Ordner. Standard: der aktuelle Ordner.

## Schritte

1. Markdown-Dateien im Ordner suchen, die CleverBrands betreffen (Lieferanten, Produkte, Marken, Amazon, Bestellungen, Team-Entscheidungen). Dateien mit privaten Themen (Finanzen der Person, Gesundheit, Tagebuch) auslassen, auch wenn CleverBrands darin vorkommt.
2. Eine Liste zeigen: Datei, ein Satz warum, geschätzte Form (Lieferant, Produkt, Thema, Entscheidung, SOP, Learning). Höchstens 20 Einträge je Durchgang.
3. Auf die Bestätigung warten. Der Nutzer wählt („alle“, „1, 3, 5“ oder „keine“).
4. Die gewählten Dateien einwerfen: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" drop-file <pfad> [...]`, höchstens 20 je Aufruf.
5. Die Inbox-Pfade in einem Satz melden.

Nie ohne Bestätigung einwerfen. Dateien nicht verändern.
