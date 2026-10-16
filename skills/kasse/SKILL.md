---
name: kasse
description: Kaffeekasse aus dem CleverBrands-Tool. Zeigt, was fällig ist, meldet eine PayPal-Zahlung an Mats (Claude liest den Screenshot, ins Tool gehen nur Betrag, Datum und Empfänger) und erlaubt dem Kassenwart Widerspruch und Erlass. Für „Kasse“, „Kaffeekasse“, „was schulde ich“, „hab eingezahlt“, einen PayPal-Screenshot oder den Kassen-Hinweis aus dem Hook.
---

# /kasse

Aufruf immer `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" <befehl>`. Das Tool rechnet alles: Beträge, Fälligkeit, Zinsen und wer was darf. Selbst nichts rechnen und keine Beträge schätzen. Buchungen laufen unter dem Namen, dem der Schlüssel gehört.

## Stand („Kasse“, „was schulde ich“)

`kasse` ausführen und in zwei Sätzen sagen: was jetzt fällig ist (mit Zinsen), was noch nicht fällig ist, was es bei der nächsten 12:00 ohne Meldung wird.

## Zahlung melden („hab eingezahlt“, Screenshot)

1. `kasse` ausführen. Vergleichswerte sind „Fällig“ (jetzt zu zahlen) und „Offen gesamt“ (fällig plus noch nicht fällig).
2. Den Screenshot selbst ansehen und genau drei Angaben ablesen: Betrag, Datum der Zahlung, Empfänger. Nichts ergänzen. Ist etwas unlesbar oder fehlt es, nachfragen. Ohne Screenshot die Person nach Betrag, Datum und Empfänger fragen.
3. Abweichungen sofort nennen, in einem Satz, vor der Frage:
   - Betrag passt weder zu „Fällig“ noch zu „Offen gesamt“: „Screenshot 5,00 €, fällig sind 6,60 €. Melde ich 5,00 €? Dann laufen Erinnerung und Zinsen auf 1,60 € weiter.“ Mehr als offen wird Guthaben.
   - Empfänger ist nicht Mats (für Mats' eigene Zahlung: nicht Max).
   - Datum liegt in der Zukunft oder vor dem 19.10.2026.
4. Fragen: „Screenshot 6,60 € an Mats am 20.10., fällig sind 6,60 €. Soll ich das melden?“ Erst nach ausdrücklichem Ja:
   `kasse-melden --betrag 6,60 --datum YYYY-MM-DD --empfaenger "<Name wie auf dem Screenshot>"`
5. Die Ausgabe in einem Satz wiedergeben: Nummer, bis wann widersprochen werden kann, was jetzt noch offen ist.

Das Bild bleibt in der Sitzung. Nie hochladen, nie speichern, nie als Datei oder Pfad an das Skript geben, nie mit /drop einwerfen. Ins Tool geht nur die eine Zeile aus Betrag, Datum und Empfänger. Das Skript liest keine Bilder.

## Kassenwart: widersprechen, erlassen, für andere melden

Nur auf ausdrückliche Anweisung der Person. Ob sie das darf, entscheidet das Tool (Kassenwart ist Mats, für Mats' Beträge Max). Lehnt das Tool ab, seine Meldung unverändert wiedergeben und nichts umgehen.

- Offene Meldungen mit Nummer stehen bei `kasse` unter „Zu prüfen“. Widersprechen geht nur, solange die Meldung offen ist.
- Widersprechen: `kasse-widersprechen --meldung 41 --grund "<Satz der Person>"`. Zinsen laufen dann rückwirkend.
- Erlassen (krank, Urlaub): `kasse-erlassen --fuer <Name> --tag YYYY-MM-DD [--bis YYYY-MM-DD] --grund "<Satz der Person>"`. Gilt für ganze Werktage samt Zinsen, höchstens bis heute.
- Barzahlung für jemanden: `kasse-melden --fuer <Name> --betrag … --datum … --empfaenger "Mats bar"`. Gilt sofort als bestätigt.

Den Grund immer von der Person nehmen, wörtlich, nie selbst formulieren. Relative Tage („Montag“) in YYYY-MM-DD umrechnen und im Satz nennen.

## Hinweis aus dem Hook

`<cb-plugin>Kaffeekasse: …</cb-plugin>` kommt Mo bis Fr höchstens einmal je Stunde: für den Zahler, wenn ab 12:00 etwas fällig ist, für den Kassenwart, wenn ab 08:00 eine Meldung wartet. Einmal in einem Satz weitergeben und anbieten, die Zahlung zu melden. Nicht drängen, nicht wiederholen, nie ohne Ja melden. Nach einer Meldung kommt kein Hinweis mehr.

## Fehler und Grenzen

- „Die Kasse ist im Tool noch nicht da.“: das Tool hat die Kasse noch nicht; nichts weiter versuchen.
- „Möglich: <Namen>“: den Namen bei der Person erfragen, nicht raten.
- „Schon gemeldet (Nr. …)“: dieselbe Meldung kam vor weniger als zehn Minuten schon an; nichts doppelt.
- Ändern und Löschen gibt es nicht. Eine falsche Meldung korrigiert der Kassenwart per Widerspruch, Kulanz läuft über Erlass.
