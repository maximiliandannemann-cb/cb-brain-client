---
name: wiki-setup
description: Verbindet Claude Code mit dem CleverBrands-Wiki. Prüft den persönlichen Schlüssel aus dem Tool (Wiki › Verbinden), speichert ihn unter ~/.cb-brain/tool-key und ergänzt den Abschnitt „CleverBrands-Wiki“ in der CLAUDE.md des aktuellen Ordners. Auch zum Prüfen der Verbindung ohne Argument.
---

# /wiki-setup

Argument: der Schlüssel aus dem Tool (`cbw_…`), optional gefolgt von der Adresse des Tools (nur wenn die Onboarding-Seite sie mit anzeigt, also auf einer Vorschau). Ohne Argument: nur die Verbindung prüfen.

## Schritte

1. Mit Schlüssel: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" setup <schlüssel> [adresse]` ausführen (Argumente unverändert durchreichen). Die Ausgabe nennt den Namen des Kontos; bei einem Fehler die Meldung wörtlich wiedergeben und abbrechen.
2. Ohne Schlüssel: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" ping`.
3. Prüfen, ob die `CLAUDE.md` im aktuellen Ordner den Abschnitt `## CleverBrands-Wiki` enthält. Wenn nicht, den Inhalt von `${CLAUDE_PLUGIN_ROOT}/CLAUDE-abschnitt.md` ans Ende anhängen (Datei anlegen, falls sie fehlt). Nichts anderes in der Datei ändern.
4. Kurz melden: verbunden als wer, Abschnitt ergänzt ja/nein, und dass die Onboarding-Seite im Tool den Schritt jetzt abhakt. Nächster Schritt dort: ein erster `/drop`.

Den Schlüssel nie in Dateien außer `~/.cb-brain/tool-key` schreiben und nie in der Antwort wiederholen.
