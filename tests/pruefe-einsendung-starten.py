#!/usr/bin/env python3
"""Prüfskript für `einsendung-starten` und `einsendung-stand` (Tool-Tür einsendung_starten, 06.11.2026). Ohne Framework, ohne
Netz, eigenes HOME, Uhr fest: urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut. Alle Kennungen sind
Platzhalter. Aufruf: /usr/bin/python3 tests/pruefe-einsendung-starten.py   (Exit 0 = alles grün)"""
import http.client, importlib.util, io, json, os, socket, sys, tempfile, urllib.error
from datetime import datetime, timezone

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
cb._jetzt = lambda: datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)

fehler = 0


def pruefe(name: str, ok: bool) -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name)
    fehler += 0 if ok else 1


BELEG = "Slack 06.11., Bitte um Einsendung, https://example.org/nachricht"
ID = "11111111-2222-4333-8444-555555555555"
VORSCHAU = {"vorschau": True, "wiederholt": False, "anlegbar": True, "beleg": BELEG, "lager": "Lager Test", "versandart": "paket",
            "positionen": [{"sku": "SKU-TEST-1", "name": "Testprodukt", "einheiten": 120, "kartons": 5, "paletten": None}], "kartons": 5, "paletten": None, "befunde": [], "hinweise": []}
AUFTRAG = {"id": ID, "lager": "Lager Test", "versandart": "paket", "bereit_ab": "2026-11-09", "gruppe": None,
           "positionen": [{"sku": "SKU-TEST-1", "name": "Testprodukt", "einheiten": 120, "kartons": 5, "paletten": None}], "kartons": 5, "paletten": None,
           "schritt": "transport", "wartet": "freigabe_transport", "braucht_person": True, "pruefliste_nur_im_tool": 2, "stand": "Prüfliste ansehen, dann Transport bestätigen.", "frist": None,
           "pruefliste": [{"feld": "Kartons", "tool": "5", "amazon": "5", "passt": True}, {"feld": "Gewicht", "tool": "80 kg", "amazon": None, "passt": None}],
           "klaerung": None, "abweichung": None, "sendungen": [{"fba_id": "FBA-TEST-1", "transporteur": "Test-Carrier"}], "erstellt_am": "2026-11-06T09:00:00Z"}
