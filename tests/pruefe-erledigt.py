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
# Uhr vor dem Stichtag der Ergebnis-Pflicht (26.10.2026): diese Fälle prüfen Body und Größe ohne --ergebnis.
# Die Pflicht selbst prüft tests/pruefe-ergebnis.py.
from datetime import datetime, timezone

cb._jetzt = lambda: datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)


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

# Kontext-Hook: Regel für /erledigt-Vorschläge einmal je Sitzung (Stempel ~/.cb-brain/erledigt-regel), echter Prozess.
import subprocess, time

HOOK = os.path.join(os.path.dirname(CBTOOL), "brain-context.py")
REGEL = "**Erledigt:** <Titel> (<Größe>). Eintragen?"


def hook(h: str, prompt: str, sitzung) -> str:
    env = dict(os.environ, HOME=h, CB_NO_AUTOUPDATE="1", CB_TOOL_URL="http://127.0.0.1:9")
    inp = {"prompt": prompt, "hook_event_name": "UserPromptSubmit"}
    if sitzung is not None:
        inp["session_id"] = sitzung
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(inp), capture_output=True, text=True, env=env, timeout=20)
    pruefe(f"Hook Exit 0 ohne stderr ({prompt[:20]!r}, {sitzung})", r.returncode == 0 and not r.stderr)
    return r.stdout


h = tempfile.mkdtemp()
os.makedirs(os.path.join(h, ".cb-brain"))
with open(os.path.join(h, ".cb-brain", "tool-key"), "w") as fh:
    fh.write("cbw_test")
stempel = os.path.join(h, ".cb-brain", "erledigt-regel")
erste = hook(h, "hallo", "S1")
pruefe("Hook: erste Anfrage der Sitzung bringt die Regel", REGEL in erste and "<cb-plugin>Ist in dieser Sitzung" in erste and "nur nach Ja, mit /erledigt" in erste)
pruefe("Hook: Regel nennt Ergebnis und Beleg-Link, nie erfinden", "Ergebnis: <ein Satz" in erste and "Beleg-Link" in erste and "nie erfinden" in erste)
pruefe("Hook: zweite Anfrage derselben Sitzung ohne Regel", REGEL not in hook(h, "und jetzt PO-049 prüfen, bitte mit Stand", "S1"))
pruefe("Hook: Slash-Befehl in derselben Sitzung ohne Regel", REGEL not in hook(h, "/aufgaben", "S1"))
pruefe("Hook: neue Sitzung bekommt die Regel", REGEL in hook(h, "/aufgaben", "S2"))
pruefe("Hook: ohne Sitzungs-ID keine Regel", REGEL not in hook(h, "hallo", None))
pruefe("Hook: ohne Schlüssel keine Regel", REGEL not in hook(tempfile.mkdtemp(), "hallo", "S3"))
with open(stempel, "w") as fh:
    fh.write(f"ALT\t{int(time.time()) - 8 * 86400}\nNEU\t{int(time.time())}\nkaputt\n")
pruefe("Hook: Eintrag älter als 7 Tage zählt nicht", REGEL in hook(h, "hallo", "ALT"))
pruefe("Hook: frischer Eintrag zählt", REGEL not in hook(h, "hallo", "NEU"))
with open(stempel) as fh:
    inhalt = fh.read()
pruefe("Hook: Stempel ohne kaputte Zeile, eigene Datei", "kaputt" not in inhalt and not os.path.exists(os.path.join(h, ".cb-brain", "offen-angeboten")))
with open(stempel, "wb") as fh:
    fh.write(b"\xff\xfe\x00kaputt")
pruefe("Hook: Stempel mit Nicht-UTF-8 wird ersetzt", REGEL in hook(h, "hallo", "S4"))
abschied = hook(h, "danke, das wars", "S5")
pruefe("Hook: Abschied in neuer Sitzung bringt Regel und /offen", REGEL in abschied and "/offen" in abschied)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
