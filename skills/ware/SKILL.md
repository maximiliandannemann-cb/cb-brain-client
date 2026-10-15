---
name: ware
description: Liest Bestellungen (POs), Sendungen zu Amazon, Bestand, Bestellplanung und Absatz aus dem CleverBrands-Tool, nur lesen. Für Fragen wie „Wo steht PO-049?“, „Was ist unterwegs zu Amazon?“, „Wie viel Lavendelsäckchen liegt wo?“, „Wann muss die nächste Bestellung raus?“, „Wie lief Produkt X letzte Woche auf Amazon und im Shop?“, auch für Lieferant, ETA, Wareneingang, FBA-Bestand, Lager, Verkäufe, Sitzungen, Conversion.
---

# /ware

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Nur lesen: es gibt keinen Befehl, der etwas ändert. Derselbe Schlüssel wie fürs Wiki.

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

Relative Zeiträume („letzte Woche“, „seit August“) vom heutigen Datum aus in `--von/--bis` umrechnen und den Zeitraum in der Antwort nennen.

## Antworten

- PO-Nummern, SKUs und Amazon-Shipment-IDs wortwörtlich aus der Ausgabe übernehmen, nie kürzen oder umschreiben. Der Nutzer darf „PO-049“ sagen, die Antwort nennt die volle Nummer.
- Status-Texte („+2 T überfällig“, „Fertig, liegt 6 T“) unverändert wiedergeben. Zahlen nicht selbst summieren oder umrechnen, wenn die Ausgabe sie schon zeigt.
- Immer den Stand nennen (letzte Zeile der Ausgabe, z. B. „Amazon-Bestand vom 13.10.“), bei Amazon-Zahlen besonders, weil sie einen Tag oder mehr hinterherlaufen.
- Bei einer einzelnen PO, Sendung oder einem Produkt den Link aus der Ausgabe mitgeben.
- Endet die Ausgabe mit „Gekürzt“: das sagen und mit `--suche` eingrenzen statt raten.

## Grenzen

- **Keine eigene Reichweite oder Prognose.** Nicht aus Bestand und Absatz ausrechnen, wie lange die Ware reicht oder wann sie ausgeht. Verweisen: „Reichweite steht im Tool unter Bestandsprognose“ plus Produkt-Link.
- **Keine Finanzen.** EK, Preise, Zahlungen, Cashflow, Kosten und Marge gibt es über Claude nicht; ins Tool verweisen. Amazon-Umsatz und Shop-Netto aus `absatz` sind Verkaufszahlen und dürfen genannt werden.
- **Conversion über 100 % oder mit „zu hoch“:** Für Tage vor dem 11.07.2026 (alte Flieber-Historie) fehlen die Sitzungen. Den Hinweis aus der Ausgabe weitergeben, die Zahl nicht deuten; für eine belastbare Conversion den Zeitraum ab 11.07.2026 abfragen.
- Shops zeigen Umsatz nur je Shop, je Produkt nur Stück und Bestellungen (so wie das Tool). Keine Aufteilung selbst rechnen.
- Keine Mails senden. Eine Rückfrage an einen Lieferanten höchstens als Entwurf im Chat.

## Fehler

- „… ist nicht eindeutig. Möglich: …“: die passende Nummer aus der Liste wählen, wenn die Frage es eindeutig macht, sonst nachfragen.
- „… gibt es nicht“: mit `bestellungen --status alle --suche <Teil>` oder `sendungen --status alle --suche <Teil>` suchen.
- „Kein Schlüssel“ oder 401: `/wiki-setup` nennen. „Für diesen Bereich hast du keinen Zugang“: so weitergeben.
