#!/usr/bin/env python3
"""Prüfskript für `--ergebnis` (Ergebnis beim Erledigen, Tool-Issue #437, Pflicht ab Mo 26.10.2026 00:00 Berlin).
Ohne Framework, ohne Netz, eigenes HOME: urlopen wird ersetzt, die Uhr steht fest (cb._jetzt).
Vertrag: PATCH /api/brain-read/aufgaben/<nr> und POST /api/brain-read/aufgaben mit `ergebnis` (10 bis 2000 Zeichen).
Aufruf: /usr/bin/python3 tests/pruefe-ergebnis.py   (Exit 0 = alles grün)"""
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

fehler = 0


def pruefe(name: str, ok: bool) -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name)
    fehler += 0 if ok else 1


ERG = "PR #442 gemergt: https://github.com/x/company-interface/pull/442"
FEHLT = "Ergebnis fehlt: ein Satz, was herauskam und wo es liegt (mind. 10 Zeichen)."
AUFGABE = {"id": "CB-300", "nummer": 300, "titel": "Ergebnis-Pflicht bauen", "prio": 2, "prioText": "mittel", "fuer": "Maxi",
           "erledigtAm": "2026-10-26T09:00:00Z", "groesse": "gross", "ergebnis": ERG,
           "link": "https://company-interface.vercel.app/aufgaben?aufgabe=CB-300"}
anfragen = []
antwort = {"status": 200, "geaendert": ["erledigt", "ergebnis"]}


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
    if req.get_method() == "GET" and req.full_url.split("?")[0].endswith("/aufgaben"):
        return Antwort(json.dumps({"aufgaben": [AUFGABE, dict(AUFGABE, id="CB-301", nummer=301, ergebnis=None)], "fuer": "Maxi"}).encode())
    return Antwort(json.dumps({"aufgabe": AUFGABE, "geaendert": antwort["geaendert"]}).encode())


cb.urllib.request.urlopen = falsches_urlopen
VORHER = datetime(2026, 10, 25, 22, 59, 59, tzinfo=timezone.utc)  # So 25.10. 23:59:59 Berlin
AB = datetime(2026, 10, 25, 23, 0, 0, tzinfo=timezone.utc)  # Mo 26.10. 00:00 Berlin
uhr = {"jetzt": AB}
cb._jetzt = lambda: uhr["jetzt"]


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


pruefe("Text wie im Tool", cb.ERGEBNIS_FEHLT == FEHLT)
pruefe("Stichtag = 2026-10-25T23:00Z wie im Tool", cb.ERGEBNIS_PFLICHT_AB.isoformat() == "2026-10-25T23:00:00+00:00")

# Fehlt: ab Stichtag lokal abgelehnt, nichts gesendet, gleicher Text.
for befehl, args in (("aufgabe-aendern", ["CB-300", "--erledigt"]), ("erledigt", ["--titel", "T", "--groesse", "klein"])):
    code, out, a = lauf(befehl, args)
    pruefe(f"{befehl} ohne --ergebnis ab Stichtag: Exit 2, keine Anfrage, Text des Tools", code == 2 and a is None and FEHLT in out and "--ergebnis" in out)
uhr["jetzt"] = VORHER
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--erledigt"])
pruefe("vor dem Stichtag: ohne --ergebnis gesendet, Body wie bisher", code == 0 and a and a["body"] == {"erledigt": True})
code, out, a = lauf("erledigt", ["--titel", "T", "--groesse", "klein"])
pruefe("vor dem Stichtag: erledigt ohne --ergebnis gesendet", code == 0 and a and a["body"] == {"titel": "T", "groesse": "klein", "erledigt": True})
uhr["jetzt"] = AB

# Zu kurz, nur Leerraum, zu lang: Bedienfehler, nichts gesendet.
for wert, name in (("zu kurz", "9 Zeichen"), ("          ", "nur Leerzeichen"), ("\n\n  abc  \n", "Umbrüche und 3 Zeichen"), ("x" * 2001, "2001 Zeichen")):
    code, out, a = lauf("aufgabe-aendern", ["CB-300", "--erledigt", "--ergebnis", wert])
    pruefe(f"--ergebnis {name}: Exit 2, keine Anfrage", code == 2 and a is None)
