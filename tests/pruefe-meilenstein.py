#!/usr/bin/env python3
"""Prüfskript für `bestellung-meilenstein` (Tool-Tür A, 29.10.2026). Ohne Framework, ohne Netz, eigenes HOME, Uhr fest (29.10.2026 10:00 Berlin):
urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-meilenstein.py   (Exit 0 = alles grün)"""
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
cb._jetzt = lambda: datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc)

fehler = 0


def pruefe(name: str, ok: bool) -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name)
    fehler += 0 if ok else 1


BELEG = "Mail Stoeffler 27.10. 14:02: Abholung durch K+N, https://mail.google.com/mail/u/0/#inbox/abc"
AENDERUNG = {"vorschau": True, "wiederholt": False, "gebuchtAm": None, "po": "PO-032-1-2-M-TK-120", "schritt": "eingang", "schrittText": "Im Lager angekommen",
             "datum": "2026-10-27", "beleg": BELEG, "statusVorher": "eta_confirmed", "statusNachher": "received",
             "stationenNeu": [{"schritt": "eingang", "schrittText": "Im Lager angekommen", "datum": "2026-10-27", "menge": 1806, "abgeleitet": False}],
             "eingang": {"standort": "fba-de", "direktFba": True, "bestandswirksam": False,
                         "positionen": [{"sku": "2-M-TK-120", "menge": 1806, "bestellt": 1806, "eingegangenVorher": 0, "eingegangenNachher": 1806}]},
             "link": "https://company-interface.vercel.app/movements?ref=PO-032-1-2-M-TK-120"}
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
        cb.main(["cbtool.py", "bestellung-meilenstein"] + list(args))
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if not isinstance(e.code, int) and e.code is not None:
            puffer.write(str(e.code))
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return code, puffer.getvalue(), (anfragen[0] if anfragen else None)


EIN = ["PO-032", "--schritt", "eingang", "--datum", "2026-10-27", "--menge", "1806", "--beleg", BELEG]

# Standard ist die Vorschau: vorschau true, Schlüssel aus dem Inhalt.
code, out, a = lauf(EIN)
pruefe("Vorschau: Exit 0", code == 0)
pruefe("Vorschau: POST an /api/brain-read/bestellungen/PO-032/schritt", a and a["methode"] == "POST" and a["url"].endswith("/api/brain-read/bestellungen/PO-032/schritt"))
pruefe("Vorschau: vorschau true", a and a["body"]["vorschau"] is True)
pruefe("Vorschau: Body", a and {k: v for k, v in a["body"].items() if k not in ("vorschau", "idempotenz_schluessel")} == {"schritt": "eingang", "datum": "2026-10-27", "beleg": BELEG, "menge": 1806})
schluessel = a["body"]["idempotenz_schluessel"] if a else ""
pruefe("Vorschau: Schlüssel aus dem Inhalt", schluessel.startswith("cbtool-") and len(schluessel) == 47)
pruefe("Vorschau: klar als Vorschau, Hinweis auf --ausfuehren", "Vorschau, nichts geschrieben" in out and "--ausfuehren" in out)
pruefe("Vorschau: Status, Eingang, bestandswirksam, Beleg, Link", "Status: eta_confirmed › received" in out and "Amazon FBA (direkt), bestandswirksam nein" in out and "2-M-TK-120: +1806" in out and f"Beleg: {BELEG}" in out and "Link: https://" in out)

# Mit --ausfuehren: gleicher Schlüssel (Wiederholung bucht nicht doppelt), vorschau false.
antwort["json"] = {"aenderung": {**AENDERUNG, "vorschau": False}}
code, out, a = lauf(EIN + ["--ausfuehren"])
pruefe("Ausführen: vorschau false, derselbe Schlüssel wie die Vorschau", a and a["body"]["vorschau"] is False and a["body"]["idempotenz_schluessel"] == schluessel)
pruefe("Ausführen: Eingetragen", code == 0 and out.startswith("Eingetragen: PO-032-1-2-M-TK-120 · Im Lager angekommen am 27.10.2026"))
code, out, a2 = lauf(["po-032", "--beleg", f"  {BELEG}\n", "--ausfuehren", "--menge", "1806", "--datum", "2026-10-27", "--schritt", "Eingang"])
pruefe("Wiederholung mit anderer Schreibweise: derselbe Schlüssel", a2 and a2["body"]["idempotenz_schluessel"] == schluessel)
code, out, a3 = lauf(EIN[:-1] + [BELEG + " (2. Mail)", "--ausfuehren"])
pruefe("anderer Beleg: anderer Schlüssel", a3 and a3["body"]["idempotenz_schluessel"] != schluessel)
antwort["json"] = {"aenderung": {**AENDERUNG, "vorschau": False, "wiederholt": True, "gebuchtAm": "2026-10-29T09:00:00Z"}}
code, out, a = lauf(EIN + ["--ausfuehren"])
pruefe("wiederholt: Schon eingetragen, nichts neu", code == 0 and "Schon eingetragen" in out and "Nichts neu geschrieben" in out)
antwort["json"] = {"aenderung": AENDERUNG}
code, out, a = lauf(EIN + ["--schluessel", "silver-0001-abc", "--ausfuehren"])
pruefe("eigener --schluessel geht durch", a and a["body"]["idempotenz_schluessel"] == "silver-0001-abc")

