#!/usr/bin/env python3
"""Prüfskript für `einsendung-status` (Tool-Tür E, 30.10.2026). Ohne Framework, ohne Netz, eigenes HOME, Uhr fest (30.10.2026 10:00 Berlin):
urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-einsendung.py   (Exit 0 = alles grün)"""
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


BELEG = "Seller Central 30.10., FBA15MRWCVVG zugestellt 29.10. LEJ5"
GRUND = "Amazon hat die Sendung am 29.10. in LEJ5 angenommen."
AENDERUNG = {"vorschau": True, "wiederholt": False, "gebuchtAm": None, "einsendung": "IN-2026-0046", "amazonShipmentId": "FBA15MRWCVVG",
             "schritt": "eingebucht", "schrittText": "Eingebucht", "datum": "2026-10-29", "beleg": BELEG, "grund": GRUND,
             "statusVorher": "picked_up", "statusVorherText": "Abgeholt", "statusNachher": "checked_in", "statusNachherText": "Eingebucht",
             "quelle": "hesterhoff", "abgeholtAm": "2026-10-27", "eingebuchtAm": "2026-10-29",
             "bewegungenNeu": [{"text": "Transit ab, bei Amazon eingebucht", "sku": "1-GH-1-WG", "menge": -2430, "standort": "transit", "datum": "2026-10-29", "bestandswirksam": True}],
             "link": "https://company-interface.vercel.app/movements?ref=IN-2026-0046"}
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
        cb.main(["cbtool.py", "einsendung-status"] + list(args))
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if not isinstance(e.code, int) and e.code is not None:
            puffer.write(str(e.code))
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return code, puffer.getvalue(), (anfragen[-1] if anfragen else None)


EIN = ["IN-2026-0046", "--schritt", "eingebucht", "--datum", "2026-10-29", "--beleg", BELEG, "--grund", GRUND]

# Standard ist die Vorschau.
code, out, a = lauf(EIN)
pruefe("Vorschau: Exit 0", code == 0)
pruefe("Vorschau: POST an /api/brain-read/einsendungen/IN-2026-0046/status", a and a["methode"] == "POST" and a["url"].endswith("/api/brain-read/einsendungen/IN-2026-0046/status"))
pruefe("Vorschau: Body genau, vorschau true, ohne Schlüssel, eine Anfrage", a and len(anfragen) == 1 and a["body"] == {"schritt": "eingebucht", "datum": "2026-10-29", "beleg": BELEG, "grund": GRUND, "vorschau": True})
pruefe("Vorschau: klar als Vorschau, Hinweis auf --ausfuehren", "Vorschau, nichts geschrieben: IN-2026-0046 (FBA15MRWCVVG) · Eingebucht am 29.10.2026" in out and "--ausfuehren" in out)
pruefe("Vorschau: Status, Bewegung, Beleg, Grund, Link", "Status: Abgeholt › Eingebucht" in out and "1-GH-1-WG −2.430 St. transit am 29.10.2026, bestandswirksam ja" in out
       and f"Beleg: {BELEG}" in out and f"Grund: {GRUND}" in out and "Link: https://" in out)

# Mit --ausfuehren: erst Vorschau, dann Schreiben mit Schlüssel aus dem Inhalt (IN-Nummer aus der Vorschau).
antwort["json"] = {"aenderung": {**AENDERUNG, "vorschau": False}}
code, out, a = lauf(EIN + ["--ausfuehren"])
schluessel = a["body"]["idempotenz_schluessel"] if a else ""
pruefe("Ausführen: erst Vorschau, dann vorschau false mit Schlüssel", len(anfragen) == 2 and anfragen[0]["body"]["vorschau"] is True and a["body"]["vorschau"] is False and schluessel.startswith("cbtool-") and len(schluessel) == 47)
pruefe("Ausführen: Eingetragen", code == 0 and out.startswith("Eingetragen: IN-2026-0046 (FBA15MRWCVVG) · Eingebucht am 29.10.2026"))
code, out, a2 = lauf(["FBA15MRWCVVG"] + EIN[1:] + ["--ausfuehren"])
pruefe("Amazon-ID und IN-Nummer: derselbe Schlüssel", a2 and a2["url"].endswith("/einsendungen/FBA15MRWCVVG/status") and a2["body"]["idempotenz_schluessel"] == schluessel)
code, out, a3 = lauf(EIN[:-1] + [GRUND + " Zweiter Satz.", "--ausfuehren"])
pruefe("anderer Grund: anderer Schlüssel", a3 and a3["body"]["idempotenz_schluessel"] != schluessel)
code, out, a4 = lauf(["IN-2026-0046", "--schritt", "Eingebucht", "--grund", f" {GRUND}\n", "--datum", "2026-10-29", "--beleg", BELEG, "--ausfuehren"])
pruefe("andere Schreibweise: derselbe Schlüssel", a4 and a4["body"]["idempotenz_schluessel"] == schluessel)
antwort["json"] = {"aenderung": {**AENDERUNG, "vorschau": False, "wiederholt": True, "gebuchtAm": "2026-10-30T09:00:00Z"}}
code, out, a = lauf(EIN + ["--ausfuehren"])
pruefe("wiederholt: Schon eingetragen, nichts neu", code == 0 and "Schon eingetragen" in out and "Nichts neu geschrieben" in out)
antwort["json"] = {"aenderung": AENDERUNG}
code, out, a = lauf(EIN + ["--schluessel", "silver-0046-ein", "--ausfuehren"])
pruefe("eigener --schluessel geht durch, eine Anfrage", a and len(anfragen) == 1 and a["body"]["idempotenz_schluessel"] == "silver-0046-ein" and a["body"]["vorschau"] is False)
code, out, a = lauf(["IN-2026-0046", "--schritt", "abgeholt", "--datum", "2026-10-27", "--beleg", BELEG, "--grund", GRUND])
pruefe("abgeholt: Body", a and a["body"]["schritt"] == "abgeholt" and a["body"]["datum"] == "2026-10-27")

