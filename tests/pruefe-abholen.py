#!/usr/bin/env python3
"""Prüfskript für `sendung-abholen` (Tool-Tür T4, 30.10.2026). Ohne Framework, ohne Netz, eigenes HOME, Uhr fest (30.10.2026 10:00 Berlin):
urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-abholen.py   (Exit 0 = alles grün)"""
import importlib.util, io, json, os, sys, tempfile, urllib.error
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
cb._jetzt = lambda: datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)

fehler = 0


def pruefe(name: str, ok: bool) -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name)
    fehler += 0 if ok else 1


BELEG = "Seller Central 30.10., FBA15MP34324 Receiving 3.206/3.206"
GRUND = "Amazon-ID der Tonkarton-Sendung fehlte im Tool (CB-483)."
AENDERUNG = {"vorschau": True, "wiederholt": False, "gebuchtAm": None, "amazonShipmentId": "FBA15MP34324", "abgeholtAm": "2026-10-27", "spediteur": "K+N", "direktFba": True,
             "bestellungen": [{"po": "PO-051-1-1-M-TK-60", "statusVorher": "oc_received", "statusNachher": "in_transit", "statusVorherText": "AB erhalten", "statusNachherText": "In Transit", "umgehaengt": False},
                              {"po": "PO-032-1-2-M-TK-120", "statusVorher": "received", "statusNachher": "received", "statusVorherText": "Geliefert", "statusNachherText": "Geliefert", "umgehaengt": True}],
             "sendung": ["PO-032-1-2-M-TK-120", "PO-051-1-1-M-TK-60"], "beleg": BELEG, "grund": GRUND,
             "link": "https://company-interface.vercel.app/movements?ref=PO-051-1-1-M-TK-60"}
