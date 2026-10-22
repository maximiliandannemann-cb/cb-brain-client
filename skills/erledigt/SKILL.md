---
name: erledigt
description: Trägt erledigte Arbeit der Person ins CleverBrands-Tool ein, damit sie in den Bruno-Punkten zählt (klein 1, mittel 3, groß 5). Ist in der Sitzung ein Arbeitsschritt abgeschlossen (gemergt, verschickt, fertig, entschieden), am Ende der Antwort EINEN Eintrag vorschlagen: „**Erledigt:** <Titel> (<Größe>). Eintragen?“ mit einem Satz Ergebnis und Beleg-Link darunter. Eintragen erst nach Ja. Auch für „hab heute 6 Ads fertig“, „trag ein, dass …“, „/erledigt“.
---

# /erledigt

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Eingetragen wird nur für die Person selbst, nie für andere (das Tool lehnt es ab).

## Wann vorschlagen

- Ein Arbeitsschritt der Person ist in dieser Sitzung abgeschlossen: ein PR gemergt, eine Mail verschickt, eine Vorlage fertig, eine Entscheidung getroffen, ein Bug behoben. Dann ans Ende der Antwort den Vorschlag, darunter das Ergebnis:
  `**Erledigt:** ImmunVital: Welcome Flow in Klaviyo (mittel). Eintragen?`
  `Ergebnis: Flow live mit drei Mails, Vorlage im Drive: https://drive.google.com/…`
- Die Person erzählt von Arbeit ohne Claude („hab heute 6 Ads fertig“): genauso vorschlagen.
- Nicht für Kleinkram unter etwa 15 Minuten, nicht für Zwischenschritte, nicht für Arbeit anderer. Je Arbeitsschritt nur einmal vorschlagen; nach Nein oder ohne Antwort nicht wieder für denselben Schritt.
- Neben einem `/drop`-Vorschlag steht der Erledigt-Vorschlag als eigene Zeile darunter.

## Titel und Größe

- Titel kurz, wie eine Aufgabe; betrifft es ein Produkt, dann „Produkt: Tätigkeit“. Mehrere gleiche Teile zählen als ein Eintrag („6 Ads für ImmunVital“).
- Größe schätzt Claude nach der Arbeitszeit: **klein** unter 1 Stunde, **mittel** etwa ein halber Tag, **groß** ab einem Tag. Im Zweifel mittel. Nennt die Person eine andere Größe, gilt ihre.

## Ergebnis und Beleg (Pflicht ab Mo 26.10.2026)

Ohne Ergebnis wird nichts erledigt; das Tool und das Skript lehnen es ab („Ergebnis fehlt: …“).

- **Satz:** was kam heraus, wo liegt es. Ein Satz, mindestens 10 Zeichen, sachlich („Angebot liegt vor, 2,10 € je Dose“, „Bug behoben, Login geht wieder“). Kein Protokoll, keine Arbeitsschritte. Nummern (PO, Sendung, SKU, CB) wörtlich.
- **Beleg-Link selbst suchen**, bevor Claude vorschlägt, und in denselben Satz schreiben:
  - Bau, Code: der PR. `gh pr view <nr> --json url,state,title` oder `gh pr list --search "<stichwort>" --state all --json number,url,title`.
  - Mail: über die Composio-CLI mit dem Konto, das in dieser Sitzung schon benutzt wurde (z. B. `--account "Cleverbrands Gmail"`); den Link `https://mail.google.com/mail/u/0/#all/<thread_id>` aus der Thread-ID bauen. Kein anderes Konto raten.
  - Drive: der Link der Datei oder des Ordners, wie er in der Sitzung vorkam oder über die Drive-Suche gefunden wurde.
- **Nie einen Link erfinden oder aus dem Gedächtnis zusammensetzen.** Findet Claude keinen, reicht der Satz; dann ohne Link vorschlagen.
- Satz und Link stehen im Vorschlag; die Person kann beides ändern. Geschrieben wird erst nach Ja, mit ihren Änderungen.

## Eintragen, erst nach Ja

Ja heißt auch „passt“, „mach“, „trag ein“. Schweigen oder ein Themenwechsel ist kein Ja.

1. Dublette prüfen: `aufgaben --suche "<stichwort>"`. Gibt es eine offene eigene Aufgabe dazu, diese erledigt setzen statt neu anlegen: `aufgabe-aendern CB-123 --erledigt --groesse <größe> --ergebnis "<satz mit link>"` (CB-Nummer wörtlich).
2. Sonst: `erledigt --titel "<titel>" --groesse klein|mittel|gross --ergebnis "<satz mit link>"`. `--notiz` nur für Kontext, der nicht ins Ergebnis gehört.
3. Antwortet das Skript „Ergebnis fehlt: …“: die Person nach dem Ergebnis fragen, nicht selbst eins erfinden, und den Aufruf mit `--ergebnis` wiederholen.
4. In einem Satz wiedergeben, mit der CB-Nummer aus der Ausgabe.

## Grenzen

- Eingetragen wird am heutigen Tag; nicht rückdatieren. Erledigtes hat keine Frist.
- Nur für die Person selbst. Will sie Arbeit für jemand anderen eintragen: sagen, dass das nur die Person selbst kann.
- Endet die Ausgabe mit einer Meldung des Tools, sie unverändert wiedergeben.
