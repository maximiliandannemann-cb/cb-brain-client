# Changelog

## 0.8.0 (22.10.2026)

- Neu: `--ergebnis "<satz>"` bei `aufgabe-aendern CB-123 --erledigt` und bei `erledigt --titel … --groesse …`. Ein Satz, was herauskam und wo es liegt, mit Link zum Beleg, wo es einen gibt; 10 bis 2000 Zeichen (Umbrüche werden Leerzeichen, gezählt wie im Tool). Grund: Ab Mo 26.10.2026 00:00 Berlin wird im Tool keine Aufgabe ohne Ergebnis erledigt, auf keinem Weg (Tool-Issue #437).
- Ab dem Stichtag lehnt das Skript Erledigen ohne `--ergebnis` selbst ab, mit dem Text des Tools („Ergebnis fehlt: ein Satz, was herauskam und wo es liegt (mind. 10 Zeichen).“), und sendet nichts. Maßgeblich bleibt das Tool; antwortet es so, sagt das Skript, was zu tun ist. `--ergebnis` allein ändert das Ergebnis einer erledigten Aufgabe; mit `--offen` geht es nicht (wieder öffnen lässt das Ergebnis stehen).
- `aufgabe CB-123` zeigt „Ergebnis: …“, `aufgaben --status erledigt` zeigt es unter jeder erledigten Aufgabe.
- `/erledigt`, `/aufgaben`: Beim Abschließen schlägt Claude einen Satz Ergebnis vor und sucht den Beleg-Link selbst (PR über `gh`, Mail über die Composio-CLI mit dem Konto der Sitzung, Drive-Link). Geschrieben wird erst nach Ja; ohne gefundenen Link reicht der Satz, ein Link wird nie erfunden. `/offen` setzt nichts erledigt und verweist auf `/erledigt`.
- Kontext-Hook und CLAUDE-Abschnitt nennen die Regel in einem Satz.
- Prüfskript `tests/pruefe-ergebnis.py` (ohne Framework, ohne Netz, Uhr fest): fehlt vor und ab Stichtag, zu kurz, nur Leerraum, zu lang, 10 Zeichen, Emoji, Bodies, 400 des Tools, Anzeige. `tests/pruefe-erledigt.py` läuft mit Uhr vor dem Stichtag, damit es nach dem 26.10. grün bleibt.
- Braucht das Tool mit der Spalte `ergebnis` (company-interface PR #442); davor lehnt das Tool das Feld `ergebnis` ab. Ohne `--ergebnis` schicken die Befehle denselben Body wie bisher.

## 0.7.0 (20.10.2026)

- Neu: `/erledigt` und `cbtool.py erledigt --titel "…" --groesse klein|mittel|gross [--notiz "…"]`. Trägt abgeschlossene Arbeit für die Person selbst ins Tool ein (POST mit `erledigt: true`, ohne Person und ohne Frist). Grund: Die Bruno-Punkte zählen ab 20.10.2026 jede erledigte Aufgabe nach Größe (klein 1, mittel 3, groß 5; ohne Größe = mittel), auch Arbeit, die vorher keine Aufgabe war (Ads, Bugfixes, Creative Direction).
- Verhalten: Ist ein Arbeitsschritt abgeschlossen (gemergt, verschickt, fertig, entschieden), schlägt Claude am Ende der Antwort einen Eintrag vor: „**Erledigt:** <Titel> (<Größe>). Eintragen?“ Größe schätzt Claude nach der Arbeitszeit. Eingetragen nur nach Ja; gibt es eine offene Aufgabe dazu, wird diese erledigt gesetzt statt neu angelegt. Nicht für Kleinkram unter etwa 15 Minuten, nicht zweimal für denselben Schritt. Zeile in `CLAUDE-abschnitt.md`. Damit die Regel auch bei einem älteren Abschnitt ankommt, gibt der Kontext-Hook sie einmal je Sitzung als Hinweis mit (kein Netz, Fehler enden still; Stempel `~/.cb-brain/erledigt-regel`, Sitzungs-IDs mit Zeitpunkt, älter als sieben Tage fallen weg; ohne Sitzungs-ID oder Schlüssel kein Hinweis).
- `aufgabe-neu` und `aufgabe-aendern` kennen `--groesse` (auch „groß“). Eine falsche Größe ist ein Bedienfehler, nichts wird gesendet. `aufgabe CB-123` zeigt die Größe.
- Prüfskript `tests/pruefe-erledigt.py` (ohne Framework, ohne Netz): Body nach Vertrag, falsche Größe abgelehnt, 403 des Tools unverändert, Hook-Hinweis einmal je Sitzung.
- Braucht das Tool mit der Spalte `groesse`; davor lehnt das Tool die Felder `groesse` und `erledigt` beim Anlegen ab.

## 0.6.1 (20.10.2026)

- Kaffeekasse: Gezahlt wird per PayPal an info@cleverbrands.de (Firmenkonto), nicht an Mats; das gilt für alle, auch für Mats (Max 20.10.). `/kasse` übernimmt den Empfänger vom Screenshot und nennt eine Abweichung, wenn er weder info@cleverbrands.de noch CleverBrands ist. Kassenwart bleibt Mats, für seine Beträge Max.

## 0.6.0 (16.10.2026)

- Neu: `/kasse` für die Bruno-Kaffeekasse und vier Befehle in `cbtool.py`: `kasse` (Stand: fällig mit Zinsen, noch nicht fällig, heute, nächste 12:00, eigene Meldungen, für den Kassenwart „Zu prüfen“), `kasse-melden --betrag 6,60 --datum YYYY-MM-DD --empfaenger <name> [--fuer <name>]`, `kasse-widersprechen --meldung <nr> --grund <text>`, `kasse-erlassen --fuer <name> --tag YYYY-MM-DD [--bis YYYY-MM-DD] --grund <text>`. Grund: Ab 20.10.2026 ist werktags um 12:00 fällig, was am Vortag aufgelaufen ist; gemeldet wird in Claude Code.
- Das Tool rechnet und entscheidet alles (Beträge in Cent, Fälligkeit, Zinsen, wer widersprechen oder erlassen darf). Das Plugin zeigt die Antwort und die Meldung des Tools unverändert. Der Body enthält nur gesetzte Felder; Betrag, Datum, Empfänger und Grund werden vor dem Senden geprüft.
- Screenshot: Claude liest Betrag, Datum und Empfänger selbst ab und übergibt nur diese Angaben. Das Skript liest keine Bilder, nimmt keine Dateien, und das Bild wird nie hochgeladen oder gespeichert. Eine Abweichung zum Fälligen nennt Claude vor der Frage; gemeldet wird nur nach ausdrücklichem Ja.
- Kontext-Hook: Mo bis Fr 08:00 bis 18:59 (Berlin) fragt er höchstens alle 15 Minuten beim Tool nach (`GET /api/brain-read/kasse`, Zeitlimit 1,5 s) und zeigt dessen fertigen Satz höchstens einmal je Stunde: dem Zahler ab 12:00, wenn etwas fällig ist, dem Kassenwart ab 08:00, wenn eine Meldung wartet. Nach einer Meldung liefert das Tool keinen Satz mehr, der Hinweis endet. Außerhalb des Fensters kein Netz. Fehler, Zeitlimit und ein Tool ohne Kasse (404) enden still. Stempel `~/.cb-brain/kasse-hinweis` („gefragt<TAB>gezeigt“, atomar), parallele Sitzungen teilen ihn.
- Zeitbudget des Hooks: Die Wiki-Suche bekommt, was nach der Kasse übrig ist (zusammen höchstens 5,4 s, Grenze 6 s). Gemessen mit `/usr/bin/python3` gegen einen lokalen Stub: 0,26 s ohne Verzögerung, 2,2 s mit kalter Suche, 5,5 s im schlimmsten Fall (Kasse und Suche hängen).
- Prüfskript `tests/pruefe-kasse.py` (ohne Framework, ohne Netz): Betrag, Bodies, lokale Fehler, Antworten 200/201/400/401/403/404/409, Hook-Fenster, Stempel, Zeitbudget.
- Braucht das Tool mit der Kasse (company-interface PR #377); davor sagen die Befehle „Die Kasse ist im Tool noch nicht da.“ und der Hook schweigt.

## 0.5.0 (15.10.2026)

- `aufgabe-aendern` kennt `--grund "<text>"`: ein Satz, warum sich eine bestehende Frist ändert oder wegfällt. Nur zusammen mit `--faellig` oder `--faellig-weg`, 1 bis 300 Zeichen (Zeilenumbrüche werden Leerzeichen, wie im Tool). Ohne `--grund` schickt der Befehl genau denselben Body wie bisher. Grund: Das Tool nimmt ab 19.10.2026 eine Friständerung nur mit Grund an; er steht danach im Verlauf der Aufgabe.
- Antwortet das Tool „Bitte kurz begründen, warum die Frist sich ändert.“, sagt der Befehl das klar und nennt `--grund` als nächsten Schritt.
- `/aufgaben`: Vor dem Verschieben oder Entfernen einer bestehenden Frist fragt Claude die Person nach einem Satz Grund und übergibt ihn wörtlich. Claude formuliert keinen Grund selbst. Erstes Setzen einer Frist braucht keinen. `/offen` verschiebt keine Fristen und verweist dafür auf `/aufgaben`.
- Prüfskript `tests/pruefe-grund.py` (ohne Framework, ohne Netz): Body mit und ohne `--grund`, lokale Längenprüfung, Meldung bei fehlendem Grund.
- Braucht das Tool mit der Erweiterung vom 15.10.2026; das Tool davor lehnt das Feld `grund` ab.

## 0.4.0 (15.10.2026)

- Neu: `/offen`. Am Ende einer Sitzung schlägt Claude vor, was dort offen geblieben ist (eigene Zusagen, nächste Schritte, Warten auf andere), als Aufgaben ins Tool zu legen: kurze Liste mit Titel („Produkt: Tätigkeit“), Person und Frist, Dublettenprüfung mit `aufgaben --suche`, bei vorhandener Aufgabe eine Notiz statt Neuanlage. Angelegt wird nur nach ausdrücklichem Ja, ohne Frist nichts. Grund: Zusagen aus Claude-Sitzungen sollen im Tool landen, auch wenn niemand sie von Hand anlegt.
- Kontext-Hook: Besteht ein Prompt (höchstens 80 Zeichen) nur aus einem Abschied („danke, das wars“, „ok, fertig für heute“, „Feierabend!“, „tschüss“), erinnert er Claude einmal je Sitzung an `/offen`. Abschiedswörter in Arbeitsanweisungen („Schick das bis morgen an Mats“) lösen nichts aus. Claude bietet nur an, wenn wirklich etwas offen ist, und nach einem Nein nicht wieder. Stempel `~/.cb-brain/offen-angeboten`: Sitzungs-IDs mit Zeitpunkt, sieben Tage, parallele Sitzungen stören sich nicht. Ohne Schlüssel oder Sitzungs-ID kein Hinweis.
- `/offen` schlägt Aufgaben nur für die Person selbst vor; Warten auf andere wird eine eigene Nachfass-Aufgabe. Fristen nur, wenn die Person sie genannt hat, sonst fragt Claude.
- Prüfskript `tests/pruefe-offen.py` (ohne Framework, ohne Netz): Abschiede, Fehlauslöser, Stempel.
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
