---
name: aufgaben
description: Arbeitet die eigenen Aufgaben aus dem CleverBrands-Tool ab. Zeigt, was ansteht, liest eine Aufgabe (CB-123), setzt sie erledigt (mit Ergebnis), verschiebt die Fälligkeit, ändert Prio oder Person, hängt Notizen an und legt auf ausdrückliche Anweisung neue an. Für „was steht an“, „meine Aufgaben“, „CB-123“, „ist erledigt“, „leg an: …“, „verschieb auf Freitag“.
---

# /aufgaben

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Jede Änderung läuft unter dem Namen der Person, der der Schlüssel gehört. IDs (`CB-123`) immer wortwörtlich übernehmen.

## Überblick („was steht an“, „meine Aufgaben“)

1. `aufgaben` ausführen; für andere Personen `--fuer <Name>` oder `--fuer alle`, für Erledigtes `--status erledigt` (zeigt das Ergebnis unter der Zeile), für ein Stichwort `--suche <text>`.
2. Die Liste gruppiert zeigen: überfällig, diese Woche, später, ohne Datum. Jede Zeile unverändert, nichts hinzudichten.

## An einer Aufgabe arbeiten („CB-123“)

1. `aufgabe CB-123` lesen.
2. Die eigentliche Arbeit mit den übrigen Werkzeugen der Sitzung erledigen: Firmenwissen über `/wiki`, Mails nur als Entwurf, nie senden.
3. Danach in einem Satz anbieten: „Soll ich das als Notiz an CB-123 hängen?“ Erst nach Ja: `aufgabe-aendern CB-123 --notiz "<ein bis zwei Sätze Ergebnis>"`. Eine Notiz ist ein Ergebnis, kein Protokoll.

## Ändern, nur auf Wort der Person

`aufgabe-aendern CB-123` mit `--erledigt` oder `--offen`, `--faellig YYYY-MM-DD` oder `--faellig-weg` (bei bestehender Frist mit `--grund`, siehe unten), `--prio 1-4` (niedrig, mittel, hoch, dringend), `--fuer <Name>` oder `--fuer-weg`, `--groesse klein|mittel|gross` (nur eigene Aufgaben). Nur ändern, was die Person sagt. Relative Daten („Freitag“, „nächste Woche“) vom heutigen Datum aus in YYYY-MM-DD umrechnen und das Datum im Satz nennen („verschoben auf Fr 16.10.“). Die Ausgabe in einem Satz wiedergeben.

### Erledigt setzen: nur mit Ergebnis (Pflicht ab Mo 26.10.2026)

1. Einen Satz vorschlagen, was herauskam und wo es liegt, mit Beleg-Link, den Claude selbst sucht: PR über `gh pr view` / `gh pr list --search`, Mail über die Composio-CLI mit dem Konto dieser Sitzung (Link aus der Thread-ID), Drive-Link aus der Sitzung oder der Drive-Suche. Nie einen Link erfinden; ohne Fund reicht der Satz. Nummern wörtlich.
2. Erst nach Ja der Person (mit ihren Änderungen): `aufgabe-aendern CB-123 --erledigt --ergebnis "<satz mit link>"`.
3. Ein Ergebnis an einer schon erledigten Aufgabe ändern: `aufgabe-aendern CB-123 --ergebnis "<satz>"`. Wieder öffnen (`--offen`) lässt das Ergebnis stehen; beim nächsten Erledigen kommt ein neuer Satz.
4. Antwortet das Skript „Ergebnis fehlt: …“: die Person nach dem Ergebnis fragen und wiederholen. `aufgabe CB-123` zeigt ein vorhandenes Ergebnis.

### Frist verschieben oder entfernen: nur mit Grund der Person

Hat die Aufgabe schon eine Frist (`aufgabe CB-123` zeigt „Fällig“) und soll sie sich ändern oder wegfallen, braucht das Tool einen Satz Grund (Pflicht ab 19.10.2026).

1. Vor dem Aufruf die Person fragen: „Warum verschiebt sich CB-123? Ein Satz reicht.“ Hat sie den Grund in der Sitzung schon selbst genannt („verschieb auf Freitag, der Lieferant ist krank“), gilt dieser.
2. Den Grund wörtlich übergeben: `aufgabe-aendern CB-123 --faellig YYYY-MM-DD --grund "<Satz der Person>"` (oder `--faellig-weg --grund "…"`). Höchstens 300 Zeichen.
3. Den Grund nie selbst formulieren, umschreiben, ergänzen oder aus dem Zusammenhang erraten. Ohne Grund der Person wird nicht verschoben.

Erstes Setzen einer Frist (die Aufgabe hatte keine) braucht keinen Grund. Antwortet das Tool „Bitte kurz begründen, warum die Frist sich ändert.“, die Person nach dem Grund fragen und den Aufruf mit `--grund` wiederholen.

## Anlegen, nur auf ausdrückliche Anweisung

Nur wenn die Person es verlangt („leg an“, „mach eine Aufgabe“): `aufgabe-neu --titel "<titel>" [--beschreibung "<text>"] [--fuer <Name>] [--faellig YYYY-MM-DD] [--prio 1-4] [--groesse klein|mittel|gross]`. Größe nur, wenn die Person sie nennt oder Claude sie nach der Arbeitszeit schätzen kann (klein unter 1 Stunde, mittel etwa ein halber Tag, groß ab einem Tag); ohne zählt sie wie mittel. Ohne `--fuer` gehört sie der Person selbst. Nie von sich aus Aufgaben anlegen und keine Aufgabenlisten aus Mails, Meetings oder Notizen vorschlagen (Firmenregel: keine KI-Aufgaben). Ausnahmen: `/offen` bietet am Ende einer Sitzung an, was dort offen geblieben ist, und `/erledigt` schlägt vor, abgeschlossene Arbeit einzutragen; beide legen erst nach Ja an.

## Fehler und Grenzen

- Namen für `--fuer` gehen auch als eindeutige Kurzform ab drei Zeichen („Max“, „Mau“).
- Endet die Ausgabe mit „Möglich: <Namen>“: den passenden Namen bei der Person erfragen, nicht raten.
- Löschen geht nur im Tool; dafür den Link aus `aufgabe CB-123` nennen.
