# cb-brain-client

Claude-Code-Plugin für das CleverBrands-Wiki. Spricht nur mit dem Tool (`company-interface`), kein GitHub-Konto, kein weiterer Login.

## Voraussetzung

Python 3.9 oder neuer, also alles, was macOS ab Werk mitbringt. Prüfen mit `python3 --version`. Wenn ein Befehl des Plugins mit einer Python-Meldung abbricht, hilft die Version im Fehlertext weiter; bis v0.1.6 brauchte das Plugin 3.10 und brach auf der macOS-Systemversion 3.9 ab (Issue #1).

## Einrichten (drei Schritte, aus dem Tool heraus)

1. Im Tool: Wiki › **Verbinden** › Schlüssel erzeugen.
2. Im Terminal, im Ordner deines Vaults:

   ```
   claude plugin marketplace add maximiliandannemann-cb/cb-brain-client && claude plugin install cb-brain-client@cleverbrands
   ```

3. In Claude Code: `/wiki-setup <schlüssel>`.

Danach: `/drop <Text>` wirft ins Wiki, `/wiki <Frage>` fragt es, `/wiki-extract` schlägt vor, was aus deinem Vault ins Wiki gehört. `/aufgaben` arbeitet die eigenen Aufgaben aus dem Tool ab, `/offen` legt am Ende einer Sitzung offene Punkte als Aufgaben an (nur nach Ja), `/ware` liest Bestellungen, Sendungen, Bestand, Bestellplanung und Absatz, `/kasse` zeigt die Kaffeekasse und meldet Zahlungen. Jede Frage bekommt automatisch Wiki-Treffer als Kontext.

## Aufgaben (ab v0.2.0)

`/aufgaben` zeigt die eigenen Aufgaben aus dem Tool und arbeitet sie ab: „was steht an“, „CB-123“, „ist erledigt“, „verschieb auf Freitag“, „leg an: …“. Jede Änderung läuft unter dem Namen, dem der Schlüssel gehört. Ändert sich eine bestehende Frist, fragt Claude nach einem Satz Grund und übergibt ihn wörtlich (`aufgabe-aendern CB-123 --faellig YYYY-MM-DD --grund "…"`, Pflicht im Tool ab 19.10.2026, ab v0.5.0). Neue Aufgaben entstehen nur auf ausdrückliche Anweisung, Löschen geht nur im Tool. Derselbe Schlüssel wie fürs Wiki, keine weitere Einrichtung.

## Offene Punkte (ab v0.4.0)

`/offen` sammelt am Ende einer Sitzung, was dort offen geblieben ist (eigene Zusagen, nächste Schritte, Warten auf andere), prüft mit `aufgaben --suche` auf Dubletten und zeigt eine kurze Liste mit Titel, Person und Frist. Angelegt wird erst nach ausdrücklichem Ja; zu einer schon offenen Aufgabe schlägt es eine Notiz vor. Besteht ein Prompt nur aus einem Abschied („danke, das wars“, „Feierabend!“), erinnert der Kontext-Hook Claude einmal je Sitzung daran; ein Abschiedswort in einer Arbeitsanweisung („Schick das bis morgen an Mats“) zählt nicht. Stempel `~/.cb-brain/offen-angeboten`: eine Zeile je Sitzungs-ID mit Zeitpunkt, Einträge älter als sieben Tage fallen weg.

Prüfskripte (ohne Framework, ohne Netz, macOS-Python 3.9): `/usr/bin/python3 tests/pruefe-offen.py` und `/usr/bin/python3 tests/pruefe-grund.py` (Body von `aufgabe-aendern` mit und ohne `--grund`), `/usr/bin/python3 tests/pruefe-kasse.py` (Kasse).

## Kaffeekasse (ab v0.6.0)

`/kasse` zeigt den eigenen Stand der Bruno-Kaffeekasse (fällig mit Zinsen, noch nicht fällig, nächste 12:00) und meldet eine Zahlung: PayPal an Mats, Screenshot in Claude Code ziehen, „hab eingezahlt“. Claude liest Betrag, Datum und Empfänger selbst ab, nennt eine Abweichung zum Fälligen und meldet erst nach Ja (`kasse-melden --betrag 6,60 --datum YYYY-MM-DD --empfaenger "Mats Mueller"`). Ins Tool geht nur diese eine Zeile; das Bild wird nie hochgeladen oder gespeichert, das Skript liest keine Bilder. Der Kassenwart (Mats, für Mats' Beträge Max) widerspricht (`kasse-widersprechen --meldung 41 --grund "…"`), erlässt Tage (`kasse-erlassen --fuer Jannes --tag YYYY-MM-DD --grund "…"`) oder meldet Barzahlungen für andere (`--fuer`). Wer was darf, entscheidet das Tool.

Der Kontext-Hook zeigt Mo bis Fr höchstens einmal je Stunde den Satz des Tools, wenn ab 12:00 etwas fällig ist oder ab 08:00 eine Meldung auf den Kassenwart wartet; nach der Meldung hört er auf. Er fragt höchstens alle 15 Minuten (Zeitlimit 1,5 s) und außerhalb von 08:00 bis 18:59 gar nicht. Stempel: `~/.cb-brain/kasse-hinweis`. Prüfskript: `/usr/bin/python3 tests/pruefe-kasse.py`.

## Ware (ab v0.3.0)

`/ware` liest aus dem Tool, was zur Ware gehört: Bestellungen und ihr Stand („Wo steht PO-049?“), Sendungen zu Amazon, Bestand je Produkt (FBA, Lager, unterwegs), die Bestellplanung und den Absatz auf Amazon und in den Shops. Nur lesen, dieselben Zahlen wie im Tool. Reichweite und Prognose bleiben im Tool (Bestandsprognose), Finanzen (EK, Zahlungen, Cashflow) gibt es über Claude nicht. Derselbe Schlüssel, keine weitere Einrichtung.

## Wenn der Wiki-Kontext fehlt

Der Kontext-Hook blockiert nie und meldet sich nicht, wenn etwas schiefgeht. Was er gefunden hat, steht in `~/.cb-brain/logs/hook.log`, sobald er das Skript nicht laden kann.

## Was liegt wo

- `hooks/hooks.json` · `scripts/brain-context.py`: Kontext-Hook (UserPromptSubmit), nie blockierend, Zeitlimit 6 s (Kasse 1,5 s, Suche mit dem Rest, höchstens 4 s); startet einmal am Tag das Selbst-Update, erinnert beim Abschied einmal je Sitzung an `/offen`, zeigt höchstens einmal je Stunde den Kassen-Hinweis.
- `scripts/selbst-update.py`: Selbst-Update über die `claude`-CLI, läuft losgelöst im Hintergrund.
- `scripts/cbtool.py`: Kern (setup, ping, search, drop, drop-file, aufgaben, aufgabe, aufgabe-neu, aufgabe-aendern, bestellungen, bestellung, sendungen, sendung, bestand, bestellplanung, absatz, kasse, kasse-melden, kasse-widersprechen, kasse-erlassen). Schlüssel in `~/.cb-brain/tool-key`, Tool-Adresse optional in `~/.cb-brain/tool-url` oder `CB_TOOL_URL`.
- `skills/*`: die acht Befehle.
- `CHANGELOG.md`: was sich je Version geändert hat.
- `CLAUDE-abschnitt.md`: der Abschnitt, den `/wiki-setup` in die CLAUDE.md des Vaults hängt. `/wiki-setup` hängt ihn nur an, wenn er fehlt; wer ihn schon hat, ergänzt die Zeilen zu `/ware`, `/aufgaben`, `/offen` und `/kasse` von Hand oder löscht den Abschnitt und ruft `/wiki-setup` erneut auf.

## Neue Version ausliefern

Das Plugin aktualisiert sich selbst (ab v0.3.1): Der Kontext-Hook startet höchstens einmal am Tag im Hintergrund `scripts/selbst-update.py`, das den Marketplace `cleverbrands` neu holt und `claude plugin update cb-brain-client@cleverbrands` aufruft. Nach einem Update sagt Claude es beim nächsten Prompt einmal an; aktiv ist die neue Version ab dem nächsten Start von Claude Code oder nach `/reload-plugins`. Das ist nötig, weil Claude Code den Marketplace trotz Auto-Update nicht zuverlässig neu holt.

Eine Änderung kommt nur an, wenn die Versionsnummer steigt; bei gleicher Nummer meldet `plugin update` „already at the latest version“. Deshalb bei jeder Änderung `version` in `.claude-plugin/plugin.json` und `.claude-plugin/marketplace.json` gleich hochzählen und einen Eintrag in `CHANGELOG.md` schreiben. Wer noch eine Version vor 0.3.1 hat, ruft einmal `claude plugin marketplace update cleverbrands && claude plugin update cb-brain-client@cleverbrands` auf; danach läuft es von selbst.

- Abschalten: Umgebungsvariable `CB_NO_AUTOUPDATE=1`.
- Log: `~/.cb-brain/logs/update.log`, eine Zeile je Lauf (Zeit, Version vorher und nachher, Ergebnis). Wann zuletzt geprüft wurde, steht in `~/.cb-brain/update-check`; Löschen der Datei erzwingt die Prüfung beim nächsten Prompt.

Keine Geheimnisse im Repo. Der Schlüssel entsteht im Tool und liegt nur bei der Person.
