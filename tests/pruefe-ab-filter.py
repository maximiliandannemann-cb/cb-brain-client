#!/usr/bin/env python3
"""Prüfskript für `bestellungen --ab fehlt|ueberfaellig` (Auftrag 308, 13.11.2026). Ohne Framework, ohne Netz, eigenes HOME:
urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut. Antwortform wie src/lib/lesezugang.ts auf next
(company-interface PR #831): je Bestellung `abFehlt`, `abFehltSeitWerktage`, `abUeberfaellig`.
Fälle: fehlt, überfällig, ungültiger Wert, Tool ohne die neuen Felder (400 „Unbekannte Parameter“ und 200 ohne Felder), leere Liste.
Aufruf: /usr/bin/python3 tests/pruefe-ab-filter.py   (Exit 0 = alles grün)"""
import importlib.util, io, json, os, sys, tempfile, urllib.error, urllib.parse

home = tempfile.mkdtemp()
os.makedirs(os.path.join(home, ".cb-brain"))
with open(os.path.join(home, ".cb-brain", "tool-key"), "w") as fh:
    fh.write("cbw_test")
os.environ["HOME"] = home
os.environ["CB_TOOL_URL"] = "http://127.0.0.1:9"
os.environ.pop("CB_VERCEL_BYPASS", None)

CBTOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "cbtool.py")
spec = importlib.util.spec_from_file_location("cbtool", CBTOOL)
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

fehler = 0


def pruefe(name: str, ok: bool, ausgabe: str = "") -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name + ("" if ok else f"\n{ausgabe}"))
    fehler += 0 if ok else 1


STAND = {"abgerufen": "2026-11-13T09:00:00Z", "daten": "live"}
anfragen = []
antwort = {}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append(req.full_url)
    if antwort.get("status", 200) != 200:
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "Bad Request", {}, io.BytesIO(json.dumps(antwort["json"]).encode()))
    return Antwort(json.dumps(antwort["json"]).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(args, json_antwort, status=200):
    anfragen.clear()
    antwort["json"] = json_antwort
    antwort["status"] = status
    code = 0
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    try:
        cb.main(["cbtool.py"] + list(args))
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code)
            code = 1
        else:
            code = e.code or 0
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return puffer.getvalue(), code


def query():
    return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(anfragen[0]).query)) if anfragen else None


def bestellung(po, lieferant, werktage, ueberfaellig, bestellt="2026-11-05", fehlt=True):
    return {"po": po, "produkt": "Produkt", "weitereProdukte": 0, "skus": ["SKU"], "lieferant": lieferant, "veredler": None, "ziel": "Fillhub",
            "marktplatz": "DE", "status": "Bestellt", "gruppe": "Läuft", "bestelltAm": bestellt, "etaZugesagt": "2026-12-01", "etaBestaetigt": None,
            "eingegangenAm": None, "menge": {"gesamt": 1000, "eingegangen": 0, "offen": 1000}, "naechsterSchritt": None, "abNummer": None,
            "abFehlt": fehlt, "abFehltSeitWerktage": werktage, "abUeberfaellig": ueberfaellig, "teilVon": None, "link": "https://x/movements?po=" + po}


# Nummern wie in der Antwort von next am 13.11. (Auftrag 302, lesezugang-bestellungen-ab-ueberfaellig.json), wörtlich.
GWO_OHNE = bestellung("PO-009-1-18-H2-heimonie-geschenkbox-blau", "GWO", None, True, bestellt=None)
GWO_6 = bestellung("PO-066-1-4-H2-Heimonie-Goldenes-Ticket-FBA", "GWO", 6, True)
JOSIE = bestellung("PO-050-1-2-B-22-PLS-SET", "Josie", 23, True, bestellt="2026-10-12")
FRISCH = bestellung("PO-070-1-1-TEST-FRISCH", "Gluetec", 2, False, bestellt="2026-11-11")
EIN_TAG = bestellung("PO-071-1-1-TEST-EINTAG", "Gluetec", 1, False, bestellt="2026-11-12")

