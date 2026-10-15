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

Danach: `/drop <Text>` wirft ins Wiki, `/wiki <Frage>` fragt es, `/wiki-extract` schlägt vor, was aus deinem Vault ins Wiki gehört. `/aufgaben` arbeitet die eigenen Aufgaben aus dem Tool ab, `/offen` legt am Ende einer Sitzung offene Punkte als Aufgaben an (nur nach Ja), `/ware` liest Bestellungen, Sendungen, Bestand, Bestellplanung und Absatz. Jede Frage bekommt automatisch Wiki-Treffer als Kontext.

## Aufgaben (ab v0.2.0)

`/aufgaben` zeigt die eigenen Aufgaben aus dem Tool und arbeitet sie ab: „was steht an“, „CB-123“, „ist erledigt“, „verschieb auf Freitag“, „leg an: …“. Jede Änderung läuft unter dem Namen, dem der Schlüssel gehört. Neue Aufgaben entstehen nur auf ausdrückliche Anweisung, Löschen geht nur im Tool. Derselbe Schlüssel wie fürs Wiki, keine weitere Einrichtung.

## Offene Punkte (ab v0.4.0)

`/offen` sammelt am Ende einer Sitzung, was dort offen geblieben ist (eigene Zusagen, nächste Schritte, Warten auf andere), prüft mit `aufgaben --suche` auf Dubletten und zeigt eine kurze Liste mit Titel, Person und Frist. Angelegt wird erst nach ausdrücklichem Ja; zu einer schon offenen Aufgabe schlägt es eine Notiz vor. Besteht ein Prompt nur aus einem Abschied („danke, das wars“, „Feierabend!“), erinnert der Kontext-Hook Claude einmal je Sitzung daran; ein Abschiedswort in einer Arbeitsanweisung („Schick das bis morgen an Mats“) zählt nicht. Stempel `~/.cb-brain/offen-angeboten`: eine Zeile je Sitzungs-ID mit Zeitpunkt, Einträge älter als sieben Tage fallen weg. Prüfskript: `/usr/bin/python3 tests/pruefe-offen.py`.

## Ware (ab v0.3.0)

`/ware` liest aus dem Tool, was zur Ware gehört: Bestellungen und ihr Stand („Wo steht PO-049?“), Sendungen zu Amazon, Bestand je Produkt (FBA, Lager, unterwegs), die Bestellplanung und den Absatz auf Amazon und in den Shops. Nur lesen, dieselben Zahlen wie im Tool. Reichweite und Prognose bleiben im Tool (Bestandsprognose), Finanzen (EK, Zahlungen, Cashflow) gibt es über Claude nicht. Derselbe Schlüssel, keine weitere Einrichtung.

## Wenn der Wiki-Kontext fehlt

Der Kontext-Hook blockiert nie und meldet sich nicht, wenn etwas schiefgeht. Was er gefunden hat, steht in `~/.cb-brain/logs/hook.log`, sobald er das Skript nicht laden kann.

## Was liegt wo

- `hooks/hooks.json` · `scripts/brain-context.py`: Kontext-Hook (UserPromptSubmit), nie blockierend, Zeitlimit 6 s (Suche 4 s); startet einmal am Tag das Selbst-Update, erinnert beim Abschied einmal je Sitzung an `/offen`.
- `scripts/selbst-update.py`: Selbst-Update über die `claude`-CLI, läuft losgelöst im Hintergrund.
- `scripts/cbtool.py`: Kern (setup, ping, search, drop, drop-file, aufgaben, aufgabe, aufgabe-neu, aufgabe-aendern, bestellungen, bestellung, sendungen, sendung, bestand, bestellplanung, absatz). Schlüssel in `~/.cb-brain/tool-key`, Tool-Adresse optional in `~/.cb-brain/tool-url` oder `CB_TOOL_URL`.
- `skills/*`: die sieben Befehle.
- `CHANGELOG.md`: was sich je Version geändert hat.
- `CLAUDE-abschnitt.md`: der Abschnitt, den `/wiki-setup` in die CLAUDE.md des Vaults hängt. `/wiki-setup` hängt ihn nur an, wenn er fehlt; wer ihn schon hat, ergänzt die Zeilen zu `/ware`, `/aufgaben` und `/offen` von Hand oder löscht den Abschnitt und ruft `/wiki-setup` erneut auf.

## Neue Version ausliefern

Das Plugin aktualisiert sich selbst (ab v0.3.1): Der Kontext-Hook startet höchstens einmal am Tag im Hintergrund `scripts/selbst-update.py`, das den Marketplace `cleverbrands` neu holt und `claude plugin update cb-brain-client@cleverbrands` aufruft. Nach einem Update sagt Claude es beim nächsten Prompt einmal an; aktiv ist die neue Version ab dem nächsten Start von Claude Code oder nach `/reload-plugins`. Das ist nötig, weil Claude Code den Marketplace trotz Auto-Update nicht zuverlässig neu holt.

Eine Änderung kommt nur an, wenn die Versionsnummer steigt; bei gleicher Nummer meldet `plugin update` „already at the latest version“. Deshalb bei jeder Änderung `version` in `.claude-plugin/plugin.json` und `.claude-plugin/marketplace.json` gleich hochzählen und einen Eintrag in `CHANGELOG.md` schreiben. Wer noch eine Version vor 0.3.1 hat, ruft einmal `claude plugin marketplace update cleverbrands && claude plugin update cb-brain-client@cleverbrands` auf; danach läuft es von selbst.

- Abschalten: Umgebungsvariable `CB_NO_AUTOUPDATE=1`.
- Log: `~/.cb-brain/logs/update.log`, eine Zeile je Lauf (Zeit, Version vorher und nachher, Ergebnis). Wann zuletzt geprüft wurde, steht in `~/.cb-brain/update-check`; Löschen der Datei erzwingt die Prüfung beim nächsten Prompt.

Keine Geheimnisse im Repo. Der Schlüssel entsteht im Tool und liegt nur bei der Person.
