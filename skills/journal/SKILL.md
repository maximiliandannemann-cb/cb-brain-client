---
name: journal
description: Betriebs-Journal des CleverBrands-Tools, reine Historie. Liest, was seit einem Zeitpunkt passiert ist (Einträge von Personen, Claude Code und Silver plus Stationen, Termine, Bewegungen, Aufgaben-Wechsel aus dem Tool) und trägt nach Ja eine Zeile ein. Für „was ist seit gestern passiert“, „was hat Silver gemacht“, „Akte PO-032“, „gib das an Silver ab“ (Aufgabe plus Zeile), Sitzungsende mit Übergabe. Was offen ist, steht in den Aufgaben (/aufgaben).
---

# /journal

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Das Journal ist reine Historie: eine Zeile je Sache, die passiert ist, mit Verfasser und Beleg. Offenes lebt nur in Aufgaben (`/aufgaben`); das Journal kennt kein „offen für“ und keine Quittung. Was dauerhaft gilt, geht mit `/drop` ins Wiki.

## Lesen

| Frage | Befehl |
|---|---|
| Was ist seit gestern / seit Montag passiert? | `journal --seit 1d` bzw. `--seit 2026-10-26` (Standard 2d, höchstens 30 Tage) |
| Was hat Silver gemacht? | `journal --von Silver` |
| Was ist offen für mich? | nicht hier: `aufgaben` (offene, auch „Mac:“) und `aufgaben --status wartet` (Nachfassen) |
| Alles zu einer Bestellung, Aufgabe, Einsendung | `journal --ref PO-032` (30 Tage, Anfang der Nummer reicht) |
| Nur Fakten aus dem Tool | `journal --art fakten` |

Antworten kurz: was passiert ist, wer, worauf bezogen. J-Nummern, CB- und PO-Nummern wörtlich.

## Eintragen (nur nach Ja)

Eine Zeile je Handlung mit Außenwirkung: Mail verschickt oder Entwurf angelegt, Nachfass-Mail, Entscheidung von Max entgegengenommen, Zusage gemacht oder bekommen, Übergabe an jemand anderen. Lesen, Suchen, Rechnen sind keine Zeilen. Vorschlag zeigen, nach Ja eintragen:

`journal-neu --art ereignis|entscheidung|zusage|uebergabe --text "<ein bis zwei Sätze>" --beleg "<woher, mit Link>" [--ref PO-032] [--faellig YYYY-MM-DD] [--bereich <b>]`

- `--text`: was passiert ist, Ort und Beleg nennen, nicht den Inhalt einer Mail kopieren (10 bis 1.000 Zeichen).
- `--beleg`: ein Satz, woher die Information kommt, mit Link, wo es einen gibt (10 bis 500). Nie erfinden.
- `uebergabe` zeigt immer auf eine Aufgabe (`--ref CB-123`), die die Arbeit trägt; `zusage` braucht `--faellig` (das zugesagte Datum; Nachfassen ist eine Aufgabe).
- `--ref` mit der Nummer, wo es eine gibt (PO, CB, IN, J); Mail-Threads mit `--ref <thread-id> --ref-art mail`.
- `--bereich` (Standard `allgemein`): `supply_chain`, `sales`, `finanzen`, `team`, `privat`. Finanzen sieht Silver nicht.
- Alles zu Geld, Kasse, Belegen, Rechnungen, Zahlungen oder Gehalt immer mit `--bereich finanzen`.
- **Nie von Hand:** Aufgaben-Ereignisse (angelegt, erledigt, zugewiesen, Frist, wartet) schreibt das Tool selbst; Stationen, Termine, Wareneingänge stehen über ihre Buchung im Journal. Zusatzinfo zu einer Aufgabe ist eine Notiz (`aufgabe-aendern CB-123 --notiz`). Freigaben (`freigabe`) schreibt nur eine Tür des Tools.
- Ein wiederholter Befehl am selben Tag schreibt nicht doppelt („Schon eingetragen“).

## Sitzungsende

Am Ende einer Sitzung mit Firmenbezug eine Übergabe vorschlagen: „**Übergabe:** <was offen ist, wer es tut>. Anlegen?“ Nach Ja zwei Schritte: erst die Aufgabe (`aufgabe-neu --titel "…"`; für Max „Mac: …“; für Silver „Silver: …“ mit `--fuer Max`, weil Silver Max' Aufgaben sieht und Personen Silver heute nichts zuweisen können), dann die Zeile `journal-neu --art uebergabe --ref CB-<neu> --text "…" --beleg "Sitzung Claude Code <Datum>, <Ort/Link>"`. Offen ist nur die Aufgabe; erledigt wird sie in `/aufgaben`.

Antwortet das Tool „noch nicht freigeschaltet“ oder „gibt es im Tool noch nicht“: nichts eintragen, Übergaben wie bisher.
