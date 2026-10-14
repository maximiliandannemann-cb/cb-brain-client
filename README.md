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

Danach: `/drop <Text>` wirft ins Wiki, `/wiki <Frage>` fragt es, `/wiki-extract` schlägt vor, was aus deinem Vault ins Wiki gehört. `/aufgaben` arbeitet die eigenen Aufgaben aus dem Tool ab, `/ware` liest Bestellungen, Sendungen, Bestand, Bestellplanung und Absatz. Jede Frage bekommt automatisch Wiki-Treffer als Kontext.

## Aufgaben (ab v0.2.0)

`/aufgaben` zeigt die eigenen Aufgaben aus dem Tool und arbeitet sie ab: „was steht an“, „CB-123“, „ist erledigt“, „verschieb auf Freitag“, „leg an: …“. Jede Änderung läuft unter dem Namen, dem der Schlüssel gehört. Neue Aufgaben entstehen nur auf ausdrückliche Anweisung, Löschen geht nur im Tool. Derselbe Schlüssel wie fürs Wiki, keine weitere Einrichtung.

## Ware (ab v0.3.0)

`/ware` liest aus dem Tool, was zur Ware gehört: Bestellungen und ihr Stand („Wo steht PO-049?“), Sendungen zu Amazon, Bestand je Produkt (FBA, Lager, unterwegs), die Bestellplanung und den Absatz auf Amazon und in den Shops. Nur lesen, dieselben Zahlen wie im Tool. Reichweite und Prognose bleiben im Tool (Bestandsprognose), Finanzen (EK, Zahlungen, Cashflow) gibt es über Claude nicht. Derselbe Schlüssel, keine weitere Einrichtung.

## Wenn der Wiki-Kontext fehlt

Der Kontext-Hook blockiert nie und meldet sich nicht, wenn etwas schiefgeht. Was er gefunden hat, steht in `~/.cb-brain/logs/hook.log`, sobald er das Skript nicht laden kann.

## Was liegt wo

- `hooks/hooks.json` · `scripts/brain-context.py`: Kontext-Hook (UserPromptSubmit), nie blockierend, Zeitlimit 2,5 s.
- `scripts/cbtool.py`: Kern (setup, ping, search, drop, drop-file, aufgaben, aufgabe, aufgabe-neu, aufgabe-aendern, bestellungen, bestellung, sendungen, sendung, bestand, bestellplanung, absatz). Schlüssel in `~/.cb-brain/tool-key`, Tool-Adresse optional in `~/.cb-brain/tool-url` oder `CB_TOOL_URL`.
- `skills/*`: die sechs Befehle.
- `CHANGELOG.md`: was sich je Version geändert hat.
- `CLAUDE-abschnitt.md`: der Abschnitt, den `/wiki-setup` in die CLAUDE.md des Vaults hängt. `/wiki-setup` hängt ihn nur an, wenn er fehlt; wer ihn schon hat, ergänzt die Zeile zu `/ware` und `/aufgaben` von Hand oder löscht den Abschnitt und ruft `/wiki-setup` erneut auf.

Keine Geheimnisse im Repo. Der Schlüssel entsteht im Tool und liegt nur bei der Person.
