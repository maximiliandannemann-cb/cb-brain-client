# Changelog

## 0.4.0 (15.10.2026)

- Neu: `/offen`. Am Ende einer Sitzung schlägt Claude vor, was dort offen geblieben ist (eigene Zusagen, nächste Schritte, Warten auf andere), als Aufgaben ins Tool zu legen: kurze Liste mit Titel („Produkt: Tätigkeit“), Person und Frist, Dublettenprüfung mit `aufgaben --suche`, bei vorhandener Aufgabe eine Notiz statt Neuanlage. Angelegt wird nur nach ausdrücklichem Ja, ohne Frist nichts. Grund: Zusagen aus Claude-Sitzungen sollen im Tool landen, auch wenn niemand sie von Hand anlegt.
- Kontext-Hook: Verabschiedet sich die Person in einem kurzen Prompt („danke, das wars“, „fertig für heute“, „Feierabend“, „tschüss“), erinnert er Claude einmal je Sitzung an `/offen`. Claude bietet nur an, wenn wirklich etwas offen ist, und nach einem Nein nicht wieder. Stempel `~/.cb-brain/offen-angeboten` mit der Sitzungs-ID. Ohne Schlüssel kein Hinweis.
- `/aufgaben` nennt `/offen` als einzige Ausnahme von „nie von sich aus vorschlagen“; CLAUDE-Abschnitt, Begrüßung und README nennen `/offen`. Bestehende CLAUDE.md-Abschnitte ergänzt `/wiki-setup` nicht; der Hook-Hinweis wirkt auch ohne.

## 0.3.2 (15.10.2026)

- Begrüßung: Beim ersten Prompt nach dem Verbinden sagt Claude einmal, was jetzt geht (Wiki, /aufgaben, /ware, /drop) und empfiehlt /wiki-setup. Einmal je Schlüssel, Stempel `~/.cb-brain/begruesst` mit einem Hash, nie dem Schlüssel.

## 0.3.1 (15.10.2026)

- Das Plugin aktualisiert sich selbst: Der Kontext-Hook startet höchstens einmal je 24 Stunden losgelöst `scripts/selbst-update.py`, das `claude plugin marketplace update cleverbrands` und `claude plugin update cb-brain-client@cleverbrands` aufruft. Grund: Claude Code holte den Marketplace trotz Auto-Update nicht neu.
- Nach einem Update sagt Claude es beim nächsten Prompt einmal an; aktiv wird die neue Version ab dem nächsten Start von Claude Code oder mit `/reload-plugins`.
- Abschalten mit `CB_NO_AUTOUPDATE=1`. Log: `~/.cb-brain/logs/update.log`.
- Der Hook lädt `cbtool.py` erst, wenn er wirklich sucht; ein kaputtes `cbtool.py` hält das Selbst-Update nicht mehr auf.

## 0.3.0 (14.10.2026)

- Neu: `/ware` und sieben Lesebefehle in `cbtool.py`: `bestellungen`, `bestellung`, `sendungen`, `sendung`, `bestand`, `bestellplanung`, `absatz`. Nur lesen, Bereich Supply Chain und Sales Performance; braucht das Tool mit den Routen unter `/api/brain-read/` (Lesezugang 14.10.2026).
- Ausgabe kompakt: eine Zeile je Objekt, Einzelbefehle mit allen Feldern und Link, Zahlen deutsch, Nummern wörtlich, am Ende immer der Stand der Daten.
- `bestand` fragt 200 Produkte ab (das Tool kürzt sonst bei 50).
- `absatz` markiert Conversion-Werte, die Tage ohne Sitzungen mitzählen (Historie vor 11.07.2026).
- Mehrdeutige Bestellnummer: die möglichen Nummern stehen in der Meldung (höchstens zehn).
- CLAUDE-Abschnitt und README nennen `/ware` und `/aufgaben`. Bestehende CLAUDE.md-Abschnitte ergänzt `/wiki-setup` nicht von selbst.

## 0.2.0 (14.10.2026)

- `/aufgaben` und vier Befehle (`aufgaben`, `aufgabe`, `aufgabe-neu`, `aufgabe-aendern`).

## 0.1.x (08.09. bis 18.09.2026)

- Kontext-Hook, `/drop`, `/wiki`, `/wiki-setup`, `/wiki-extract`; Python 3.9 (0.1.7), Stapel und Zeitlimit für `drop-file` (0.1.8, 0.1.9). Einzelheiten im Git-Log.
