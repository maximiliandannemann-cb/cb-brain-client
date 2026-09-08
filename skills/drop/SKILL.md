---
name: drop
description: Wirft Wissen ins CleverBrands-Wiki. Text oder Dateien (.md/.txt) landen in der Inbox des Firmen-Wikis unter dem Namen des Nutzers; der Ingest sortiert sie nachts in die passende Seite ein. Nutzen, wenn etwas passiert ist, das ein Kollege in drei Monaten wissen muss.
---

# /drop

Argument: Freitext, ein oder mehrere Dateipfade (.md, .txt), oder das Wort `session` für einen Auszug der laufenden Sitzung.

## Schritte

0. Ist das Argument `session` (oder „Sitzung“, „alles von heute“): Schreibe einen **Sitzungsauszug** aus dem bisherigen Gesprächsverlauf, kein Protokoll. Aufnehmen: Entscheidungen mit Grund, Fakten (Zahlen, Namen, Daten wortwörtlich), Zusagen von Lieferanten oder Partnern, Fehler und was daraus folgt, Ergebnisse von Analysen. Weglassen: Zwischenstände, Versuche ohne Ergebnis, Werkzeug- und Codefragen ohne Firmenbezug, Privates, Gehälter, Gesundheit, Bewertungen von Personen. Form: kurze Absätze in Max' Register, je Sache ein Absatz, zusammen höchstens etwa 300 Wörter; bei mehr als einem Thema je Thema ein eigener `/drop`. Zeige den Auszug und frage „So einwerfen?“. Erst nach Zustimmung weiter mit Schritt 3, dabei den Text unverändert einwerfen und `session` als Quelle nennen.
1. Ist das Argument leer, fragen: „Was soll ins Wiki?“ und auf die Antwort warten.
2. Enthält das Argument Dateipfade, die existieren: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" drop-file <pfad> [...]`.
3. Sonst den Text so einwerfen, wie er ist, ohne Umformulieren: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" drop "<text>"`. Zahlen, Namen, Daten wortwörtlich lassen.
4. Die Ausgabe (Inbox-Pfad) in einem Satz wiedergeben. Nicht erklären, wie der Ingest funktioniert.

Was ins Wiki gehört: Zusagen von Lieferanten, Preise und Lieferzeiten, Entscheidungen mit Begründung, Fehler die Geld gekostet haben, Ergebnisse von Gesprächen und Analysen. Was nicht: Privates, Zwischenstände ohne Ergebnis, Passwörter oder Schlüssel.
