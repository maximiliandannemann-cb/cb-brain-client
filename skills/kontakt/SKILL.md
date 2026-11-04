---
name: kontakt
description: Kontaktgeschichte vor jeder Mail. Pflicht, bevor eine Mail oder ein Entwurf an einen Lieferanten, Partner oder sonstigen Kontakt entsteht, auch bei Serien (jeder Empfänger einzeln). Fragt das CleverBrands-Tool, wer der Kontakt ist und was offen ist, liefert die fertige Gmail-Suche und klärt so, ob eine Vorstellung nötig ist. Für „schreib an …“, „Entwurf an …“, „frag bei … nach“, „Mail an Fillhub“, Nachfass-Mails, Serienmails.
---

# Kontaktgeschichte vor jeder Mail

Anlass: Ein Bot hat sich bei Kontakten vorgestellt, mit denen es schon Austausch gab. Deshalb gilt vor JEDER Mail an einen Kontakt dieser Ablauf. Das Tool liest keine Mails. Es ordnet zu und liefert die Gmail-Suche. Die Mails liest jeder Bot mit seiner eigenen Gmail-Verbindung.

Aufruf: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cbtool.py" kontakt <adresse|domain|firma>` (mit `--json` die rohe Antwort).

## Ablauf

1. **Kontakt abfragen.** `kontakt pia@fillhub.de`, `kontakt fillhub.de` oder `kontakt Fillhub`. Am besten mit der Adresse, an die die Mail geht. Die Antwort nennt Lieferant bzw. Partner, offene Bestellungen und Sendungen, die letzten Journal-Zeilen, die Wiki-Seite und `mail_suche`.
2. **Mail-Suche ausführen, mit der eigenen Gmail-Verbindung.** `mail_suche` wörtlich übernehmen, nicht umbauen. Nur Kopfzeilen lesen: Datum, Absender, Betreff der letzten drei bis fünf Mails. Den Inhalt einer Mail nur öffnen, wenn der Bezug für den Entwurf nötig ist.
   - Claude Code (Max, CleverBrands-Postfach): `python3 ~/cleverbrands-exports/werkzeuge/gmail_lesen.py suche "<mail_suche>" 5`. Konto ist dort fest „Cleverbrands Gmail“.
   - Andere Personen: ihre eigene Gmail-Verbindung mit derselben Suche.
3. **Anrede wählen.**
   - Kontakt bekannt (sicher im Tool zugeordnet, über kontakt-mail oder domain, ODER Treffer in der Mail-Suche): keine Vorstellung. Direkt auf den letzten Austausch Bezug nehmen („zu unserer Mail vom 03.11. …“).
   - Nur über den Namen zugeordnet (`über name`, Zeile „Achtung: nur über den Namen zugeordnet, unsicher“): das Tool hat den Partner aus dem Namen geraten. Erst die Mail-Suche entscheidet: mit Treffern Bezug auf den letzten Austausch, ohne Treffer kurz vorstellen. Daten des Partners nur verwenden, wenn die Mails bestätigen, dass es derselbe ist.
   - Kontakt unbekannt (keine Zuordnung UND keine Treffer): kurze Vorstellung, ein Satz, wer wir sind und warum wir schreiben.
   - „Im Tool unbekannt“ heißt nicht „unbekannt“. Erst die Mail-Suche entscheidet.
4. **Nach dem Entwurf prüfen:** Passt die Anrede zur Geschichte? Bei bekanntem Kontakt darf kein „ich möchte mich kurz vorstellen“, „wir sind …“ oder Ähnliches im Text stehen. Stimmt der Bezug (Datum, Betreff, PO- oder IN-Nummer wörtlich aus der Antwort)?
5. **Serien:** Schritte 1 bis 4 für jeden Empfänger einzeln. Kein gemeinsamer Text mit Vorstellung für alle.

## Was die Antwort sagt

- `Bekannt im Tool: <Name> · über kontakt-mail|domain` bzw. `Zugeordnet (unsicher): <Name> · über name`: wie die Zuordnung zustande kam. `name` heißt: kein Kontakt mit dieser Mail im Tool, nur der Name ist gleich, also unsicher (siehe Schritt 3).
- `N Partner passen (…). Mit adresse= oder genauerer firma= eingrenzen.`: mit der vollen Adresse oder einem genaueren Namen erneut fragen.
- `Journal gerade nicht ladbar, Antwort ohne Journal-Zeilen.`: Journal fehlt nur diesmal; die Mail-Suche reicht für die Anrede.
- Eine Domain eines Freemail-Anbieters (gmail.com, mail.163.com) oder eine reine Endung (com.cn) lehnt das Tool ab: mit der vollen Adresse fragen.
- `Lücke: …`: im Tool fehlt eine Mail-Adresse oder Firmendomain. Nicht selbst nachtragen, sondern der Person nennen.
- Nummern (PO, IN, J, CB) immer wörtlich übernehmen.

## Nicht

- Keine Mail ohne diesen Ablauf, auch keine kurze Nachfrage.
- Keine Mail senden: nur Entwürfe, gesendet wird von der Person.
- Die Mail-Suche nicht ohne `in:anywhere` ausführen (sonst fehlen archivierte Mails).