ID2 = "22222222-2222-4333-8444-555555555555"
START = {"vorschau": False, "wiederholt": False, "beleg": BELEG, "auftrag_id": ID, "auftrag_ids": [ID], "teilfehler": None, "auftrag": AUFTRAG}
anfragen = []
antwort = {}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    body = json.loads(req.data.decode()) if req.data else None
    anfragen.append({"methode": req.get_method(), "url": req.full_url, "body": body})
    if antwort.get("wurf") and (body is None or not body.get("vorschau") or antwort.get("auch_vorschau")):
        raise antwort["wurf"]
    if antwort.get("status", 200) != 200 and (body is None or not body.get("vorschau") or antwort.get("auch_vorschau")):
        roh = antwort.get("roh") or json.dumps(antwort["json"]).encode()
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "Fehler", {}, io.BytesIO(roh))
    if body is not None and body.get("vorschau"):
        return Antwort(json.dumps({"aenderung": antwort.get("vorschau", VORSCHAU)}).encode())
    return Antwort(json.dumps(antwort.get("json", {})).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(befehl, args):
    anfragen.clear()
    cb.HILFE = "Aufgaben:"
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    code = 0
    try:
        cb.main(["cbtool.py", befehl] + list(args))
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if not isinstance(e.code, int) and e.code is not None:
            puffer.write(str(e.code))
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return code, puffer.getvalue(), (anfragen[-1] if anfragen else None)


def setze(**w):
    antwort.clear()
    antwort.update(w)


EIN = ["--lager", "lager-test", "--bereit-ab", "2026-11-09", "--position", "SKU-TEST-1=120", "--beleg", BELEG]
ANTRAG = {"lagerCode": "lager-test", "bereitAb": "2026-11-09", "positionen": [{"sku": "SKU-TEST-1", "einheiten": 120}]}
PFAD = "/api/brain-read/einsendungen/auftrag"

# Standard ist die Vorschau: genau eine Anfrage, vorschau true, kein Schlüssel.
setze()
code, out, a = lauf("einsendung-starten", EIN)
pruefe("Vorschau: Exit 0, eine Anfrage", code == 0 and len(anfragen) == 1)
pruefe("Vorschau: POST an die Tür", a and a["methode"] == "POST" and a["url"].endswith(PFAD))
pruefe("Vorschau: Body genau so", a and a["body"] == {"antrag": ANTRAG, "beleg": BELEG, "vorschau": True})
pruefe("Vorschau: klar als Vorschau, Hinweis auf --ausfuehren", "Vorschau, nichts gestartet" in out and "--ausfuehren" in out)
pruefe("Vorschau: Lager, SKU, Kartons, Beleg", "Lager Test" in out and "SKU-TEST-1" in out and "120" in out and f"Beleg: {BELEG}" in out)

# Nicht anlegbar: Befunde, auch mit --ausfuehren kein Start.
setze(vorschau={**VORSCHAU, "anlegbar": False, "befunde": [{"art": "menge", "text": "Menge passt nicht auf volle Kartons."}]})
code, out, a = lauf("einsendung-starten", EIN)
pruefe("Nicht anlegbar: Befund steht da, kein Angebot zum Ausführen", code == 0 and "Menge passt nicht" in out and "--ausfuehren" not in out)
code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
pruefe("Nicht anlegbar + --ausfuehren: Exit ungleich 0, nur die Vorschau lief", code != 0 and len(anfragen) == 1 and a["body"]["vorschau"] is True and "Nicht gestartet" in out)

# Ausführen: erst Vorschau, dann Start mit Schlüssel aus dem Inhalt.
setze(json={"aenderung": START})
code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
schluessel = a["body"]["idempotenz_schluessel"] if a else ""
pruefe("Ausführen: Vorschau, dann Start", len(anfragen) == 2 and anfragen[0]["body"]["vorschau"] is True and a["body"]["vorschau"] is False)
pruefe("Ausführen: Schlüssel aus dem Inhalt, gültige Form", schluessel.startswith("cbtool-") and len(schluessel) == 47)
pruefe("Ausführen: Auftrag, Stand, Person ist dran, Weg zum Stand", code == 0 and out.startswith(f"Gestartet: Auftrag {ID}") and "Transport bestätigen" in out and "Eine Person ist dran" in out and f"einsendung-stand {ID}" in out)
code, out, a2 = lauf("einsendung-starten", ["--beleg", f"  {BELEG}\n", "--ausfuehren", "--position", "SKU-TEST-1=120", "--bereit-ab", "2026-11-09", "--lager", "lager-test"])
pruefe("Andere Reihenfolge und Schreibweise: derselbe Schlüssel", a2 and a2["body"]["idempotenz_schluessel"] == schluessel)
code, out, a3 = lauf("einsendung-starten", EIN[:-1] + [BELEG + " (2. Bitte)", "--ausfuehren"])
pruefe("Anderer Beleg: anderer Schlüssel", a3 and a3["body"]["idempotenz_schluessel"] != schluessel)
code, out, a4 = lauf("einsendung-starten", ["--lager", "lager-test", "--bereit-ab", "2026-11-09", "--position", "SKU-TEST-1=240", "--beleg", BELEG, "--ausfuehren"])
pruefe("Andere Menge: anderer Schlüssel", a4 and a4["body"]["idempotenz_schluessel"] != schluessel)
code, out, a5 = lauf("einsendung-starten", EIN + ["--ausfuehren", "--schluessel", "bot-0001-abc"])
pruefe("Eigener --schluessel geht durch", a5 and a5["body"]["idempotenz_schluessel"] == "bot-0001-abc")
setze(json={"aenderung": {**START, "wiederholt": True}})
code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
pruefe("wiederholt: Schon gestartet, nichts neu", code == 0 and "Schon gestartet" in out and "Nichts neu" in out)

# Mehrere Aufträge: alle IDs, je einmal der Weg zum Stand.
setze(json={"aenderung": {**START, "auftrag_ids": [ID, ID2]}})
code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
pruefe("Mehrere Aufträge: beide IDs, je ein Weiter", code == 0 and f"Gestartet: Auftrag {ID}, {ID2}" in out and f"einsendung-stand {ID}" in out and f"einsendung-stand {ID2}" in out)
setze(json={"aenderung": {**START, "auftrag_ids": [ID], "teilfehler": "Für SKU-TEST-2 läuft schon eine Einsendung."}})
code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
pruefe("Teilfehler: läuft, kein „Nicht gestartet“", code == 0 and "Teilweise gestartet" in out and "SKU-TEST-2" in out and "Nicht gestartet" not in out)

# Beim Ausführen: Ausgang unklar statt „Nicht gestartet“, wo der Start gelaufen sein kann.
for status in (409, 500, 502, 503, 504):
    setze(status=status, json={"error": "Fehler des Tools."})
    code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
    pruefe(f"Ausführen {status}: Ausgang unklar", code != 0 and out.strip() == "Ausgang unklar, nicht neu starten: Fehler des Tools." and "Nicht gestartet" not in out)
setze(status=502, json={"error": "Ausgang unklar, nicht neu starten: Zeitlimit"})
code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
pruefe("Text des Tools sagt es schon: nicht doppelt", out.strip() == "Ausgang unklar, nicht neu starten: Zeitlimit")
for status in (403, 422, 423):
    setze(status=status, json={"error": "Abgelehnt vom Tool."})
    code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
    pruefe(f"Ausführen {status}: Nicht gestartet", code != 0 and out.strip() == "Nicht gestartet: Abgelehnt vom Tool.")
for name, wurf in (("Lese-Timeout", socket.timeout("timed out")), ("Verbindung weg", ConnectionResetError("reset")), ("Antwort abgerissen", http.client.IncompleteRead(b""))):
    setze(wurf=wurf)
    code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
    pruefe(f"Ausführen {name}: Ausgang unklar, ohne Traceback", code != 0 and out.startswith("Ausgang unklar, nicht neu starten") and "Traceback" not in out)
setze(wurf=urllib.error.URLError("nicht erreichbar"))
code, out, a = lauf("einsendung-starten", EIN + ["--ausfuehren"])
pruefe("Ausführen, Tool nicht erreichbar: Ausgang unklar", code != 0 and out.startswith("Ausgang unklar, nicht neu starten"))
setze(wurf=socket.timeout("timed out"), auch_vorschau=True)
code, out, a = lauf("einsendung-starten", EIN)
pruefe("Vorschau, Timeout: Nicht gestartet, ohne Traceback", code != 0 and out.startswith("Nicht gestartet"))
setze(wurf=socket.timeout("timed out"), auch_vorschau=True)
code, out, a = lauf("einsendung-stand", [ID])
pruefe("Stand, Timeout: ohne Traceback", code != 0 and "antwortet nicht" in out)

# Positionen: mehrere, MHD, Reihenfolge egal.
setze()
code, out, a = lauf("einsendung-starten", ["--lager", "lager-test", "--bereit-ab", "2026-11-09", "--position", "SKU-TEST-2=60@2028-01-31", "--position", "SKU-TEST-1=120", "--beleg", BELEG])
pruefe("Mehrere Positionen sortiert, MHD im Body", a and a["body"]["antrag"]["positionen"] == [{"sku": "SKU-TEST-1", "einheiten": 120}, {"sku": "SKU-TEST-2", "einheiten": 60, "mhd": "2028-01-31"}])

# --help
code, out, a = lauf("einsendung-starten", ["--help"])
pruefe("--help: Hilfe, keine Anfrage", code == 0 and a is None and "--ausfuehren" in out and "--beleg" in out)

# Lokale Fehler: nichts wird gesendet.
for name, args, text in [
    ("ohne --lager", EIN[2:], "--lager"),
    ("ohne --bereit-ab", EIN[:2] + EIN[4:], "--bereit-ab"),
    ("--bereit-ab falsch", ["--lager", "lager-test", "--bereit-ab", "09.11.2026", "--position", "SKU-TEST-1=120", "--beleg", BELEG], "--bereit-ab"),
    ("ohne --position", EIN[:4] + EIN[6:], "--position"),
    ("--position falsch", ["--lager", "lager-test", "--bereit-ab", "2026-11-09", "--position", "SKU-TEST-1:120", "--beleg", BELEG], "SKU=Menge"),
    ("--position 0", ["--lager", "lager-test", "--bereit-ab", "2026-11-09", "--position", "SKU-TEST-1=0", "--beleg", BELEG], "SKU=Menge"),
    ("--position doppelt", ["--lager", "lager-test", "--bereit-ab", "2026-11-09", "--position", "SKU-TEST-1=1", "--position", "sku-test-1=2", "--beleg", BELEG], "nur einmal"),
    ("ohne --beleg", EIN[:6], "--beleg"),
    ("--beleg zu kurz", EIN[:7] + ["kurz"], "--beleg"),
    ("--schluessel ungültig", EIN + ["--schluessel", "kurz"], "--schluessel"),
    ("unbekanntes Argument", EIN + ["--freigeben"], "Unbekannt"),
]:
    code, out, a = lauf("einsendung-starten", args)
    pruefe(f"{name}: Exit 2, keine Anfrage", code == 2 and a is None and text in out)

# Antworten des Tools: Text unverändert, mit „Nicht gestartet:“ davor.
for status, text in [
    (403, "Dieses Konto darf im Tool keine Einsendungen starten."),
    (409, "Für dieses Produkt läuft an diesem Lager schon eine Einsendung."),
    (422, "Menge passt nicht auf volle Kartons."),
    (503, "Einsendungen anlegen ist im Tool noch nicht freigeschaltet."),
]:
    setze(status=status, json={"error": text}, auch_vorschau=True)
    code, out, a = lauf("einsendung-starten", EIN)
    pruefe(f"{status}: Text des Tools", code != 0 and out.strip() == f"Nicht gestartet: {text}")
setze(status=404, roh=b"<html>404</html>", auch_vorschau=True)
code, out, a = lauf("einsendung-starten", EIN)
pruefe("404 ohne Route (älteres Tool): klarer Satz", code != 0 and "gibt es im Tool noch nicht" in out)

# einsendung-stand
setze(json={"auftrag": AUFTRAG})
code, out, a = lauf("einsendung-stand", [ID])
pruefe("Stand: GET je Auftrag, kein Body", code == 0 and a["methode"] == "GET" and a["body"] is None and a["url"].endswith(f"{PFAD}/{ID}"))
pruefe("Stand: Stand, Person, Prüfliste mit passt und nicht prüfbar, FBA", "Transport bestätigen" in out and "Eine Person ist dran" in out and "Kartons" in out and "passt" in out and "nicht prüfbar" in out and "FBA-TEST-1" in out and "2 Zeilen nur im Tool" in out)
setze(json={"auftrag": {**AUFTRAG, "wartet": "klaerung", "pruefliste": None, "klaerung": "Amazon lehnt die Etiketten ab."}})
code, out, a = lauf("einsendung-stand", [ID])
pruefe("Stand: Klärung", code == 0 and "Klärung: Amazon lehnt die Etiketten ab." in out)
setze(json={"auftrag": {**AUFTRAG, "wartet": "amazon", "braucht_person": False, "pruefliste": None}})
code, out, a = lauf("einsendung-stand", [ID])
pruefe("Stand: niemand muss etwas tun", code == 0 and "Eine Person ist dran" not in out)
code, out, a = lauf("einsendung-stand", [])
pruefe("Stand ohne Nummer: Exit 2", code == 2 and a is None)
setze(status=404, json={"error": "Auftrag nicht gefunden."})
code, out, a = lauf("einsendung-stand", [ID])
pruefe("Stand: Auftrag unbekannt, Text des Tools", code != 0 and "Auftrag nicht gefunden." in out)
setze(status=404, roh=b"<html>404</html>")
code, out, a = lauf("einsendung-stand", [ID])
pruefe("Stand: 404 ohne Route", code != 0 and "gibt es im Tool noch nicht" in out)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
