---
name: journal
description: Betriebs-Journal des CleverBrands-Tools. Liest, was seit einem Zeitpunkt passiert ist (Einträge von Personen, Claude Code und Silver plus Stationen, Termine, Bewegungen, Aufgaben-Wechsel aus dem Tool), zeigt, was für die Person offen ist (Übergaben, Zusagen), quittiert Gesehenes und trägt nach Ja eine Zeile ein. Für „was ist seit gestern passiert“, „was hat Silver gemacht“, „was ist offen für mich“, „Akte PO-032“, „gib das an Silver ab“, Sitzungsende mit Übergabe.
---

# /journal

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Das Journal ist ein Protokoll: eine Zeile je Sache, die passiert ist, mit Verfasser und Beleg. Es ist keine Aufgabe (Arbeit mit Frist gehört nach `/aufgaben`) und kein Wiki (was dauerhaft gilt, geht mit `/drop` ins Wiki).

## Lesen

| Frage | Befehl |
|---|---|
| Was ist seit gestern / seit Montag passiert? | `journal --seit 1d` bzw. `--seit 2026-10-26` (Standard 2d, höchstens 30 Tage) |
| Was hat Silver gemacht? | `journal --von Silver` |
| Was ist offen für mich? | `journal --offen-fuer ich` (Übergaben zuerst, dann Zusagen nach Fälligkeit) |
| Alles zu einer Bestellung, Aufgabe, Einsendung | `journal --ref PO-032` (30 Tage, Anfang der Nummer reicht) |
| Nur Fakten aus dem Tool | `journal --art fakten` |

Antworten kurz: was passiert ist, wer, worauf bezogen. J-Nummern und PO-Nummern wörtlich. Zeilen mit `OFFEN` zuerst nennen.

## Quittieren

`journal --quittieren J-1234` nur, wenn die Person die Übergabe wirklich gesehen hat (sie hat sie gelesen oder ausdrücklich „gesehen“, „ok“ gesagt). Nie automatisch alle quittieren. Quittieren darf, für wen die Zeile offen ist, und Max.

## Eintragen (nur nach Ja)

Eine Zeile je Handlung mit Außenwirkung: Mail verschickt oder Entwurf angelegt, Nachfass-Mail, Entscheidung von Max entgegengenommen, Zusage gemacht oder bekommen, Übergabe an jemand anderen. Lesen, Suchen, Rechnen sind keine Zeilen. Vorschlag zeigen, nach Ja eintragen:

`journal-neu --art ereignis|entscheidung|zusage|uebergabe --text "<ein bis zwei Sätze>" --beleg "<woher, mit Link>" [--ref PO-032] [--fuer <name>] [--faellig YYYY-MM-DD] [--bereich <b>]`

- `--text`: was passiert ist, Ort und Beleg nennen, nicht den Inhalt einer Mail kopieren (10 bis 1.000 Zeichen).
- `--beleg`: ein Satz, woher die Information kommt, mit Link, wo es einen gibt (10 bis 500). Nie erfinden.
- `uebergabe` braucht `--fuer` (bleibt offen, bis der Empfänger quittiert); `zusage` braucht `--faellig`.
- `--ref` mit der Nummer, wo es eine gibt (PO, CB, IN, J); Mail-Threads mit `--ref <thread-id> --ref-art mail`.
- `--bereich` (Standard `allgemein`): `supply_chain`, `sales`, `finanzen`, `team`, `privat`. Finanzen sieht Silver nicht.
- **Nie von Hand:** Aufgaben-Ereignisse (angelegt, erledigt, zugewiesen, Frist, wartet) schreibt das Tool selbst; Stationen, Termine, Wareneingänge stehen über ihre Buchung im Journal. Zusatzinfo zu einer Aufgabe ist eine Notiz (`aufgabe-aendern CB-123 --notiz`). Freigaben (`freigabe`) schreibt nur eine Tür des Tools.
- Ein wiederholter Befehl am selben Tag schreibt nicht doppelt („Schon eingetragen“).

## Sitzungsende

Am Ende einer Sitzung mit Firmenbezug eine Übergabe vorschlagen: „**Übergabe an Silver:** <was offen ist, was Silver tun soll>. Eintragen?“ Nach Ja `journal-neu --art uebergabe --fuer Silver --text "…" --beleg "Sitzung Claude Code <Datum>, <Ort/Link>"`. Was Arbeit mit Frist braucht, wird zusätzlich eine Aufgabe (`/aufgaben`), und die Übergabe nennt sie (`--ref CB-123`). Nie beides für dieselbe Arbeit ohne Bezug.

Antwortet das Tool „noch nicht freigeschaltet“ oder „gibt es im Tool noch nicht“: nichts eintragen, Übergaben wie bisher.
