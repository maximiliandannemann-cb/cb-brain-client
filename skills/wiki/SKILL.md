---
name: wiki
description: Fragt das CleverBrands-Wiki und antwortet mit Quellenangabe (Seite und Form). Für Fragen wie „Was war da mit Gechem?“, „Wie buchen wir Wareneingang?“, „Warum haben wir Flieber behalten?“. Nutzt nur, was im Wiki steht.
---

# /wiki

Argument: eine Frage oder ein Begriff.

## Schritte

1. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" search "<frage>" 6` ausführen. Das Ergebnis ist JSON mit `title`, `slug`, `type`, `source`, `snippet`.
2. Aus den Treffern antworten, in zwei bis fünf Sätzen, nur mit dem, was in den Ausschnitten steht. Nichts ergänzen, was nicht im Wiki steht; fehlt es, sagen „Dazu steht nichts im Wiki“ und einen `/drop` vorschlagen.
3. Unter der Antwort die Quellen als Liste: `Titel (Form) · https://company-interface.vercel.app/wissen/<slug>`; Treffer mit `source: tool` als „im Tool“ kennzeichnen.
