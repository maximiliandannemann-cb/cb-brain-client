#!/usr/bin/env python3
"""Prüfskript für die Lage in `sendungen`, `sendung` und `bestand` (06.11.2026). Ohne Framework, ohne Netz, eigenes HOME, nur Platzhalter.
Das Tool rechnet die Lage, hier wird nur angezeigt. Fehlfall: ein älteres Tool ohne die Felder ändert die Ausgabe nicht.
Aufruf: /usr/bin/python3 tests/pruefe-sendung-lage.py   (Exit 0 = alles grün)"""
import importlib.util, io, json, os, sys, tempfile

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


def pruefe(name, ok, ausgabe=""):
    global fehler
    print(("ok    " if ok else "FEHLER ") + name + ("" if ok else f"\n{ausgabe}"))
    fehler += 0 if ok else 1


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


antwort = {}
cb.urllib.request.urlopen = lambda req, timeout=None: Antwort(json.dumps(antwort["json"]).encode())


def lauf(args, json_antwort):
    antwort["json"] = json_antwort
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    try:
        cb.main(["cbtool.py"] + list(args))
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code)
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return puffer.getvalue()


STAND = {"abgerufen": "2026-11-06T08:47:00Z", "daten": "live"}
LAGE = {"lage": "Wird eingebucht", "seit": "2026-11-04T08:00:00Z", "widerspruch": None}
KOPF = {"nr": "EIN-1", "status": "Abgeholt", "amazonId": "AMZ-1", "gruppe": "Unterwegs", "von": "Lager A", "eta": None, "angelegtAm": "2026-10-06", "stueck": 10, "kartons": None, "produkt": "Produkt A", "link": "http://x/y", "positionen": []}


# sendungen
neu = lauf(["sendungen"], {"sendungen": [dict(KOPF, **LAGE)], "anzahl": 1, "stand": STAND})
pruefe("sendungen: Status und Lage nebeneinander", "AMZ-1 · Abgeholt · Lage Wird eingebucht seit 04.11.2026" in neu, neu)
alt = lauf(["sendungen"], {"sendungen": [KOPF], "anzahl": 1, "stand": STAND})
pruefe("sendungen, älteres Tool: keine Lage", "Lage " not in alt and "AMZ-1 · Abgeholt · von Lager A" in alt, alt)
pruefe("sendungen: außer der Lage alles gleich", neu.replace(" · Lage Wird eingebucht seit 04.11.2026 09:00", "") == alt, neu + alt)
aus = lauf(["sendungen"], {"sendungen": [dict(KOPF, lage="Abgeschlossen", seit="2026-11-02", widerspruch="amazon_wieder_geoeffnet: Amazon meldet MIXED, war schon CLOSED")], "anzahl": 1, "stand": STAND})
pruefe("sendungen: Widerspruch wörtlich, Tag als seit", "Lage Abgeschlossen seit 02.11.2026 (amazon_wieder_geoeffnet: Amazon meldet MIXED, war schon CLOSED)" in aus, aus)
aus = lauf(["sendungen"], {"sendungen": [dict(KOPF, lage="Abgeholt", seit=None, widerspruch=None)], "anzahl": 1, "stand": STAND})
pruefe("sendungen: seit unbekannt, kein „seit None“", "· Lage Abgeholt ·" in aus and "None" not in aus, aus)

aus = lauf(["sendungen"], {"sendungen": [dict(KOPF, lage=None, seit=None, widerspruch=None)], "anzahl": 1, "mengenNichtGeladen": True, "stand": STAND})
pruefe("sendungen: Amazon-Daten fehlen, Grund genannt", "AMZ-1 · Abgeholt · Lage unbekannt, Amazon-Daten nicht geladen" in aus, aus)

