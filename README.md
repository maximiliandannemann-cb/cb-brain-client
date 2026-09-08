# cb-brain-client

Claude-Code-Plugin für das CleverBrands-Wiki. Spricht nur mit dem Tool (`company-interface`), kein GitHub-Konto, kein weiterer Login.

## Einrichten (drei Schritte, aus dem Tool heraus)

1. Im Tool: Wiki › **Verbinden** › Schlüssel erzeugen.
2. Im Terminal, im Ordner deines Vaults:

   ```
   claude plugin marketplace add maximiliandannemann-cb/cb-brain-client && claude plugin install cb-brain-client@cleverbrands
   ```

3. In Claude Code: `/wiki-setup <schlüssel>`.

Danach: `/drop <Text>` wirft ins Wiki, `/wiki <Frage>` fragt es, `/wiki-extract` schlägt vor, was aus deinem Vault ins Wiki gehört. Jede Frage bekommt automatisch Wiki-Treffer als Kontext.

## Was liegt wo

- `hooks/hooks.json` · `scripts/brain-context.py`: Kontext-Hook (UserPromptSubmit), nie blockierend, Zeitlimit 2,5 s.
- `scripts/cbtool.py`: Kern (setup, ping, search, drop, drop-file). Schlüssel in `~/.cb-brain/tool-key`, Tool-Adresse optional in `~/.cb-brain/tool-url` oder `CB_TOOL_URL`.
- `skills/*`: die vier Befehle.
- `CLAUDE-abschnitt.md`: der Abschnitt, den `/wiki-setup` in die CLAUDE.md des Vaults hängt.

Keine Geheimnisse im Repo. Der Schlüssel entsteht im Tool und liegt nur bei der Person.