# 1. überfällig: Anfrage mit ab=ueberfaellig, Text je Bestellung, PO wörtlich.
aus, code = lauf(["bestellungen", "--ab", "ueberfaellig"], {"bestellungen": [GWO_OHNE, GWO_6, JOSIE], "anzahl": 3, "gekuerzt": False, "stand": STAND})
pruefe("überfällig: Anfrage trägt ab=ueberfaellig", query() == {"ab": "ueberfaellig"}, str(query()))
pruefe("überfällig: Kopf nennt den Filter", "überfälliger AB" in aus and "(3)" in aus, aus)
pruefe("überfällig: PO-066 wörtlich mit 6 Werktagen", "PO-066-1-4-H2-Heimonie-Goldenes-Ticket-FBA · Bestellt · AB fehlt seit 6 Werktagen, überfällig" in aus, aus)
pruefe("überfällig: Josie 23 Werktage", "PO-050-1-2-B-22-PLS-SET · Bestellt · AB fehlt seit 23 Werktagen, überfällig" in aus, aus)
pruefe("überfällig: ohne Bestelltag kein „seit“", "PO-009-1-18-H2-heimonie-geschenkbox-blau · Bestellt · AB fehlt (kein Bestelltag erfasst), überfällig" in aus, aus)
pruefe("überfällig: Stand steht da", "Stand: abgerufen" in aus, aus)
pruefe("überfällig: Exit 0", code == 0, str(code))

# 2. fehlt: auch nicht überfällige, Einzahl bei 1 Werktag, ungleich überfällig.
aus, code = lauf(["bestellungen", "--ab", "fehlt", "--status", "alle"], {"bestellungen": [JOSIE, FRISCH, EIN_TAG], "anzahl": 3, "gekuerzt": False, "stand": STAND})
pruefe("fehlt: Anfrage trägt ab=fehlt und status", query() == {"ab": "fehlt", "status": "alle"}, str(query()))
pruefe("fehlt: Kopf nennt den Filter", "ohne AB" in aus, aus)
pruefe("fehlt: 2 Werktage, nicht überfällig", "PO-070-1-1-TEST-FRISCH · Bestellt · AB fehlt seit 2 Werktagen · Produkt" in aus, aus)
pruefe("fehlt: Einzahl Werktag", "AB fehlt seit 1 Werktag · " in aus, aus)
pruefe("fehlt: Josie überfällig", "AB fehlt seit 23 Werktagen, überfällig" in aus, aus)

# 2b. „seit heute“ nur am Bestelltag (wie abFehltText); 0 Werktage an einem anderen Tag (Bestelltag in der Zukunft) bleibt eine Zahl.
cb._jetzt = lambda: cb.datetime(2026, 11, 13, 9, 0, tzinfo=cb.timezone.utc)
HEUTE = bestellung("PO-072-1-1-TEST-HEUTE", "Gluetec", 0, False, bestellt="2026-11-13")
ZUKUNFT = bestellung("PO-073-1-1-TEST-ZUKUNFT", "Gluetec", 0, False, bestellt="2026-11-20")
aus, code = lauf(["bestellungen", "--ab", "fehlt"], {"bestellungen": [HEUTE, ZUKUNFT], "anzahl": 2, "gekuerzt": False, "stand": STAND})
pruefe("heute bestellt: „seit heute“", "PO-072-1-1-TEST-HEUTE · Bestellt · AB fehlt seit heute · " in aus, aus)
pruefe("Bestelltag in der Zukunft: 0 Werktagen", "PO-073-1-1-TEST-ZUKUNFT · Bestellt · AB fehlt seit 0 Werktagen · " in aus, aus)

# 3. Schreibweise mit Umlaut und Großbuchstaben wird angenommen und als ueberfaellig gesendet.
aus, code = lauf(["bestellungen", "--ab", "Überfällig"], {"bestellungen": [GWO_6], "anzahl": 1, "gekuerzt": False, "stand": STAND})
pruefe("Umlaut: als ueberfaellig gesendet", query() == {"ab": "ueberfaellig"}, str(query()))
aus, code = lauf(["bestellungen", "--ab", "u\u0308berfa\u0308llig"], {"bestellungen": [GWO_6], "anzahl": 1, "gekuerzt": False, "stand": STAND})
pruefe("Umlaut zerlegt (NFD): als ueberfaellig gesendet", query() == {"ab": "ueberfaellig"}, str(query()))

# 4. ungültiger Wert: lokal abgelehnt, keine Anfrage, Exit 2.
aus, code = lauf(["bestellungen", "--ab", "offen"], {"bestellungen": [], "anzahl": 0, "stand": STAND})
pruefe("ungültig: keine Anfrage", anfragen == [], str(anfragen))
pruefe("ungültig: Exit 2 und Text", code == 2 and "--ab erwartet fehlt oder ueberfaellig" in aus, f"{code}\n{aus}")
aus, code = lauf(["bestellungen", "--ab", "fällig"], {"bestellungen": [], "anzahl": 0, "stand": STAND})
pruefe("ungültig: Meldung nennt die Eingabe", code == 2 and "nicht „fällig“" in aus and anfragen == [], f"{code}\n{aus}")
aus, code = lauf(["bestellungen", "--ab"], {"bestellungen": [], "anzahl": 0, "stand": STAND})
pruefe("ohne Wert: keine Anfrage, Exit 2", anfragen == [] and code == 2 and "--ab braucht einen Wert" in aus, f"{code}\n{aus}")

