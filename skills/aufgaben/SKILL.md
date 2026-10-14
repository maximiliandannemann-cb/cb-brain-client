---
name: aufgaben
description: Arbeitet die eigenen Aufgaben aus dem CleverBrands-Tool ab. Zeigt, was ansteht, liest eine Aufgabe (CB-123), setzt sie erledigt, verschiebt die Fälligkeit, ändert Prio oder Person, hängt Notizen an und legt auf ausdrückliche Anweisung neue an. Für „was steht an“, „meine Aufgaben“, „CB-123“, „ist erledigt“, „leg an: …“, „verschieb auf Freitag“.
---

# /aufgaben

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Jede Änderung läuft unter dem Namen der Person, der der Schlüssel gehört. IDs (`CB-123`) immer wortwörtlich übernehmen.

## Überblick („was steht an“, „meine Aufgaben“)

1. `aufgaben` ausführen; für andere Personen `--fuer <Name>` oder `--fuer alle`, für Erledigtes `--status erledigt`, für ein Stichwort `--suche <text>`.
2. Die Liste gruppiert zeigen: überfällig, diese Woche, später, ohne Datum. Jede Zeile unverändert, nichts hinzudichten.

## An einer Aufgabe arbeiten („CB-123“)

1. `aufgabe CB-123` lesen.
2. Die eigentliche Arbeit mit den übrigen Werkzeugen der Sitzung erledigen: Firmenwissen über `/wiki`, Mails nur als Entwurf, nie senden.
3. Danach in einem Satz anbieten: „Soll ich das als Notiz an CB-123 hängen?“ Erst nach Ja: `aufgabe-aendern CB-123 --notiz "<ein bis zwei Sätze Ergebnis>"`. Eine Notiz ist ein Ergebnis, kein Protokoll.

## Ändern, nur auf Wort der Person

`aufgabe-aendern CB-123` mit `--erledigt` oder `--offen`, `--faellig YYYY-MM-DD` oder `--faellig-weg`, `--prio 1-4` (niedrig, mittel, hoch, dringend), `--fuer <Name>` oder `--fuer-weg`. Nur ändern, was die Person sagt. Relative Daten („Freitag“, „nächste Woche“) vom heutigen Datum aus in YYYY-MM-DD umrechnen und das Datum im Satz nennen („verschoben auf Fr 16.10.“). Die Ausgabe in einem Satz wiedergeben.

## Anlegen, nur auf ausdrückliche Anweisung

Nur wenn die Person es verlangt („leg an“, „mach eine Aufgabe“): `aufgabe-neu --titel "<titel>" [--beschreibung "<text>"] [--fuer <Name>] [--faellig YYYY-MM-DD] [--prio 1-4]`. Ohne `--fuer` gehört sie der Person selbst. Nie von sich aus Aufgaben anlegen und keine Aufgabenlisten aus Mails, Meetings oder Notizen vorschlagen (Firmenregel: keine KI-Aufgaben).

## Fehler und Grenzen

- Nennt die Ausgabe „Kein Konto …“ mit einer Liste möglicher Namen: den passenden Namen bei der Person erfragen, nicht raten.
- Löschen geht nur im Tool; dafür den Link aus `aufgabe CB-123` nennen.