# Mehrere Positionen, Station.
code, out, a = lauf(["PO-041", "--schritt", "eingang", "--datum", "2026-10-27", "--position", "A-1=20", "--position", "B-1=50", "--standort", "hesterhoff", "--beleg", BELEG])
pruefe("Positionen und Standort im Body", a and a["body"]["positionen"] == [{"sku": "A-1", "menge": 20}, {"sku": "B-1", "menge": 50}] and a["body"]["standort"] == "hesterhoff" and "menge" not in a["body"])
code, out, a = lauf(["PO-040", "--schritt", "konfektionierer-versand", "--datum", "2026-10-27", "--menge", "1000", "--beleg", BELEG])
pruefe("Station: Body", a and a["body"]["schritt"] == "konfektionierer-versand" and a["body"]["menge"] == 1000)

# --help
code, out, a = lauf(["--help"])
pruefe("--help: Hilfe, keine Anfrage", code == 0 and a is None and "--ausfuehren" in out and "--beleg" in out)

# Lokale Fehler: nichts wird gesendet.
for name, args, text in [
    ("ohne --schritt", ["PO-032", "--datum", "2026-10-27", "--menge", "1", "--beleg", BELEG], "--schritt erwartet"),
    ("falscher --schritt", ["PO-032", "--schritt", "versendet", "--datum", "2026-10-27", "--menge", "1", "--beleg", BELEG], "--schritt erwartet"),
    ("ohne --datum", ["PO-032", "--schritt", "fertig", "--menge", "1", "--beleg", BELEG], "--datum"),
    ("Zukunft (Berlin)", ["PO-032", "--schritt", "fertig", "--datum", "2026-10-30", "--menge", "1", "--beleg", BELEG], "in der Zukunft"),
    ("ohne --beleg", ["PO-032", "--schritt", "fertig", "--datum", "2026-10-27", "--menge", "1"], "--beleg fehlt"),
    ("--beleg zu kurz", ["PO-032", "--schritt", "fertig", "--datum", "2026-10-27", "--menge", "1", "--beleg", "Mail 27.1"], "--beleg fehlt"),
    ("--beleg zu lang", ["PO-032", "--schritt", "fertig", "--datum", "2026-10-27", "--menge", "1", "--beleg", "x" * 501], "höchstens 500"),
    ("Station ohne --menge", ["PO-032", "--schritt", "fertig", "--datum", "2026-10-27", "--beleg", BELEG], "braucht --menge"),
    ("--menge 0", ["PO-032", "--schritt", "fertig", "--datum", "2026-10-27", "--menge", "0", "--beleg", BELEG], "ganze Zahl"),
    ("--menge 1,5", ["PO-032", "--schritt", "fertig", "--datum", "2026-10-27", "--menge", "1,5", "--beleg", BELEG], "ganze Zahl"),
    ("Station mit --standort", ["PO-032", "--schritt", "fertig", "--datum", "2026-10-27", "--menge", "1", "--standort", "x", "--beleg", BELEG], "nur bei --schritt eingang"),
    ("Eingang ohne Menge", ["PO-032", "--schritt", "eingang", "--datum", "2026-10-27", "--beleg", BELEG], "braucht --menge"),
    ("Eingang beides", ["PO-032", "--schritt", "eingang", "--datum", "2026-10-27", "--menge", "1", "--position", "A=1", "--beleg", BELEG], "nicht beides"),
    ("--position falsch", ["PO-032", "--schritt", "eingang", "--datum", "2026-10-27", "--position", "A:1", "--beleg", BELEG], "SKU=Menge"),
    ("--position doppelt", ["PO-032", "--schritt", "eingang", "--datum", "2026-10-27", "--position", "A=1", "--position", "a=2", "--beleg", BELEG], "nur einmal"),
    ("--schluessel ungültig", EIN + ["--schluessel", "kurz"], "--schluessel"),
    ("zwei Nummern", ["PO-032", "PO-033", "--schritt", "fertig", "--datum", "2026-10-27", "--menge", "1", "--beleg", BELEG], "genau eine Nummer"),
]:
    code, out, a = lauf(args)
    pruefe(f"{name}: Exit 2, keine Anfrage", code == 2 and a is None and text in out)

# Antworten des Tools: Text unverändert, mit „Nicht eingetragen:“ davor.
for status, text in [
    (400, "Menge größer als offen: 2-M-TK-120 offen 1.806, gemeldet 2.000. Überlieferung nur im Tool."),
    (409, "Schon erfasst: production_done am 27.10.2026 mit 1806 Stück (von Silver). Nichts geschrieben."),
    (409, "Der Schlüssel cbtool-x gehört schon zu einer anderen Anfrage (PO-040, 29.10.2026 10:00). Für eine neue Meldung einen neuen Schlüssel nehmen."),
    (403, "Dieses Konto darf im Tool keine Bestellungen ändern."),
    (503, "Meilenstein und Wareneingang über den Schlüssel sind im Tool noch nicht freigeschaltet (Migration 2026-10-29-agenten-tueren.sql fehlt)."),
]:
    antwort.update(status=status, json={"error": text})
    code, out, a = lauf(EIN)
    pruefe(f"{status}: Text des Tools", code != 0 and out.strip() == f"Nicht eingetragen: {text}")
antwort.update(status=404, roh=b"<html>404</html>")
code, out, a = lauf(EIN)
pruefe("404 ohne Route (älteres Tool): klarer Satz", code != 0 and "gibt es im Tool noch nicht" in out)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
