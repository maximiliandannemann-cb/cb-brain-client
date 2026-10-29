---
name: ware
description: Liest Bestellungen (POs), Sendungen zu Amazon, Bestand, Bestellplanung und Absatz aus dem CleverBrands-Tool; verschiebt den bestätigten Termin (ETA) einer offenen PO nur nach Ja der Person. Für Fragen wie „Wo steht PO-049?“, „Was ist unterwegs zu Amazon?“, „Wie viel Lavendelsäckchen liegt wo?“, „Wann muss die nächste Bestellung raus?“, „Wie lief Produkt X letzte Woche auf Amazon und im Shop?“, auch für Lieferant, ETA, Wareneingang, FBA-Bestand, Lager, Verkäufe, Sitzungen, Conversion.
---

# /ware

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Lesen, mit einer Ausnahme: `bestellung-eta` verschiebt den bestätigten Termin einer PO, nur auf Wort der Person (Abschnitt unten). Sonst ändert kein Befehl etwas. Derselbe Schlüssel wie fürs Wiki.

## Welcher Befehl

| Frage | Befehl |
|---|---|
| Was ist bestellt, was hängt, was kommt wann? | `bestellungen` (offene), `--status alle` mit Angelieferten, `--suche <PO, Lieferant, Produkt, SKU>` |
| Eine bestimmte PO | `bestellung PO-049` (Anfang reicht, wenn eindeutig) |
| Was ist unterwegs zu Amazon? | `sendungen`, `--status alle`, `--suche <Nummer, Amazon-ID, Lager, SKU>` |
| Eine Sendung | `sendung IN-2026-0039` oder `sendung FBA15MM4GTB5` |
| Wie viel liegt wo? | `bestand --suche <SKU oder Name>` (ohne Suche alle Produkte) |
| Wann muss die nächste Bestellung raus? | `bestellplanung`, `--status faellig` (nächste 4 Wochen) oder `ueberfaellig`, `--marktplatz DE\|US`, `--suche` |
| Wie lief Produkt X? | `absatz --suche <SKU oder Name>`, Zeitraum `--von/--bis YYYY-MM-DD` (Standard 30 Tage bis gestern, höchstens 400), `--kanal amazon\|shop`, `--je tag\|woche` für den Verlauf |

| Termin einer PO verschieben (nur nach Ja) | `bestellung-eta PO-020 --eta YYYY-MM-DD --grund "<satz>" [--quelle <link>]` |

Relative Zeiträume („letzte Woche“, „seit August“) vom heutigen Datum aus in `--von/--bis` umrechnen und den Zeitraum in der Antwort nennen.

## Antworten

- PO-Nummern, SKUs und Amazon-Shipment-IDs wortwörtlich aus der Ausgabe übernehmen, nie kürzen oder umschreiben. Der Nutzer darf „PO-049“ sagen, die Antwort nennt die volle Nummer.
- Status-Texte („+2 T überfällig“, „Fertig, liegt 6 T“) unverändert wiedergeben. Zahlen nicht selbst summieren oder umrechnen, wenn die Ausgabe sie schon zeigt.
- Immer den Stand nennen (letzte Zeile der Ausgabe, z. B. „Amazon-Bestand vom 13.10.“), bei Amazon-Zahlen besonders, weil sie einen Tag oder mehr hinterherlaufen.
- Bei einer einzelnen PO, Sendung oder einem Produkt den Link aus der Ausgabe mitgeben.
- Endet die Ausgabe mit „Gekürzt“: das sagen und mit `--suche` eingrenzen statt raten.

## ETA ändern, nur auf Wort der Person

Eine neue Ankunft steht in einer Mail, einer Nachricht oder die Person sagt sie. Dann so:

