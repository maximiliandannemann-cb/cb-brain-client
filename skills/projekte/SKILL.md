---
name: projekte
description: Liest die Projekt-Akte des CleverBrands-Tools (Projekte, Stand, wer dran ist, Schritte, Bezüge) und bucht auf Wort der Person Zuordnungen und Schritte. Für „welche Projekte laufen“, „P-6“, „wo steht Projekt X“, „zu welchem Projekt gehört PO-032“, „ordne CB-218 dem Projekt zu“, „S-412 erledigt“, „übernimm S-412“.
---

# /projekte

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Nummern (P-n, S-n, CB-n, PO, SKU) wörtlich aus der Ausgabe, die `Stand:`-Zeile nennen.

| Frage | Befehl |
|---|---|
| Welche Projekte gibt es, wer ist dran? | `projekte` |
| Was hängt, was ist neu? | `projekte --ausnahmen`, `projekte --neu-seit YYYY-MM-DD` |
| Zu welchem Projekt gehört das? | `projekte --ref CB-345` (auch PO, IN, SKU) |
| Ein Projekt | `projekt P-6`, alle Schritte mit `--schritte-alle` |
| Zuordnen oder lösen | `projekt-bezug P-6 --aufgabe CB-218 --beleg "<satz>"`, lösen mit `--loesen` |
| Schritte anlegen | `projekt-schritte P-6 --art <art> --titel "<ergebnis>" --beleg "<satz>"`, viele mit `--liste <datei>` |
| Fehlende Pflichtpunkte nachziehen | `projekt-schritte P-6 --pflichtpunkte --beleg "<satz>"` |
| Schritt buchen | `schritt-aktion S-412 --aktion beginnen --beleg "<satz>"` |
| Schritt übernehmen | `schritt-uebernehmen S-412 --fuer <name> --frist YYYY-MM-DD --beleg "<satz>"` |

Alle Felder: `projekt-bezug --help`.

## Schreiben

Nur auf Wort der Person. Erst ohne `--ausfuehren` (Vorschau, nichts geschrieben), Vorschau zeigen, nach Ja derselbe Befehl mit `--ausfuehren`. `--beleg` ist ein Satz mit Fundstelle. Nummern einer Vorschau sind nicht endgültig, und eine Vorschau mit neuen Schritten oder Aufgaben überspringt Nummern; deshalb nicht wiederholt ausprobieren.

Ein Bot hakt Schritte mit `--freigabe-von <person> --freigabe-beleg <mail-id, J-n oder Slack-Link>` ab. Die Freigabe muss es wirklich geben: nie erfinden, sonst nachfragen.

## Fehler

Die Meldung des Tools wörtlich weitergeben und nicht anders versuchen, vor allem bei einer Sperre. „Schon eingetragen“ heißt: derselbe Befehl lief schon. Soll es bewusst eine neue Buchung sein (etwa nach `wieder_offen`), einen neuen Beleg oder `--schluessel` nehmen.
