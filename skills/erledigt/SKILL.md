---
name: erledigt
description: Trägt erledigte Arbeit der Person ins CleverBrands-Tool ein, damit sie in den Bruno-Punkten zählt (klein 1, mittel 3, groß 5). Ist in der Sitzung ein Arbeitsschritt abgeschlossen (gemergt, verschickt, fertig, entschieden), am Ende der Antwort EINEN Eintrag vorschlagen: „**Erledigt:** <Titel> (<Größe>). Eintragen?“ Eintragen erst nach Ja. Auch für „hab heute 6 Ads fertig“, „trag ein, dass …“, „/erledigt“.
---

# /erledigt

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Eingetragen wird nur für die Person selbst, nie für andere (das Tool lehnt es ab).

## Wann vorschlagen

- Ein Arbeitsschritt der Person ist in dieser Sitzung abgeschlossen: ein PR gemergt, eine Mail verschickt, eine Vorlage fertig, eine Entscheidung getroffen, ein Bug behoben. Dann ans Ende der Antwort genau eine Zeile:
  `**Erledigt:** ImmunVital: Welcome Flow in Klaviyo (mittel). Eintragen?`
- Die Person erzählt von Arbeit ohne Claude („hab heute 6 Ads fertig“): genauso vorschlagen.
- Nicht für Kleinkram unter etwa 15 Minuten, nicht für Zwischenschritte, nicht für Arbeit anderer. Je Arbeitsschritt nur einmal vorschlagen; nach Nein oder ohne Antwort nicht wieder für denselben Schritt.
- Neben einem `/drop`-Vorschlag steht der Erledigt-Vorschlag als eigene Zeile darunter.

## Titel und Größe

- Titel kurz, wie eine Aufgabe; betrifft es ein Produkt, dann „Produkt: Tätigkeit“. Mehrere gleiche Teile zählen als ein Eintrag („6 Ads für ImmunVital“).
- Größe schätzt Claude nach der Arbeitszeit: **klein** unter 1 Stunde, **mittel** etwa ein halber Tag, **groß** ab einem Tag. Im Zweifel mittel. Nennt die Person eine andere Größe, gilt ihre.

## Eintragen, erst nach Ja

Ja heißt auch „passt“, „mach“, „trag ein“. Schweigen oder ein Themenwechsel ist kein Ja.

1. Dublette prüfen: `aufgaben --suche "<stichwort>"`. Gibt es eine offene eigene Aufgabe dazu, diese erledigt setzen statt neu anlegen: `aufgabe-aendern CB-123 --erledigt --groesse <größe>` (CB-Nummer wörtlich).
2. Sonst: `erledigt --titel "<titel>" --groesse klein|mittel|gross [--notiz "<ein Satz Ergebnis>"]`.
3. In einem Satz wiedergeben, mit der CB-Nummer aus der Ausgabe.

## Grenzen

- Eingetragen wird am heutigen Tag; nicht rückdatieren. Erledigtes hat keine Frist.
- Nur für die Person selbst. Will sie Arbeit für jemand anderen eintragen: sagen, dass das nur die Person selbst kann.
- Endet die Ausgabe mit einer Meldung des Tools, sie unverändert wiedergeben.