# sendung
aus = lauf(["sendung", "EIN-1"], {"sendung": dict(KOPF, **LAGE), "stand": STAND})
pruefe("sendung: Lage", "Lage Wird eingebucht seit" in aus, aus)
aus = lauf(["sendung", "EIN-1"], {"sendung": KOPF, "stand": STAND})
pruefe("sendung, älteres Tool: keine Lage", "Lage" not in aus.replace("Lager", ""), aus)
aus = lauf(["sendung", "AMZ-2"], {"ohneEinsendung": dict({"amazonId": "AMZ-2", "art": "direktlieferung", "bestellungen": [], "amazonStatus": "RECEIVING", "lager": None, "stand": None, "positionen": []}, **LAGE), "sendung": {}, "stand": STAND})
pruefe("sendung ohne Einsendung: Lage", "Lage Wird eingebucht" in aus, aus)

# bestand
B = {"sku": "SKU-A", "name": "Produkt A", "marktplatz": "DE", "fba": None, "fbaHinweis": None, "lager": [], "lagerGesamt": None, "beimHersteller": 0, "unterwegs": {"stueck": 30, "anlieferungen": [{"ref": "EIN-1", "art": "Sendung", "stueck": 30, "eta": None, "ueberfaelligTage": 0}]}, "hinweis": "h", "link": "http://x/p"}
Z = dict({"amazonId": "AMZ-3", "art": "direktlieferung", "versandt": 50, "eingebucht": 10, "offen": 40}, **LAGE)
neu = lauf(["bestand", "--suche", "SKU-A"], {"bestand": [dict(B, nachLage={"Abgeholt": 10, "Wird eingebucht": 20}, ohneEinsendung=[Z])], "anzahl": 1, "stand": STAND})
pruefe("bestand: Aufteilung", "Einsendungen nach Lage: Abgeholt 10, Wird eingebucht 20" in neu, neu)
pruefe("bestand: ohne Einsendung", "ohne Einsendung: AMZ-3 · direktlieferung · Lage Wird eingebucht" in neu and "versandt 50 · eingebucht 10 · offen 40" in neu, neu)
pruefe("bestand: unterwegs gleich", "unterwegs 30" in neu, neu)
alt = lauf(["bestand", "--suche", "SKU-A"], {"bestand": [B], "anzahl": 1, "stand": STAND})
pruefe("bestand, älteres Tool: keine neue Zeile", "Lage" not in alt.replace("Lager", "") and "ohne Einsendung" not in alt, alt)
gleich = [z for z in neu.splitlines() if "nach Lage" not in z and "ohne Einsendung" not in z]
pruefe("bestand: außer den zwei Zeilen alles gleich", gleich == alt.splitlines(), neu + alt)
aus = lauf(["bestand", "--suche", "SKU-A"], {"bestand": [dict(B, nachLage=None, ohneEinsendung=None)], "anzahl": 1, "mengenNichtGeladen": True, "stand": STAND})
pruefe("bestand: Amazon-Daten fehlen, Grund genannt, nie leer", "nach Lage: unbekannt, die Amazon-Daten" in aus and "ohne Einsendung: unbekannt, die Amazon-Daten" in aus and "nichts offen" not in aus, aus)
aus = lauf(["bestand", "--suche", "SKU-A"], {"bestand": [dict(B, nachLage={}, ohneEinsendung=[])], "anzahl": 1, "stand": STAND})
pruefe("bestand: nichts offen, kein Hinweis ohne Zeile", "nichts offen" in aus and "nicht addieren" not in aus, aus)
pruefe("bestand: Hinweis gegen Doppelzählung", "nicht addieren" in neu, neu)
aus = lauf(["bestand", "--suche", "SKU-A"], {"bestand": [dict(B, nachLage={}, ohneEinsendung=[dict(Z, versandt=None, eingebucht=None, offen=None)])], "anzahl": 1, "stand": STAND})
pruefe("bestand: Menge unbekannt, nie 0", "versandt unbekannt" in aus and "offen unbekannt" in aus, aus)

print("Alle grün" if not fehler else f"{fehler} Fehler")
sys.exit(1 if fehler else 0)
