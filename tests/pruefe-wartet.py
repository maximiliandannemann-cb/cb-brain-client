#!/usr/bin/env python3
"""Prüfskript für „wartet auf“ (aufgabe-aendern --wartet-auf/--wartet-weg, aufgaben --status wartet, 29.10.2026). Ohne Framework, ohne Netz, eigenes HOME, Uhr fest (29.10.2026 10:00 Berlin):
urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-wartet.py   (Exit 0 = alles grün)"""
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


AUFGABE = {"id": "CB-240", "nummer": 240, "titel": "AB von Lüschow", "prioText": "mittel", "fuer": "Maxi", "faellig": None, "erledigtAm": None,
           "status": "wartet", "wartetAuf": "Lüschow", "wartetSeit": "2026-10-29", "nachfassenAm": "2026-11-03", "nachfassenFaellig": False,
           "link": "https://company-interface.vercel.app/aufgaben?aufgabe=CB-240"}
anfragen = []
antwort = {"status": 200, "json": {"aufgabe": AUFGABE, "geaendert": ["wartet"]}}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append({"methode": req.get_method(), "url": req.full_url, "body": json.loads(req.data.decode()) if req.data else None})
    if antwort["status"] != 200:
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "Fehler", {}, io.BytesIO(json.dumps(antwort["json"]).encode()))
    return Antwort(json.dumps(antwort["json"]).encode())


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
    return code, puffer.getvalue(), (anfragen[0] if anfragen else None)


code, out, a = lauf("aufgabe-aendern", ["CB-240", "--wartet-auf", "  Lüschow "])
pruefe("--wartet-auf: PATCH mit wartet_auf", code == 0 and a and a["methode"] == "PATCH" and a["body"] == {"wartet_auf": "Lüschow"})
pruefe("--wartet-auf: Ausgabe nennt seit und nachfassen", "wartet auf Lüschow seit 29.10., nachfassen 03.11." in out)
antwort["json"] = {"aufgabe": {**AUFGABE, "status": "offen", "wartetAuf": None, "wartetSeit": None, "nachfassenAm": None}, "geaendert": ["wartet"]}
code, out, a = lauf("aufgabe-aendern", ["CB-240", "--wartet-weg"])
pruefe("--wartet-weg: wartet_auf null", code == 0 and a and a["body"] == {"wartet_auf": None} and "liegt wieder bei uns" in out)
antwort["json"] = {"aufgaben": [{**AUFGABE, "nachfassenFaellig": True}], "fuer": "alle"}
code, out, a = lauf("aufgaben", ["--status", "wartet", "--fuer", "alle"])
pruefe("aufgaben --status wartet: Query und Kopf", code == 0 and a and "status=wartet" in a["url"] and "bei anderen liegen" in out)
pruefe("aufgaben --status wartet: nachfassen fällig", "nachfassen fällig 03.11." in out)
for name, befehl, args, text in [
    ("beides", "aufgabe-aendern", ["CB-240", "--wartet-auf", "X", "--wartet-weg"], "schließen sich aus"),
    ("mit --erledigt", "aufgabe-aendern", ["CB-240", "--wartet-auf", "X", "--erledigt", "--ergebnis", "x" * 12], "nicht zusammen mit --erledigt"),
    ("leer", "aufgabe-aendern", ["CB-240", "--wartet-auf", "  "], "1 bis 80"),
    ("zu lang", "aufgabe-aendern", ["CB-240", "--wartet-auf", "x" * 81], "1 bis 80"),
    ("falscher Status", "aufgaben", ["--status", "bei-anderen"], "offen, wartet, erledigt oder alle"),
]:
    code, out, a = lauf(befehl, args)
    pruefe(f"{name}: Exit 2, keine Anfrage", code == 2 and a is None and text in out)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