1. Erst lesen: `bestellung <nr>` für jede betroffene PO. Alten Termin, „ETA bestätigt“ und die Sendung nennen.
2. Vorschlag zeigen, nichts schreiben: je PO alter Termin › neuer Termin, Grund und Quelle. Beispiel: „PO-020-1-1-B-22-LS-SET: 04.12.2026 › 20.11.2026. Grund: CIS (Pia) meldet am 29.10. Ankunft Regensburg etwa 20.11. Quelle: Mail von Pia, 29.10. Eintragen?“
3. Erst nach einem ausdrücklichen Ja `bestellung-eta` aufrufen. „Klingt gut“ zu etwas anderem ist kein Ja. Ein Ja gilt für die gezeigten POs und Termine, nicht für weitere.
4. Grund: wörtlich von der Person, oder ein Satz aus der Quelle, den die Person mit ihrem Ja bestätigt hat. Nie selbst einen Grund erfinden oder ausschmücken. Ohne Grund nicht aufrufen, sondern fragen.
5. Quelle: Link zur Mail oder Nachricht, wenn es einen gibt (Mail über die Composio-CLI mit dem Konto der Sitzung suchen). Keinen Link erfinden; ohne Link geht es ohne `--quelle`.
6. Nach dem Aufruf die Ausgabe weitergeben: alter und neuer Termin, Link. Nennt sie „Termin gilt auch für …“, das der Person sagen: die POs reisen in derselben Sendung, ihre Ankunft hat sich mitverschoben, der Verlaufseintrag steht nur an der genannten PO.

Was nicht geht, und was dann zu tun ist:
- **Noch kein bestätigter Termin** (nur „ETA zugesagt“, also der Wunschtermin): `bestellung-eta` lehnt ab. Der erste Termin kommt im Tool mit der AB (Bestellung › Was ist passiert? › AB erhalten). Der Person das sagen und den Link geben, nicht über einen anderen Weg eintragen.
- Angelieferte POs, Termine in der Vergangenheit: lehnt das Tool ab, Meldung unverändert weitergeben.
- Nur der Termin ändert sich. Status, Mengen, AB-Nummer und Beträge ändert der Befehl nie; dafür ins Tool verweisen.
- Sendungen zu Amazon (IN-2026-…): kein Befehl. Der Termin wird im Tool gepflegt.

## Grenzen

- **Keine eigene Reichweite oder Prognose.** Nicht aus Bestand und Absatz ausrechnen, wie lange die Ware reicht oder wann sie ausgeht. Verweisen: „Reichweite steht im Tool unter Bestandsprognose“ plus Produkt-Link.
- **Keine Finanzen.** EK, Preise, Zahlungen, Cashflow, Kosten und Marge gibt es über Claude nicht; ins Tool verweisen. Amazon-Umsatz und Shop-Netto aus `absatz` sind Verkaufszahlen und dürfen genannt werden.
- **Conversion über 100 % oder mit „zu hoch“:** Für Tage vor dem 11.07.2026 (alte Flieber-Historie) fehlen die Sitzungen. Den Hinweis aus der Ausgabe weitergeben, die Zahl nicht deuten; für eine belastbare Conversion den Zeitraum ab 11.07.2026 abfragen.
- Shops zeigen Umsatz nur je Shop, je Produkt nur Stück und Bestellungen (so wie das Tool). Keine Aufteilung selbst rechnen.
- Keine Mails senden. Eine Rückfrage an einen Lieferanten höchstens als Entwurf im Chat.
- Schreiben nur über `bestellung-eta` und nur nach Ja (Abschnitt oben). Nichts sonst ändern, auch nicht auf Bitte; ins Tool verweisen.

## Fehler

- „… ist nicht eindeutig. Möglich: …“: die passende Nummer aus der Liste wählen, wenn die Frage es eindeutig macht, sonst nachfragen.
- „Nicht geändert: …“ (bei `bestellung-eta`): die Meldung des Tools wörtlich weitergeben, nicht anders versuchen. „Bitte kurz begründen …“: die Person nach einem Satz Grund fragen. „noch nicht freigeschaltet“ oder „gibt es im Tool noch nicht“: im Tool eintragen lassen.
- „… gibt es nicht“: mit `bestellungen --status alle --suche <Teil>` oder `sendungen --status alle --suche <Teil>` suchen.
- „Kein Schlüssel“ oder 401: `/wiki-setup` nennen. „Für diesen Bereich hast du keinen Zugang“: so weitergeben.