anfragen = []
antwort = {"status": 200, "json": {"aenderung": AENDERUNG}}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append({"methode": req.get_method(), "url": req.full_url, "body": json.loads(req.data.decode()) if req.data else None})
    if antwort["status"] != 200:
        roh = antwort.get("roh") or json.dumps(antwort["json"]).encode()
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "Fehler", {}, io.BytesIO(roh))
    return Antwort(json.dumps(antwort["json"]).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(args):
    anfragen.clear()
    cb.HILFE = "Aufgaben:"
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    code = 0
    try:
        cb.main(["cbtool.py", "sendung-abholen"] + list(args))
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if not isinstance(e.code, int) and e.code is not None:
            puffer.write(str(e.code))
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return code, puffer.getvalue(), (anfragen[-1] if anfragen else None)


EIN = ["PO-051", "PO-032", "--datum", "2026-10-27", "--amazon", "fba15mp34324", "--spediteur", "K+N", "--beleg", BELEG, "--grund", GRUND]

code, out, a = lauf(EIN)
pruefe("Vorschau: Exit 0", code == 0)
pruefe("Vorschau: POST an /api/brain-read/sendungen/abholen", a and a["methode"] == "POST" and a["url"].endswith("/api/brain-read/sendungen/abholen"))
pruefe("Vorschau: Body genau (Nummern in Reihenfolge, Amazon groß), eine Anfrage", a and len(anfragen) == 1 and a["body"] == {"bestellungen": ["PO-051", "PO-032"], "datum": "2026-10-27", "beleg": BELEG, "grund": GRUND, "amazon_shipment_id": "FBA15MP34324", "spediteur": "K+N", "vorschau": True})
pruefe("Vorschau: Kopf, Status je PO, Nachtrag, Sendung, Beleg, Grund", "Vorschau, nichts geschrieben: Abholung 27.10.2026 als FBA15MP34324" in out and "PO-051-1-1-M-TK-60: AB erhalten › In Transit" in out
       and "PO-032-1-2-M-TK-120: Geliefert (nur Nachtrag), in diese Sendung gelegt" in out and "Spediteur: K+N" in out and f"Grund: {GRUND}" in out and "--ausfuehren" in out)

antwort["json"] = {"aenderung": {**AENDERUNG, "vorschau": False}}
code, out, a = lauf(EIN + ["--ausfuehren"])
schluessel = a["body"]["idempotenz_schluessel"] if a else ""
pruefe("Ausführen: erst Vorschau, dann vorschau false mit Schlüssel", len(anfragen) == 2 and anfragen[0]["body"]["vorschau"] is True and a["body"]["vorschau"] is False and schluessel.startswith("cbtool-"))
pruefe("K1: Status je Bestellung aus der Vorschau geht als erwartet mit", a and a["body"].get("erwartet") == {"PO-051-1-1-M-TK-60": "oc_received", "PO-032-1-2-M-TK-120": "received"} and "erwartet" not in anfragen[0]["body"])
pruefe("Ausführen: Eingetragen", code == 0 and out.startswith("Eingetragen: Abholung 27.10.2026 als FBA15MP34324"))
code, out, a2 = lauf(["PO-051-1-1-M-TK-60", "PO-032-1-2-M-TK-120"] + EIN[2:] + ["--ausfuehren"])
pruefe("Kurzform und volle Nummern: derselbe Schlüssel", a2 and a2["body"]["idempotenz_schluessel"] == schluessel)
code, out, a3 = lauf(EIN[:-1] + [GRUND + " Zweiter Satz.", "--ausfuehren"])
pruefe("anderer Grund: anderer Schlüssel", a3 and a3["body"]["idempotenz_schluessel"] != schluessel)
antwort["json"] = {"aenderung": {**AENDERUNG, "vorschau": False, "wiederholt": True, "gebuchtAm": "2026-10-30T09:00:00Z"}}
code, out, a = lauf(EIN + ["--ausfuehren"])
pruefe("wiederholt: Schon eingetragen", code == 0 and "Schon eingetragen" in out)
antwort["json"] = {"aenderung": AENDERUNG}
code, out, a = lauf(EIN + ["--schluessel", "silver-abholen-1", "--ausfuehren"])
pruefe("eigener --schluessel: erst Vorschau, dann Schreiben mit diesem Schlüssel und erwartet", a and len(anfragen) == 2 and anfragen[0]["body"]["vorschau"] is True
       and a["body"]["idempotenz_schluessel"] == "silver-abholen-1" and a["body"]["vorschau"] is False and "erwartet" in a["body"])
antwort["json"] = {"aenderung": {**AENDERUNG, "wiederholt": True, "gebuchtAm": "2026-10-30T09:00:00Z"}}
code, out, a = lauf(EIN + ["--schluessel", "silver-abholen-1", "--ausfuehren"])
pruefe("eigener --schluessel schon gebucht: Vorschau sagt wiederholt, kein zweites Schreiben", len(anfragen) == 1 and "Schon eingetragen" in out)
antwort["json"] = {"aenderung": AENDERUNG}
code, out, a = lauf(["PO-051,PO-032"] + EIN[2:])
pruefe("K5: Komma trennt wie Leerzeichen", a and a["body"]["bestellungen"] == ["PO-051", "PO-032"])
code, out, a = lauf(["PO-051,", "PO-032"] + EIN[2:])
pruefe("K5: „PO-051, PO-032“ geht auch", a and a["body"]["bestellungen"] == ["PO-051", "PO-032"])
code, out, a = lauf(["PO-060", "--datum", "2026-10-27", "--beleg", BELEG, "--grund", GRUND])
pruefe("ohne --amazon und --spediteur: Felder fehlen im Body", a and "amazon_shipment_id" not in a["body"] and "spediteur" not in a["body"])

code, out, a = lauf(["--help"])
pruefe("--help: Hilfe, keine Anfrage", code == 0 and a is None and "--amazon" in out and "--grund" in out)

for name, args, text in [
    ("ohne Bestellung", ["--datum", "2026-10-27", "--beleg", BELEG, "--grund", GRUND], "mindestens eine Bestellung"),
    ("doppelt", ["PO-051", "po-051", "--datum", "2026-10-27", "--beleg", BELEG, "--grund", GRUND], "nur einmal"),
    ("ohne --datum", ["PO-051", "--beleg", BELEG, "--grund", GRUND], "--datum"),
    ("Zukunft", ["PO-051", "--datum", "2026-10-31", "--beleg", BELEG, "--grund", GRUND], "in der Zukunft"),
    ("--amazon falsch", EIN[:4] + ["--amazon", "X123"] + EIN[6:], "Amazon-Shipment-ID wie"),
    ("ohne --beleg", ["PO-051", "--datum", "2026-10-27", "--grund", GRUND], "--beleg fehlt"),
    ("ohne --grund", ["PO-051", "--datum", "2026-10-27", "--beleg", BELEG], "--grund fehlt"),
    ("--grund zu lang", ["PO-051", "--datum", "2026-10-27", "--beleg", BELEG, "--grund", "g" * 301], "höchstens 300"),
    ("unbekannte Option", EIN + ["--menge", "5"], "Unbekannt: --menge"),
    ("--schluessel ungültig", EIN + ["--schluessel", "kurz"], "--schluessel"),
]:
    code, out, a = lauf(args)
    pruefe(f"{name}: Exit 2, keine Anfrage", code == 2 and a is None and text in out)

for status, text in [
    (409, "Die Sendung ist schon als abgeholt am 26.10.2026 erfasst. Nichts geändert."),
    (409, "Stand anders als in der Vorschau: PO-051-1-1-M-TK-60 steht auf in_transit, Vorschau zeigte oc_received. Nichts gebucht; Vorschau neu holen."),
    (400, "Eine Abholung hat ein Ziel: PO-060 geht an Hesterhoff, PO-051-1-1-M-TK-60 an Amazon FBA (direkt)."),
    (403, "Dieses Konto darf im Tool keine Abholungen erfassen."),
    (503, "Abholungen über den Schlüssel sind im Tool noch nicht freigeschaltet (Migration 2026-10-30-sendung-abholen.sql fehlt)."),
]:
    antwort.update(status=status, json={"error": text})
    antwort.pop("roh", None)
    code, out, a = lauf(EIN)
    pruefe(f"{status}: Text des Tools", code != 0 and out.strip() == f"Nicht eingetragen: {text}")
antwort.update(status=405, roh=b"<html>405</html>")
code, out, a = lauf(EIN)
pruefe("405 ohne Route (älteres Tool, GET /sendungen/<nr>): klarer Satz", code != 0 and "gibt es im Tool noch nicht" in out)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