code, out, a = lauf("erledigt", ["--titel", "T", "--groesse", "klein", "--ergebnis", "kurz"])
pruefe("erledigt --ergebnis zu kurz: Exit 2, Text des Tools", code == 2 and a is None and FEHLT in out)
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--offen", "--ergebnis", ERG])
pruefe("--ergebnis mit --offen: Exit 2, keine Anfrage", code == 2 and a is None)

# Ok: Body nach Vertrag, normalisiert (Umbrüche zu Leerzeichen, außen getrimmt); 10 Zeichen reichen, Emoji zählt 1.
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--erledigt", "--ergebnis", f"  PR #442 gemergt:\n{ERG[17:]}  "])
pruefe("aufgabe-aendern --erledigt --ergebnis: PATCH mit beiden", code == 0 and a["methode"] == "PATCH" and a["body"] == {"erledigt": True, "ergebnis": ERG})
pruefe("Ausgabe: erledigt, Ergebnis gespeichert, Ergebnis-Zeile", "erledigt, Ergebnis gespeichert" in out and f"Ergebnis: {ERG}" in out)
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--erledigt", "--ergebnis", "1234567890"])
pruefe("genau 10 Zeichen: gesendet", code == 0 and a["body"]["ergebnis"] == "1234567890")
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--erledigt", "--ergebnis", "🙂" * 10])
pruefe("10 Emoji = 10 Zeichen wie Postgres: gesendet", code == 0 and a["body"]["ergebnis"] == "🙂" * 10)
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--ergebnis", "Korrektur: Link im Drive ergänzt"])
pruefe("--ergebnis allein (erledigte Aufgabe ändern): PATCH nur ergebnis", code == 0 and a["body"] == {"ergebnis": "Korrektur: Link im Drive ergänzt"})
code, out, a = lauf("erledigt", ["--titel", "6 Ads fertig", "--groesse", "gross", "--ergebnis", "6 Ads live, Ordner im Drive: https://drive.google.com/x"])
pruefe("erledigt --ergebnis: POST mit ergebnis", code == 0 and a["methode"] == "POST" and a["body"] == {"titel": "6 Ads fertig", "groesse": "gross", "erledigt": True, "ergebnis": "6 Ads live, Ordner im Drive: https://drive.google.com/x"})
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--offen"])
pruefe("wieder öffnen ohne ergebnis im Body (Tool lässt es stehen)", code == 0 and a["body"] == {"erledigt": False})

# 400 des Tools (Server maßgeblich, z. B. falsche Uhr): klarer nächster Schritt.
antwort.update(status=400, fehler=FEHLT + " (Plugin aktualisieren: Claude Code neu starten)")
uhr["jetzt"] = VORHER
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--erledigt"])
pruefe("400 ohne Ergebnis: Nicht erledigt + nachfragen", code != 0 and out.startswith("Nicht erledigt: " + FEHLT) and "--ergebnis" in out)
code, out, a = lauf("erledigt", ["--titel", "T", "--groesse", "klein"])
pruefe("400 bei erledigt: dieselbe Meldung", code != 0 and out.startswith("Nicht erledigt: " + FEHLT))
antwort.update(status=400, fehler="ergebnis geht nur beim Erledigen (erledigt: true) oder bei erledigten Aufgaben.")
code, out, a = lauf("aufgabe-aendern", ["CB-300", "--ergebnis", ERG])
pruefe("400 an offener Aufgabe: Text des Tools unverändert", code != 0 and out.strip() == "ergebnis geht nur beim Erledigen (erledigt: true) oder bei erledigten Aufgaben.")
antwort.update(status=200)
uhr["jetzt"] = AB

# Lesen: aufgabe CB-123 und aufgaben --status erledigt zeigen das Ergebnis.
code, out, a = lauf("aufgabe", ["CB-300"])
pruefe("aufgabe CB-300: Zeile „Ergebnis: …“", code == 0 and f"Ergebnis: {ERG}" in out)
code, out, a = lauf("aufgaben", ["--status", "erledigt"])
pruefe("aufgaben --status erledigt: Ergebnis unter der Zeile", code == 0 and f"\n    Ergebnis: {ERG}" in out and out.count("Ergebnis:") == 1)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
