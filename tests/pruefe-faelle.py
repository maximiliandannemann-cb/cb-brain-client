#!/usr/bin/env python3
"""Prüfskript für `faelle` und `fall` (06.11.2026). Ohne Framework, ohne Netz, eigenes HOME, nur Platzhalter: urlopen wird ersetzt, die
Prüfung liest die Anfrage, die `call` wirklich baut. Aufruf: /usr/bin/python3 tests/pruefe-faelle.py   (Exit 0 = alles grün)"""
import importlib.util, io, json, os, sys, tempfile, urllib.error

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


anfragen = []
antwort = {}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append((req.get_method(), req.full_url))
    if antwort.get("status"):
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "x", {}, io.BytesIO(antwort["roh"]))
    return Antwort(json.dumps(antwort["json"]).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(args, json_antwort=None, status=None, roh=b""):
    anfragen.clear()
    antwort.update(json=json_antwort, status=status, roh=roh)
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


ID, SKU = "FBA-TEST-1", "SKU-TEST-1"
STAND = {"abgerufen": "2026-11-06T08:47:00Z", "daten": "live"}
ARBEIT = [{"nr": "CB-1", "titel": "Test", "fuer": "Testperson", "status": "offen", "link": "x"}]
FALL = {
    "fbaId": ID, "sku": SKU, "stufe": "pruefen", "status": "CLOSED", "lager": "LAGER-TEST", "absender": "Absender-Test", "einsendung": "IN-TEST-1", "bestellungen": [],
    "versandt": 1000, "eingebucht": 900, "rest": 100, "saldo": -70, "vorschlagMenge": 70, "vorschlag": "Rest 100 St., Saldo −70 St.: Vorschlag 70 St. Entscheiden tut ein Mensch.",
    "nachbarn": [
        {"fbaId": "FBA-TEST-2", "status": "RECEIVING", "absender": "Absender-Test", "sendungsdatum": "2026-01-05", "versandt": 500, "eingebucht": 530, "beitrag": 30},
        {"fbaId": "FBA-TEST-3", "status": "CLOSED", "absender": None, "sendungsdatum": "2026-01-06", "versandt": None, "eingebucht": None, "beitrag": None},
    ],
    "tage": {"sendungsdatum": "2026-01-02", "zustellung": "2026-01-10", "zustellungSicher": False, "seitZustellung": 20, "abschluss": "2026-01-20", "reklamierbarAb": None, "fristBis": "2026-03-03", "fristTageRest": 30, "fristQuelle": "Annahme, Drittquelle"},
    "hinweise": ["Reklamierbar ab: unbekannt, steht in Seller Central."],
    "stand": "2026-11-06T08:00:00Z",
    "bestehendeArbeit": ARBEIT,
}
LISTE = {
    "faelle": [FALL], "anzahl": 1, "jeStufe": {"pruefen": 1}, "zaehltNoch": 2, "arbeit": "ok", "stand": STAND,
    "ungeprueft": [{"fbaId": "FBA-TEST-4", "sku": "SKU-TEST-2", "grund": "Mengen fehlen in Amazons Zeile", "status": "CLOSED", "einsendung": None, "bestellungen": ["PO-TEST-1"], "bestehendeArbeit": []}],
}

aus = lauf(["faelle"], LISTE)
pruefe("Lesen: GET auf die Liste", anfragen == [("GET", "http://127.0.0.1:9/api/brain-read/faelle")], str(anfragen))
pruefe("Kopf mit Stufen und zählt noch", aus.splitlines()[0] == "Reklamationsfälle: 1 (pruefen 1). Zählt noch: 2.", aus)
pruefe("Fallzeile wörtlich", f"{ID} · {SKU} · IN-TEST-1 · pruefen · Amazon CLOSED · 900 von 1.000 eingebucht · Rest 100 · Saldo -70\n" in aus, aus)
pruefe("Vorschlag mit beiden Zahlen", "  Rest 100 St., Saldo −70 St.: Vorschlag 70 St." in aus, aus)
pruefe("Hinweis", "  Hinweis: Reklamierbar ab: unbekannt" in aus, aus)
pruefe("Bestehende Arbeit", "  Bestehende Arbeit: CB-1 (Testperson, offen)\n" in aus, aus)
pruefe("Ungeprüft mit Grund, kein Rest", "Ungeprüft, Mengen unbekannt (1):\n  FBA-TEST-4 · SKU-TEST-2 · PO-TEST-1 · Mengen fehlen in Amazons Zeile\n" in aus, aus)
pruefe("Stand", "abgerufen" in aus, aus)

aus = lauf(["faelle"], dict(LISTE, arbeit="kein_recht", faelle=[dict(FALL, bestehendeArbeit=None)]))
pruefe("Ohne Recht: unbekannt, nicht keine", cb.ARBEIT_UNBEKANNT["kein_recht"] in aus and "Bestehende Arbeit: " not in aus and "keine offene Aufgabe" not in aus, aus)
aus = lauf(["faelle"], dict(LISTE, arbeit="fehler", faelle=[dict(FALL, bestehendeArbeit=None)], ungeprueft=[]))
pruefe("Ausfall: unbekannt", cb.ARBEIT_UNBEKANNT["fehler"] in aus and "Ungeprüft" not in aus, aus)
aus = lauf(["faelle"], {"faelle": [], "anzahl": 0, "jeStufe": {}, "zaehltNoch": 0, "ungeprueft": [], "arbeit": "ok", "stand": STAND})
pruefe("Leere Liste", aus.splitlines()[0] == "Reklamationsfälle: 0. Zählt noch: 0.", aus)
aus = lauf(["faelle"], status=404, roh=b"<html>404</html>")
pruefe("Älteres Tool: klarer Satz", cb.FAELLE_FEHLT in aus, aus)
aus = lauf(["faelle", "--x"], LISTE)
pruefe("faelle mit Zuviel: keine Anfrage", "Unbekannt: --x" in aus and not anfragen, aus)

aus = lauf(["fall", ID, SKU], {"fall": FALL, "arbeit": "ok", "stand": STAND})
pruefe("Pfad wörtlich", anfragen == [("GET", f"http://127.0.0.1:9/api/brain-read/faelle/{ID}/{SKU}")], str(anfragen))
pruefe("Lager und Absender", "Lager LAGER-TEST · Absender Absender-Test\n" in aus, aus)
pruefe("Nachbar mit Beitrag", "Nachbar FBA-TEST-2 · RECEIVING · Absender-Test · " in aus and "530 von 500, zählt 30\n" in aus, aus)
pruefe("Nachbar ohne Mengen", "Nachbar FBA-TEST-3 · CLOSED" in aus and "Mengen unbekannt\n" in aus, aus)
pruefe("Tage mit unsicherem Tag", "(unsicher), Abschluss" in aus and "reklamierbar ab unbekannt\n" in aus, aus)
pruefe("Frist mit Quelle, warnt nur", "(Annahme, Drittquelle), warnt nur\n" in aus, aus)
pruefe("Bestehende Arbeit im Einzelabruf", "Bestehende Arbeit: CB-1 (Testperson, offen)\n" in aus, aus)
aus = lauf(["fall", "FBA-TEST-1", "A B/C"], {"keinFall": {"fbaId": ID, "sku": "A B/C", "grund": "Noch nicht zugestellt."}, "stand": STAND})
pruefe("Sonderzeichen kodiert", anfragen[0][1].endswith("/faelle/FBA-TEST-1/A%20B%2FC"), str(anfragen))
pruefe("Kein Fall mit Grund", "kein Fall. Noch nicht zugestellt.\n" in aus, aus)
aus = lauf(["fall", ID, SKU], {"ungeprueft": dict(LISTE["ungeprueft"][0], bestehendeArbeit=ARBEIT), "arbeit": "ok", "stand": STAND})
pruefe("Ungeprüft im Einzelabruf", "Ungeprüft: FBA-TEST-4 · SKU-TEST-2" in aus and "Bestehende Arbeit: CB-1" in aus, aus)
aus = lauf(["fall", ID, "UNBEKANNT"], status=404, roh=json.dumps({"error": "Position nicht gefunden."}).encode())
pruefe("Unbekannt: Text des Tools", aus.strip() == "Position nicht gefunden.", aus)
aus = lauf(["fall", ID, SKU], status=404, roh=b"<html>404</html>")
pruefe("fall, älteres Tool: klarer Satz", cb.FAELLE_FEHLT in aus, aus)
for args in (["fall"], ["fall", ID], ["fall", ID, SKU, "x"], ["fall", ID, "--help"]):
    aus = lauf(args, LISTE)
    pruefe(f"Bedienfehler {args[1:]}: keine Anfrage", "braucht FBA-ID und SKU" in aus and not anfragen, aus)

print("Alle grün" if not fehler else f"{fehler} Fehler")
sys.exit(1 if fehler else 0)