code, out, a = lauf(["--help"])
pruefe("--help: Hilfe, keine Anfrage", code == 0 and a is None and "--ausfuehren" in out and "--grund" in out and "--beleg" in out)

# Lokale Fehler: nichts wird gesendet.
for name, args, text in [
    ("ohne --schritt", ["IN-2026-0046", "--datum", "2026-10-29", "--beleg", BELEG, "--grund", GRUND], "--schritt erwartet"),
    ("falscher --schritt", ["IN-2026-0046", "--schritt", "abgeschlossen", "--datum", "2026-10-29", "--beleg", BELEG, "--grund", GRUND], "--schritt erwartet"),
    ("ohne --datum", ["IN-2026-0046", "--schritt", "abgeholt", "--beleg", BELEG, "--grund", GRUND], "--datum"),
    ("Zukunft (Berlin)", ["IN-2026-0046", "--schritt", "abgeholt", "--datum", "2026-10-31", "--beleg", BELEG, "--grund", GRUND], "in der Zukunft"),
    ("ohne --beleg", ["IN-2026-0046", "--schritt", "abgeholt", "--datum", "2026-10-29", "--grund", GRUND], "--beleg fehlt"),
    ("--beleg zu lang", ["IN-2026-0046", "--schritt", "abgeholt", "--datum", "2026-10-29", "--beleg", "x" * 501, "--grund", GRUND], "höchstens 500"),
    ("ohne --grund", ["IN-2026-0046", "--schritt", "abgeholt", "--datum", "2026-10-29", "--beleg", BELEG], "--grund fehlt"),
    ("--grund zu kurz", ["IN-2026-0046", "--schritt", "abgeholt", "--datum", "2026-10-29", "--beleg", BELEG, "--grund", "weil so"], "--grund fehlt"),
    ("--grund zu lang", ["IN-2026-0046", "--schritt", "abgeholt", "--datum", "2026-10-29", "--beleg", BELEG, "--grund", "g" * 301], "höchstens 300"),
    ("--menge gibt es nicht", EIN + ["--menge", "3521"], "--menge gibt es hier nicht"),
    ("--schluessel ungültig", EIN + ["--schluessel", "kurz"], "--schluessel"),
    ("zwei Nummern", ["IN-2026-0046", "IN-2026-0045", "--schritt", "abgeholt", "--datum", "2026-10-29", "--beleg", BELEG, "--grund", GRUND], "genau eine Nummer"),
]:
    code, out, a = lauf(args)
    pruefe(f"{name}: Exit 2, keine Anfrage", code == 2 and a is None and text in out)

# Antworten des Tools: Text unverändert, mit „Nicht eingetragen:“ davor.
for status, text in [
    (409, "Einsendung IN-2026-0046 ist noch nicht abgeholt (Status labels_sent). Erst „abgeholt“ mit dem Abholdatum melden, dann „eingebucht“."),
    (409, "Rückwärts nur über Storno. Einsendung IN-2026-0045 steht auf „Eingebucht“."),
    (409, "Einsendung IN-2026-0046 steht jetzt auf checked_in, erwartet picked_up. Nichts gebucht; bitte neu lesen."),
    (400, "Das Datum 26.10.2026 liegt vor der Abholung am 27.10.2026."),
    (403, "Dieses Konto darf im Tool keine Einsendungen ändern."),
    (404, "Sendung IN-2026-0099 gibt es nicht."),
    (503, "Einsendungs-Status über den Schlüssel ist im Tool noch nicht freigeschaltet (Migration 2026-10-30-einsendung-tuer.sql fehlt)."),
]:
    antwort.update(status=status, json={"error": text})
    antwort.pop("roh", None)
    code, out, a = lauf(EIN)
    pruefe(f"{status}: Text des Tools", code != 0 and out.strip() == f"Nicht eingetragen: {text}")
antwort.update(status=404, roh=b"<html>404</html>")
code, out, a = lauf(EIN)
pruefe("404 ohne Route (älteres Tool): klarer Satz", code != 0 and "gibt es im Tool noch nicht" in out)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
