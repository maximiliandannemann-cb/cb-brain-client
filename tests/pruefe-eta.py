#!/usr/bin/env python3
"""Prüfskript für `bestellung-eta`. Ohne Framework, ohne Netz, eigenes HOME, Uhr fest (29.10.2026 10:00 Berlin):
urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-eta.py   (Exit 0 = alles grün)"""
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


GRUND = "CIS (Pia) meldet am 29.10. Ankunft Regensburg etwa 20.11."
ANTWORT = {"aenderung": {"po": "PO-020-1-1-B-22-LS-SET", "alt": "2026-12-04", "neu": "2026-11-20", "geaendert": True, "grund": GRUND, "quelle": None,
                         "auchFuer": ["Josie-04-1-B-22-LS-SET", "PO-021-1-2-B-22-PLS-SET"], "link": "https://company-interface.vercel.app/movements?ref=PO-020-1-1-B-22-LS-SET"}}
anfragen = []
antwort = {"status": 200, "json": ANTWORT}


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


def lauf(args, ausfuehren=True):
    """bestellung-eta ausführen (Standard mit --ausfuehren; ohne ist es die Vorschau); Rückgabe (Exit-Code, Ausgabe, Anfrage oder None)."""
    args = list(args) + (["--ausfuehren"] if ausfuehren else [])
    anfragen.clear()
    cb.HILFE = "Aufgaben:"
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    code = 0
    try:
        cb.main(["cbtool.py", "bestellung-eta"] + list(args))
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if not isinstance(e.code, int) and e.code is not None:
            puffer.write(str(e.code))
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return code, puffer.getvalue(), (anfragen[0] if anfragen else None)


