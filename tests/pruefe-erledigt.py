#!/usr/bin/env python3
"""Prüfskript für `erledigt` und `--groesse` (Punkte als Produktivitätsscore, 20.10.2026). Ohne Framework, ohne Netz,
eigenes HOME: urlopen wird ersetzt, die Prüfung liest den Body, den `call` wirklich baut.
Vertrag: POST /api/brain-read/aufgaben mit { titel, groesse, erledigt: true, beschreibung? }, ohne fuer und faellig.
Aufruf: /usr/bin/python3 tests/pruefe-erledigt.py   (Exit 0 = alles grün)"""
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


AUFGABE = {"id": "CB-300", "nummer": 300, "titel": "6 Ads fertig", "prio": 1, "prioText": "niedrig", "fuer": "Jannes",
           "erledigtAm": "2026-10-20T09:00:00Z", "groesse": "gross", "link": "https://company-interface.vercel.app/aufgaben?aufgabe=CB-300"}
anfragen = []
antwort = {"status": 200}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append({"methode": req.get_method(), "url": req.full_url, "body": json.loads(req.data.decode()) if req.data else None})
    if antwort["status"] not in (200, 201):
        roh = json.dumps({"error": antwort["fehler"]}).encode()
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "Fehler", {}, io.BytesIO(roh))
    return Antwort(json.dumps({"aufgabe": AUFGABE, "geaendert": ["groesse"]}).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(befehl, args):
    """Befehl ausführen; Rückgabe (Exit-Code, stdout+stderr, erste Anfrage oder None)."""
    anfragen.clear()
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


# erledigt: Body nach Vertrag, POST auf die Liste, nie fuer oder faellig.
code, out, a = lauf("erledigt", ["--titel", "6 Ads fertig", "--groesse", "gross"])
pruefe("erledigt: Exit 0", code == 0)
pruefe("erledigt: POST auf /api/brain-read/aufgaben", a and a["methode"] == "POST" and a["url"].endswith("/api/brain-read/aufgaben"))
pruefe("erledigt: Body genau titel, groesse, erledigt", a and a["body"] == {"titel": "6 Ads fertig", "groesse": "gross", "erledigt": True})
pruefe("erledigt: Ausgabe nennt Größe und CB-Nummer", "Eingetragen (groß)" in out and "CB-300" in out)
code, out, a = lauf("erledigt", ["--titel", "  Bugfix Login  ", "--groesse", "klein", "--notiz", " PR #12 gemergt "])
pruefe("erledigt mit --notiz: als beschreibung, getrimmt", a and a["body"] == {"titel": "Bugfix Login", "groesse": "klein", "erledigt": True, "beschreibung": "PR #12 gemergt"})
code, out, a = lauf("erledigt", ["--titel", "Briefing", "--groesse", "groß"])
pruefe("„groß“ wird gross", a and a["body"]["groesse"] == "gross")
code, out, a = lauf("erledigt", ["--titel", "Briefing", "--groesse", "Mittel"])
pruefe("Groß/klein egal: Mittel wird mittel", a and a["body"]["groesse"] == "mittel")

# Lokale Fehler: nichts wird gesendet.
for wert in ("riesig", "xl", "3", ""):
    code, out, a = lauf("erledigt", ["--titel", "T", "--groesse", wert])
    pruefe(f"falsche Größe „{wert}“: Exit 2, keine Anfrage", code == 2 and a is None and "--groesse erwartet" in out)
code, out, a = lauf("erledigt", ["--titel", "T"])
pruefe("ohne --groesse: Exit 2, keine Anfrage", code == 2 and a is None and "braucht --groesse" in out)
code, out, a = lauf("erledigt", ["--groesse", "klein"])
pruefe("ohne --titel: Exit 2, keine Anfrage", code == 2 and a is None and "braucht --titel" in out)
code, out, a = lauf("erledigt", ["--titel", "T", "--groesse", "klein", "--fuer", "Mats"])
pruefe("--fuer gibt es bei erledigt nicht: Exit 2, keine Anfrage", code == 2 and a is None and "Unbekannt" in out)
code, out, a = lauf("erledigt", ["--titel", "T", "--groesse", "klein", "--notiz", "  "])
pruefe("leere Notiz: Exit 2, keine Anfrage", code == 2 and a is None)

# Antwort 403 des Tools (erledigt anlegen nur für sich selbst): Text unverändert.
antwort.update(status=403, fehler="Erledigt anlegen geht nur für dich selbst (fuer: ich).")
code, out, a = lauf("erledigt", ["--titel", "T", "--groesse", "klein"])
pruefe("403: Meldung des Tools unverändert", code != 0 and out.strip() == "Erledigt anlegen geht nur für dich selbst (fuer: ich).")
antwort.update(status=200)

# aufgabe-neu --groesse und aufgabe-aendern --groesse.
code, out, a = lauf("aufgabe-neu", ["--titel", "Etikett freigeben", "--faellig", "2026-10-23", "--groesse", "mittel"])
pruefe("aufgabe-neu --groesse: Feld im Body", a and a["body"] == {"titel": "Etikett freigeben", "faellig": "2026-10-23", "groesse": "mittel"})
code, out, a = lauf("aufgabe-neu", ["--titel", "Etikett freigeben"])
pruefe("aufgabe-neu ohne --groesse: Body wie bisher", a and a["body"] == {"titel": "Etikett freigeben"})
code, out, a = lauf("aufgabe-neu", ["--titel", "T", "--groesse", "riesig"])
pruefe("aufgabe-neu falsche Größe: Exit 2, keine Anfrage", code == 2 and a is None)
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--erledigt", "--groesse", "gross"])
pruefe("aufgabe-aendern --erledigt --groesse: PATCH mit beiden", a and a["methode"] == "PATCH" and a["body"] == {"erledigt": True, "groesse": "gross"})
pruefe("aufgabe-aendern: Ausgabe nennt Größe", "Größe groß" in out)
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--groesse", "riesig"])
pruefe("aufgabe-aendern falsche Größe: Exit 2, keine Anfrage", code == 2 and a is None)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
