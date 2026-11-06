#!/usr/bin/env python3
"""Prüfskript für die Amazon-Mengen in `sendung` und `sendungen --abweichung` (06.11.2026). Ohne Framework, ohne Netz, eigenes HOME:
urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut. Fehlfall: fehlende Mengen sind „unbekannt“, nie 0.
Aufruf: /usr/bin/python3 tests/pruefe-sendung-mengen.py   (Exit 0 = alles grün)"""
import importlib.util, io, json, os, sys, tempfile, urllib.parse

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


STAND = {"abgerufen": "2026-11-06T08:47:00Z", "daten": "live"}
KOPF = {"nr": "IN-2026-0039", "status": "Eingebucht", "amazonId": "FBA15MM4GTB5", "gruppe": "Eingebucht", "von": "Fillhub", "eta": None, "angelegtAm": "2026-10-06", "stueck": 10000, "kartons": 125, "link": "x"}
POS = {"sku": "1-B-22-LS-SET", "produkt": "Lavendelsäckchen", "stueck": 10000, "offen": 0, "kartons": 125}
anfragen = []
antwort = {}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append(req.full_url)
    return Antwort(json.dumps(antwort["json"]).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(args, json_antwort):
    anfragen.clear()
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


# Bekannte Mengen: wörtlich, mit Stand.
mit = dict(KOPF, amazon={"status": "CLOSED", "lager": "DTM1", "stand": "2026-11-06T07:30:00Z"}, nurBeiAmazon=[], abweichung=True,
           positionen=[dict(POS, versandt=10000, eingebucht=9976, differenz=24, amazonStand="2026-11-06T07:30:00Z", abweichung="Amazon: 9.976 von 10.000 St. eingebucht")])
aus = lauf(["sendung", "FBA15MM4GTB5"], {"sendung": mit, "stand": STAND})
pruefe("Mengen je Position", "versandt 10.000 · eingebucht 9.976 · offen 0" in aus, aus)
pruefe("Abweichung an der Position", "Amazon: 9.976 von 10.000 St. eingebucht" in aus, aus)
pruefe("Stand der Amazon-Daten", "Amazon-Mengen: Stand 06.11.2026 08:30, Status CLOSED, Lager DTM1" in aus, aus)

# Gemeldete 0 bleibt 0.
null_gemeldet = dict(mit, positionen=[dict(POS, versandt=2000, eingebucht=0, differenz=2000, amazonStand="2026-11-06T07:30:00Z", abweichung=None)])
aus = lauf(["sendung", "FBA15MM4GTB5"], {"sendung": null_gemeldet, "stand": STAND})
pruefe("gemeldete 0 ist 0", "versandt 2.000 · eingebucht 0" in aus, aus)

# Fehlfall: keine Zeile vom Abgleich.
ohne = dict(KOPF, amazon=None, nurBeiAmazon=[], abweichung=False, positionen=[dict(POS, versandt=None, eingebucht=None, differenz=None, amazonStand=None, abweichung=None)])
aus = lauf(["sendung", "FBA15MM4GTB5"], {"sendung": ohne, "stand": STAND})
pruefe("unbekannt statt 0", "versandt unbekannt · eingebucht unbekannt" in aus and "eingebucht 0" not in aus, aus)
pruefe("Kopf sagt unbekannt", "Amazon-Mengen: unbekannt" in aus, aus)

# Älteres Tool ohne die Felder: Zeile wie bisher, keine Behauptung.
alt = dict(KOPF, positionen=[POS])
aus = lauf(["sendung", "FBA15MM4GTB5"], {"sendung": alt, "stand": STAND})
pruefe("älteres Tool: keine Mengenzeile", "unbekannt" not in aus and "versandt" not in aus and "1-B-22-LS-SET · Lavendelsäckchen · 10.000 St. · 125 Kartons\n" in aus, aus)

# Direktlieferung: Bestellung kennt die ID, der Abgleich nicht.
direkt = {"amazonId": "FBA15MPF1BNQ", "art": "bestellung", "amazonStatus": None, "lager": None, "stand": None, "bestellungen": ["PO-043-1-10-V-Klebenaht-30"], "abweichung": False,
          "positionen": [{"sku": "10-V-Klebenaht-30", "produkt": "Klebenaht", "versandt": None, "eingebucht": None, "differenz": None, "amazonStand": None, "abweichung": None}]}
aus = lauf(["sendung", "FBA15MPF1BNQ"], {"ohneEinsendung": direkt, "stand": STAND})
pruefe("Direktlieferung nennt die PO", "FBA15MPF1BNQ · keine Einsendung im Tool (bestellung)" in aus and "PO-043-1-10-V-Klebenaht-30" in aus, aus)
pruefe("Direktlieferung unbekannt", "versandt unbekannt · eingebucht unbekannt" in aus, aus)

# Liste: Parameter und Ausgabe.
liste = {"sendungen": [mit], "anzahl": 1, "gekuerzt": False, "mengenUnbekannt": 26, "ohneEinsendung": [dict(direkt, amazonStatus="CLOSED", stand="2026-11-06T07:30:00Z", abweichung=True, positionen=[dict(direkt["positionen"][0], versandt=100, eingebucht=90, abweichung="Amazon: 90 von 100 St. eingebucht")])], "ohneEinsendungAnzahl": 1, "stand": STAND}
aus = lauf(["sendungen", "--abweichung"], liste)
q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(anfragen[0]).query))
pruefe("Anfrage: alle, 200, abweichung", q == {"status": "alle", "limit": "200", "abweichung": "ja"}, str(q))
pruefe("Abweichung Einsendung", "IN-2026-0039 · FBA15MM4GTB5 · Eingebucht" in aus and "1-B-22-LS-SET · versandt 10.000 · eingebucht 9.976 · Amazon: 9.976 von 10.000 St. eingebucht" in aus, aus)
pruefe("Abweichung Direktlieferung", "FBA15MPF1BNQ · bestellung · PO-043-1-10-V-Klebenaht-30" in aus and "versandt 100 · eingebucht 90" in aus, aus)
pruefe("nicht geprüft genannt", "Nicht geprüft: 26 Sendungen" in aus, aus)
aus = lauf(["sendungen", "--abweichung", "--status", "offen"], {"sendungen": [], "anzahl": 0, "mengenUnbekannt": 0, "ohneEinsendung": [], "stand": STAND})
pruefe("--status gewinnt", "status=offen" in anfragen[0], anfragen[0])
pruefe("leer", "Keine Abweichung" in aus and "Nicht geprüft" not in aus, aus)
aus = lauf(["sendungen", "--abweichung"], {"sendungen": [], "anzahl": 0, "stand": STAND})
pruefe("älteres Tool: klare Meldung", "gibt es im Tool noch nicht" in aus, aus)
aus = lauf(["sendungen"], {"sendungen": [dict(KOPF, positionen=[POS])], "anzahl": 1, "stand": STAND})
pruefe("ohne Schalter kein abweichung-Parameter", "abweichung" not in anfragen[0], anfragen[0])

print("Alle grün" if not fehler else f"{fehler} Fehler")
sys.exit(1 if fehler else 0)
