#!/usr/bin/env python3
"""Prüfskript für `aufgabe-aendern --grund`. Ohne Framework, ohne Netz, eigenes HOME:
urlopen wird ersetzt, die Prüfung liest den PATCH-Body, den `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-grund.py   (Exit 0 = alles grün)"""
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


def pruefe(name: str, ok: bool) -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name)
    fehler += 0 if ok else 1


AUFGABE = {"id": "CB-7", "nummer": 7, "titel": "Test", "prio": 2, "prioText": "mittel", "faellig": "2026-10-23"}
anfragen = []
antwort = {"status": 200}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append({"methode": req.get_method(), "url": req.full_url, "body": json.loads(req.data.decode()) if req.data else None})
    if antwort["status"] != 200:
        roh = json.dumps({"error": antwort["fehler"]}).encode()
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "Bad Request", {}, io.BytesIO(roh))
    return Antwort(json.dumps({"aufgabe": AUFGABE, "geaendert": ["faellig"]}).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(args):
    """aufgabe-aendern ausführen; Rückgabe (Exit-Code, stdout+stderr, Body der Anfrage oder None)."""
    anfragen.clear()
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    code = 0
    try:
        cb.main(["cbtool.py", "aufgabe-aendern"] + list(args))
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if not isinstance(e.code, int) and e.code is not None:
            puffer.write(str(e.code))
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return code, puffer.getvalue(), (anfragen[0]["body"] if anfragen else None)


# Ohne --grund: Body genau wie bisher, kein Feld grund (der Live-Server lehnt unbekannte Felder ab).
code, out, body = lauf(["CB-7", "--faellig", "2026-10-23"])
pruefe("ohne --grund: Exit 0", code == 0)
pruefe("ohne --grund: Body nur faellig", body == {"faellig": "2026-10-23"})
pruefe("ohne --grund: PATCH auf CB-7", anfragen and anfragen[0]["methode"] == "PATCH" and anfragen[0]["url"].endswith("/aufgaben/CB-7"))
code, out, body = lauf(["CB-7", "--faellig-weg"])
pruefe("--faellig-weg ohne --grund: Body faellig null, kein grund", body == {"faellig": None})
code, out, body = lauf(["7", "--notiz", "AB da", "--prio", "3"])
pruefe("andere Felder unverändert", body == {"notiz": "AB da", "prio": 3})

# Mit --grund: Feld im Body, wörtlich (nur Zeilenumbrüche und Ränder wie im Tool normalisiert).
code, out, body = lauf(["CB-7", "--faellig", "2026-10-23", "--grund", "Lieferant hat Betriebsferien"])
pruefe("mit --grund: Exit 0", code == 0)
pruefe("mit --grund: Feld im Body", body == {"faellig": "2026-10-23", "grund": "Lieferant hat Betriebsferien"})
code, out, body = lauf(["CB-7", "--faellig-weg", "--grund", "Projekt gestoppt"])
pruefe("--faellig-weg mit --grund", body == {"faellig": None, "grund": "Projekt gestoppt"})
code, out, body = lauf(["CB-7", "--grund", "  Lieferant\nkrank ", "--faellig", "2026-10-23"])
pruefe("Zeilenumbruch und Ränder wie im Tool", body == {"faellig": "2026-10-23", "grund": "Lieferant krank"})
code, out, body = lauf(["CB-7", "--faellig", "2026-10-23", "--grund", "x" * 300])
pruefe("300 Zeichen gehen durch", body is not None and len(body["grund"]) == 300)

# Lokale Fehler: nichts wird gesendet.
code, out, body = lauf(["CB-7", "--faellig", "2026-10-23", "--grund", "x" * 301])
pruefe("301 Zeichen: lokaler Fehler, Exit 2, keine Anfrage", code == 2 and body is None and "höchstens 300" in out)
code, out, body = lauf(["CB-7", "--faellig", "2026-10-23", "--grund", "\U0001F600" * 151])
pruefe("Zählung wie im Tool (Emoji = 2 Zeichen): 302 > 300", code == 2 and body is None)
code, out, body = lauf(["CB-7", "--faellig", "2026-10-23", "--grund", "  \n "])
pruefe("leerer Grund: lokaler Fehler", code == 2 and body is None and "leer" in out)
code, out, body = lauf(["CB-7", "--prio", "3", "--grund", "egal"])
pruefe("--grund ohne Frist: lokaler Fehler", code == 2 and body is None and "nur zusammen" in out)
code, out, body = lauf(["CB-7", "--faellig", "2026-10-23", "--grund"])
pruefe("--grund ohne Wert: lokaler Fehler", code == 2 and body is None)

# 400 des Tools ohne Grund: klare Meldung mit Hinweis auf --grund.
antwort.update(status=400, fehler="Bitte kurz begründen, warum die Frist sich ändert.")
code, out, body = lauf(["CB-7", "--faellig", "2026-10-30"])
pruefe("400 ohne Grund: Meldung des Tools", code != 0 and "Bitte kurz begründen, warum die Frist sich ändert." in out)
pruefe("400 ohne Grund: Hinweis auf --grund", "--grund" in out and "CB-7" in out)
antwort.update(fehler="Unbekanntes Feld: grund.")
code, out, body = lauf(["CB-7", "--faellig", "2026-10-30", "--grund", "Urlaub"])
pruefe("andere 400: Text des Tools unverändert", code != 0 and out.strip() == "Unbekanntes Feld: grund.")

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
