---
name: offen
description: Schlägt am Ende einer Arbeitssitzung vor, offene Punkte als Aufgaben ins CleverBrands-Tool zu legen (Zusagen, nächste Schritte, Warten auf andere). Zeigt eine kurze Liste, legt erst nach ausdrücklichem Ja an. Einmal anbieten, wenn die Person die Arbeit abschließt („danke, das wars“, „fertig für heute“, verabschiedet sich) und in der Sitzung wirklich etwas offen geblieben ist; nach Nein nicht wieder. Auch für „was ist offen geblieben“, „/offen“.
---

# /offen

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Firmenregel „keine KI-Aufgaben“: Claude schlägt nur vor, angelegt wird erst nach ausdrücklichem Ja der Person.

## Wann

- Die Person ruft `/offen` auf, oder sie schließt die Arbeit ab und in dieser Sitzung sind offene Punkte entstanden. Dann einmal in einem Satz anbieten: „Sollen wir die offenen Punkte als Aufgaben ins Tool legen?“
- Höchstens einmal je Sitzung anbieten. Sagt die Person nein oder geht nicht darauf ein: nicht wieder fragen.
- Ist nichts offen geblieben: nichts anbieten. Bei `/offen` sagen „Aus dieser Sitzung ist nichts offen.“ und fertig.

## Was zählt

Nur, was in dieser Sitzung wirklich offen geblieben ist: eine Zusage der Person („schick ich morgen“), ein vereinbarter nächster Schritt, etwas, das auf eine Antwort von anderen wartet. Nicht: Ideen, Vielleicht-Punkte, Erledigtes, Aufgaben „zur Sicherheit“, Punkte aus alten Mails oder Notizen. Nichts erfinden; im Zweifel weglassen.

## Schritte

1. Vorschläge sammeln. Je Punkt: **Titel** (kurz; betrifft es ein Produkt, dann „Produkt: Tätigkeit“, z. B. „ImmunVital: Etikett freigeben“), **für wen** (ohne Angabe die Person selbst), **Frist** (Datum).
2. Für jeden Punkt Dubletten prüfen: `aufgaben --suche "<stichwort>" --fuer alle`. Gibt es schon eine offene Aufgabe dazu, statt Neuanlage eine Notiz an diese Aufgabe vorschlagen (CB-Nummer wörtlich).
3. Die Liste zeigen, je Punkt eine Zeile, keine Tabelle:
   `1. ImmunVital: Etikett freigeben · Max · bis Fr 16.10.`
   `2. Notiz an CB-123: Angebot von Gechem liegt vor`
   Fehlt eine Frist, im selben Zug danach fragen („Bis wann soll 1 erledigt sein?“). Ohne Frist wird nichts angelegt.
   Darunter: „Soll ich die anlegen? Du kannst einzelne streichen oder ändern.“
4. Warten. Erst nach ausdrücklichem Ja („ja“, „passt“, „leg an“, „nur 1 und 3“) genau die bestätigten Punkte anlegen:
   - neu: `aufgabe-neu --titel "<titel>" --faellig YYYY-MM-DD [--fuer <Name>] [--beschreibung "<ein Satz Kontext>"]`
   - Notiz: `aufgabe-aendern CB-123 --notiz "<ein bis zwei Sätze>"`
   Relative Daten („Freitag“, „nächste Woche“) vom heutigen Datum aus in YYYY-MM-DD umrechnen und im Satz als Datum nennen.
5. In einem Satz wiedergeben, was angelegt wurde, mit den CB-Nummern aus der Ausgabe.

## Grenzen

- Kein Ja, keine Aufgabe. Schweigen oder ein Themenwechsel ist kein Ja.
- Namen für `--fuer` gehen als eindeutige Kurzform ab drei Zeichen. Endet die Ausgabe mit „Möglich: <Namen>“, nachfragen, nicht raten.
- Ton: kurz, deutsch, ohne Erklärung der Regeln.