# 5. Tool ohne die neuen Felder: main vor dem Release antwortet 400 „Unbekannte Parameter: ab“.
alt400 = {"error": "Unbekannte Parameter: ab. Erlaubt: status, suche, limit."}
aus, code = lauf(["bestellungen", "--ab", "ueberfaellig"], alt400, status=400)
pruefe("altes Tool 400: klarer Satz", "noch nicht live" in aus and code != 0, f"{code}\n{aus}")
pruefe("altes Tool 400: nicht leer und kein „Keine“", "Keine" not in aus, aus)
# … oder ignoriert den Parameter und liefert Zeilen ohne die Felder.
ohne_felder = {k: v for k, v in JOSIE.items() if not k.startswith("abFehlt") and k != "abUeberfaellig"}
aus, code = lauf(["bestellungen", "--ab", "fehlt"], {"bestellungen": [ohne_felder], "anzahl": 1, "gekuerzt": False, "stand": STAND})
pruefe("altes Tool 200 ohne Felder: klarer Satz, keine Liste", "noch nicht live" in aus and "PO-050" not in aus and code != 0, f"{code}\n{aus}")
# Ein anderer 400 bleibt der Text des Tools.
aus, code = lauf(["bestellungen", "--ab", "fehlt"], {"error": "limit erwartet 1 bis 200."}, status=400)
pruefe("anderer 400: Text des Tools", "limit erwartet 1 bis 200." in aus and "noch nicht live" not in aus, aus)

# 6. leere Liste: sagt, dass keine fehlt, nicht „noch nicht live“.
aus, code = lauf(["bestellungen", "--ab", "ueberfaellig"], {"bestellungen": [], "anzahl": 0, "gekuerzt": False, "stand": STAND})
pruefe("leer: klarer Satz", "Keine offenen Bestellungen mit überfälliger AB." in aus and "noch nicht live" not in aus and code == 0, f"{code}\n{aus}")
aus, code = lauf(["bestellungen", "--ab", "fehlt"], {"bestellungen": [], "anzahl": 0, "gekuerzt": False, "stand": STAND})
pruefe("leer fehlt: klarer Satz", "Keine offenen Bestellungen ohne AB." in aus, aus)

# 7. ohne --ab: Anfrage ohne ab; die Liste zeigt die AB-Lage trotzdem, wenn das Tool sie liefert; altes Tool unverändert.
mit_ab = dict(bestellung("PO-049-1-1-B-22-LS-SET", "Josie", 23, True, bestellt="2026-10-12"))
mit_ab_nr = dict(mit_ab, abNummer="AB-1", abFehlt=False, abFehltSeitWerktage=None, abUeberfaellig=False, po="PO-048-1-1-TEST")
aus, code = lauf(["bestellungen"], {"bestellungen": [mit_ab, mit_ab_nr, ohne_felder], "anzahl": 3, "gekuerzt": False, "stand": STAND})
pruefe("ohne --ab: kein ab in der Anfrage", "ab" not in (query() or {}), str(query()))
pruefe("ohne --ab: AB-Lage in der Zeile", "PO-049-1-1-B-22-LS-SET · Bestellt · AB fehlt seit 23 Werktagen, überfällig" in aus, aus)
pruefe("ohne --ab: mit AB kein Text", "PO-048-1-1-TEST · Bestellt · Produkt" in aus, aus)
pruefe("ohne --ab: altes Tool wie bisher", "PO-050-1-2-B-22-PLS-SET · Bestellt · Produkt" in aus, aus)

# 8. Einzelansicht zeigt die AB-Lage.
aus, code = lauf(["bestellung", "PO-066-1-4-H2-Heimonie-Goldenes-Ticket-FBA"], {"bestellung": dict(GWO_6, positionen=[], meilensteine=[], stationen=[], etaAenderungen=[]), "stand": STAND})
pruefe("Einzelansicht: AB-Zeile", "AB: fehlt seit 6 Werktagen, überfällig" in aus, aus)

print(f"\n{'Alles grün.' if not fehler else f'{fehler} Fehler.'}")
sys.exit(1 if fehler else 0)
