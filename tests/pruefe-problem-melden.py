#!/usr/bin/env python3
"""Prüfskript für `problem-melden` und die Hilfe (11.11.2026). Ohne Framework, ohne Netz, eigenes HOME: urlopen wird
ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-problem-melden.py   (Exit 0 = alles grün)"""
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


NEU = {"meldung": {"id": "iss-bot-1-abcdef", "titel": "Lexi: Kasse liefert 403", "neu": True, "heuteGemeldet": 1, "heuteErlaubt": 10},
       "github": {"uebertragen": False, "grund": "nicht eingerichtet"}}
anfragen = []
antwort = {"status": 201, "json": NEU}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append({"methode": req.get_method(), "url": req.full_url, "body": json.loads(req.data.decode()) if req.data else None})
    if antwort["status"] >= 400:
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "Fehler", {}, io.BytesIO(json.dumps(antwort["json"]).encode()))
    return Antwort(json.dumps(antwort["json"]).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(argv):
    anfragen.clear()
    cb.HILFE = "Aufgaben:"
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    code = 0
    try:
        cb.main(["cbtool.py"] + list(argv))
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if not isinstance(e.code, int) and e.code is not None:
            puffer.write(str(e.code))
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return code, puffer.getvalue(), (anfragen[-1] if anfragen else None)


# --- Hilfe: Exit 0, keine Anfrage
for h in ("--help", "-h", "help"):
    code, out, a = lauf([h])
    pruefe(f"{h}: Exit 0, Übersicht mit Problem", code == 0 and a is None and "problem-melden" in out and "Ware:" in out)
code, out, a = lauf([])
pruefe("ohne Befehl: Übersicht, Exit 0", code == 0 and a is None)
code, out, a = lauf(["gibt-es-nicht"])
pruefe("unbekannter Befehl: weiter Exit 2", code == 2 and a is None)
code, out, a = lauf(["problem-melden", "--help"])
pruefe("problem-melden --help: Exit 0, Satz zu Daten und Grenzen", code == 0 and a is None and "Nur Text. Keine Schlüssel, keine Mailinhalte, keine Finanz- oder Personendaten. Höchstens 10 Meldungen am Tag; gleiche Meldung binnen 24 Stunden wird angehängt." in out)

# --- Senden
code, out, a = lauf(["problem-melden", "--titel", " Kasse liefert 403 ", "--text", "Beim Abruf der Kasse kommt 403.", "--befehl", "cbtool.py kasse", "--status", "403"])
pruefe("POST /api/brain-read/problem mit genau den Feldern", code == 0 and a["methode"] == "POST" and a["url"].endswith("/api/brain-read/problem")
       and a["body"] == {"titel": "Kasse liefert 403", "text": "Beim Abruf der Kasse kommt 403.", "befehl": "cbtool.py kasse", "status": 403})
pruefe("Ausgabe neu: Titel, Tool-ID, nur im Tool, Zähler", "Gemeldet (neu): Lexi: Kasse liefert 403" in out and "Tool-ID: iss-bot-1-abcdef" in out and "Nur im Tool." in out and "Heute gemeldet: 1 von 10." in out)
code, out, a = lauf(["problem-melden", "--titel", "Funktion fehlt", "--text", "Ich brauche einen Weg für X.", "--art", "funktion"])
pruefe("--art wird gesendet, ohne befehl/status", a["body"] == {"titel": "Funktion fehlt", "text": "Ich brauche einen Weg für X.", "art": "funktion"})

antwort["json"] = {"meldung": {**NEU["meldung"], "neu": False, "heuteGemeldet": 2},
                   "github": {"uebertragen": True, "url": "https://github.com/x/y/issues/42", "nummer": 42}}
antwort["status"] = 200
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert 403", "--text", "Wieder 403 bei der Kasse."])
pruefe("Ausgabe angehängt mit GitHub-Link", code == 0 and "Angehängt an die bestehende Meldung" in out and "GitHub: https://github.com/x/y/issues/42" in out)
antwort["json"] = {"meldung": NEU["meldung"], "github": {"uebertragen": False, "status": 500}}
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert 403", "--text", "Wieder 403 bei der Kasse."])
pruefe("GitHub gescheitert: nur im Tool mit Status", "Nur im Tool (Übertragung an GitHub gescheitert, Status 500)." in out)

# --- Schlüssel im Text: nie gesendet
for feld in ("--titel", "--text", "--befehl"):
    argv = {"--titel": "Kasse liefert 403", "--text": "Beim Abruf der Kasse kommt 403.", "--befehl": "cbtool.py kasse"}
    argv[feld] = argv[feld] + " CBW_abcd1234efgh"
    code, out, a = lauf(["problem-melden"] + [x for kv in argv.items() for x in kv])
    pruefe(f"cbw_ in {feld}: Exit 2, nichts gesendet", code == 2 and a is None and "wie ein Schlüssel" in out and "CBW_abcd1234efgh" not in out)

# --- Bedienfehler
for name, argv in [("ohne --text", ["--titel", "Kasse liefert 403"]), ("ohne --titel", ["--text", "Beim Abruf kommt 403."]),
                   ("--status keine Zahl", ["--titel", "abcde", "--text", "x" * 12, "--status", "vier"]),
                   ("--art falsch", ["--titel", "abcde", "--text", "x" * 12, "--art", "wunsch"]),
                   ("unbekannte Option", ["--titel", "abcde", "--text", "x" * 12, "--prio", "3"])]:
    code, out, a = lauf(["problem-melden"] + argv)
    pruefe(f"{name}: Exit 2, keine Anfrage, Hilfe Problem", code == 2 and a is None and "Problem:" in out)

# --- Tool antwortet mit Fehler
antwort.update(status=429, json={"error": "Heute schon 10 Meldungen von diesem Konto. Morgen wieder, oder Max direkt fragen. Nichts gespeichert."})
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert 403", "--text", "Beim Abruf kommt 403."])
pruefe("429: Satz des Tools wörtlich", code == 1 and "Heute schon 10 Meldungen" in out)
antwort.update(status=404, json={"error": "Nicht gefunden."})
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert 403", "--text", "Beim Abruf kommt 403."])
pruefe("404: Route fehlt, eigener Satz", code == 1 and "gibt es im Tool noch nicht" in out)

print("\n" + ("alles grün" if fehler == 0 else f"{fehler} Fehler"))
sys.exit(1 if fehler else 0)
