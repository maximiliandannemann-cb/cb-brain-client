# Changelog

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