# Erfolg: POST an /bestellungen/<nr>/eta, Body nur eta und grund (quelle nur, wenn gesetzt), Ausgabe alt › neu, Link.
code, out, a = lauf(["PO-020", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("Erfolg: Exit 0", code == 0)
pruefe("Erfolg: POST an /api/brain-read/bestellungen/PO-020/eta", a and a["methode"] == "POST" and a["url"].endswith("/api/brain-read/bestellungen/PO-020/eta"))
pruefe("Erfolg: Body nur eta und grund", a and a["body"] == {"eta": "2026-11-20", "grund": GRUND})
pruefe("Erfolg: alt › neu", "PO-020-1-1-B-22-LS-SET 04.12.2026 › 20.11.2026" in out)
pruefe("Erfolg: Grund und Link", f"Grund: {GRUND}" in out and "Link: https://company-interface.vercel.app/movements?ref=PO-020-1-1-B-22-LS-SET" in out)
pruefe("Erfolg: gleiche Sendung genannt", "auch für: Josie-04-1-B-22-LS-SET, PO-021-1-2-B-22-PLS-SET" in out)
code, out, a = lauf(["PO-020", "--eta", "2026-11-20", "--grund", f"  {GRUND}\n", "--quelle", " https://mail.google.com/mail/u/0/#inbox/abc "])
pruefe("Quelle im Body, Ränder und Umbruch wie im Tool", a and a["body"] == {"eta": "2026-11-20", "grund": GRUND, "quelle": "https://mail.google.com/mail/u/0/#inbox/abc"})
code, out, a = lauf(["PO-020", "--eta", "2026-10-29", "--grund", "x"])
pruefe("heute (Berlin) geht", code == 0 and a is not None)
antwort["json"] = {"aenderung": {**ANTWORT["aenderung"], "geaendert": False, "alt": "2026-11-20", "auchFuer": []}}
code, out, a = lauf(["PO-021", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("unverändert: klar gesagt", code == 0 and "Unverändert" in out and "steht schon auf 20.11.2026" in out)
antwort["json"] = ANTWORT

# Vorschau (Standard ohne --ausfuehren, 29.10.): vorschau true im Body, klar als Vorschau ausgegeben.
antwort["json"] = {"aenderung": {**ANTWORT["aenderung"], "vorschau": True}}
code, out, a = lauf(["PO-020", "--eta", "2026-11-20", "--grund", GRUND], ausfuehren=False)
pruefe("Vorschau: vorschau true im Body", code == 0 and a and a["body"] == {"eta": "2026-11-20", "grund": GRUND, "vorschau": True})
pruefe("Vorschau: nichts geschrieben, Hinweis auf --ausfuehren", "Vorschau, nichts geschrieben" in out and "--ausfuehren" in out)
antwort["json"] = ANTWORT
antwort.update(status=400, json={"error": "Über den Schlüssel ändert sich nur der Termin. Unbekannt: vorschau. Erlaubt: eta, grund, quelle."})
code, out, a = lauf(["PO-020", "--eta", "2026-11-20", "--grund", GRUND], ausfuehren=False)
pruefe("Vorschau an altem Tool: klarer Satz", code != 0 and "kennt die Vorschau" in out)
antwort.update(status=200, json=ANTWORT)

# Lokale Fehler: nichts wird gesendet.
for name, args, text in [
    ("ohne --eta", ["PO-020", "--grund", GRUND], "--eta"),
    ("falsches Datum", ["PO-020", "--eta", "20.11.2026", "--grund", GRUND], "YYYY-MM-DD"),
    ("ohne --grund", ["PO-020", "--eta", "2026-11-20"], "Bitte kurz begründen, warum der Termin sich ändert."),
    ("leerer --grund", ["PO-020", "--eta", "2026-11-20", "--grund", " \n "], "Bitte kurz begründen"),
    ("--grund zu lang", ["PO-020", "--eta", "2026-11-20", "--grund", "x" * 301], "höchstens 300"),
    ("Vergangenheit (Berlin)", ["PO-020", "--eta", "2026-10-28", "--grund", GRUND], "liegt in der Vergangenheit"),
    ("--quelle mehrzeilig", ["PO-020", "--eta", "2026-11-20", "--grund", GRUND, "--quelle", "a\nb"], "eine Zeile"),
    ("--quelle zu lang", ["PO-020", "--eta", "2026-11-20", "--grund", GRUND, "--quelle", "q" * 501], "höchstens 500"),
    ("zwei Nummern", ["PO-020", "PO-021", "--eta", "2026-11-20", "--grund", GRUND], "genau eine Nummer"),
    ("ohne Nummer", ["--eta", "2026-11-20", "--grund", GRUND], "genau eine Nummer"),
    ("--status gibt es nicht", ["PO-020", "--eta", "2026-11-20", "--grund", GRUND, "--status", "x"], "Unbekannt"),
]:
    code, out, a = lauf(args)
    pruefe(f"{name}: Exit 2, keine Anfrage", code == 2 and a is None and text in out)

# Antworten des Tools: Text unverändert, mit „Nicht geändert:“ davor.
antwort.update(status=400, json={"error": "PO-02 ist nicht eindeutig.", "treffer": ["PO-020-1-1-B-22-LS-SET", "PO-021-1-2-B-22-PLS-SET"]})
code, out, a = lauf(["PO-02", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("mehrdeutig: Möglich: …", code != 0 and out.strip() == "Nicht geändert: PO-02 ist nicht eindeutig. Möglich: PO-020-1-1-B-22-LS-SET, PO-021-1-2-B-22-PLS-SET")
antwort.update(status=409, json={"error": "Bestellung PO-030 hat noch keinen bestätigten Termin (Wunschtermin 04.12.2026). Den ersten Termin trägt man im Tool mit der AB ein."})
code, out, a = lauf(["PO-030", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("409 ohne bestätigten Termin: Text des Tools", code != 0 and "hat noch keinen bestätigten Termin" in out and out.startswith("Nicht geändert:"))
antwort.update(status=400, json={"error": "Bitte kurz begründen, warum der Termin sich ändert."})
code, out, a = lauf(["PO-020", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("400 ohne Grund: Hinweis auf --grund", code != 0 and "--grund" in out)
antwort.update(status=503, json={"error": "ETA ändern über den Schlüssel ist im Tool noch nicht freigeschaltet (Migration 2026-10-29-eta-per-schluessel.sql fehlt)."})
code, out, a = lauf(["PO-020", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("503 vor der Migration: Text des Tools", code != 0 and "noch nicht freigeschaltet" in out)
antwort.update(status=404, roh=b"<html>404</html>")
code, out, a = lauf(["PO-020", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("404 ohne Route (älteres Tool): klarer Satz", code != 0 and "gibt es im Tool noch nicht" in out)
antwort.pop("roh")
antwort.update(status=404, json={"error": "Bestellung PO-099 gibt es nicht."})
code, out, a = lauf(["PO-099", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("404 des Tools: Text des Tools", code != 0 and "Bestellung PO-099 gibt es nicht." in out)
antwort.update(status=403, json={"error": "Dieses Konto darf im Tool keine Bestellungen ändern."})
code, out, a = lauf(["PO-020", "--eta", "2026-11-20", "--grund", GRUND])
pruefe("403: Text des Tools", code != 0 and "keine Bestellungen ändern" in out)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
