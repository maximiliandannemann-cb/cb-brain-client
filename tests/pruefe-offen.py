#!/usr/bin/env python3
"""Prüfskript für den /offen-Hinweis im Kontext-Hook. Ohne Framework, ohne Netz, eigenes HOME.
Aufruf: /usr/bin/python3 tests/pruefe-offen.py   (Exit 0 = alles grün)"""
import importlib.util, json, os, subprocess, sys, tempfile, time

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "brain-context.py")
spec = importlib.util.spec_from_file_location("brain_context", HOOK)
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

fehler = 0


def pruefe(name: str, ok: bool) -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name)
    fehler += 0 if ok else 1


# Review B1: echte Abschiede erkennen, Arbeitsanweisungen mit Abschiedswörtern nicht.
ABSCHIEDE = ["danke, das wars", "Feierabend!", "tschüss", "bis morgen", "ciao",
             "Danke dir, das wars für heute, bis morgen dann!", "ok danke, fertig für heute",
             "Ich mach Schluss für heute, schönen Abend", "super, danke. Schönes Wochenende!", "das war's dann, tschüss"]
ARBEIT = ["Schick das bis morgen an Mats", "Vor Feierabend noch PO-049 prüfen", "Bis morgen muss die Analyse fertig sein",
          "das war es nicht, versuch nochmal", "Ciao Bella ist das Produkt, suche den Lieferanten",
          "mach Schluss mit den Tabellen, nur Fließtext", "Schönes Wochenende-Angebot: 20 % auf alles, prüf die Marge",
          "Tschüssi-Karte als Beileger entwerfen", "Feierabendbier GmbH anschreiben",
          "fertig", "danke", "/offen", "danke, das wars " + "x" * 80]
for p in ABSCHIEDE:
    pruefe(f"Abschied: {p!r}", bc.ist_abschied(p))
for p in ARBEIT:
    pruefe(f"kein Abschied: {p[:50]!r}", not bc.ist_abschied(p))

t = time.time()
for boese in ("tschüss " * 9 + "x", "danke dir " * 8 + "x", " " * 79 + "x", "dir" * 26 + "x"):
    for _ in range(50):
        bc.ABSCHIED.match(boese[-bc.ABSCHIED_MAX:])
pruefe("Regex bleibt billig (200 Läufe mit 80 Zeichen < 1 s)", time.time() - t < 1.0)


def hook(home: str, prompt: str, sitzung) -> str:
    env = dict(os.environ, HOME=home, CB_NO_AUTOUPDATE="1", CB_TOOL_URL="http://127.0.0.1:9")
    inp = {"prompt": prompt, "hook_event_name": "UserPromptSubmit"}
    if sitzung is not None:
        inp["session_id"] = sitzung
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(inp), capture_output=True, text=True, env=env, timeout=20)
    pruefe(f"Exit 0 ohne stderr ({prompt[:20]!r}, {sitzung})", r.returncode == 0 and not r.stderr)
    return r.stdout


def neues_home(schluessel: str = "cbw_test") -> str:
    home = tempfile.mkdtemp()
    os.makedirs(os.path.join(home, ".cb-brain"))
    with open(os.path.join(home, ".cb-brain", "tool-key"), "w") as fh:
        fh.write(schluessel)
    hook(home, "hallo", "start")  # Begrüßung verbrauchen
    return home


home = neues_home()
stempel = os.path.join(home, ".cb-brain", "offen-angeboten")
pruefe("Sitzung A: erster Abschied gibt Hinweis", "/offen" in hook(home, "danke, das wars", "A"))
pruefe("Sitzung A: zweiter Abschied still", "/offen" not in hook(home, "tschüss", "A"))
pruefe("Arbeitsanweisung in Sitzung C still", "/offen" not in hook(home, "Schick das bis morgen an Mats", "C"))
pruefe("Sitzung B parallel: Hinweis", "/offen" in hook(home, "Feierabend!", "B"))
pruefe("Review B2: A nach B bleibt still", "/offen" not in hook(home, "bis morgen", "A"))
pruefe("Sitzung C bekommt den echten Abschied noch", "/offen" in hook(home, "ok danke, fertig für heute", "C"))

with open(stempel, "w") as fh:
    fh.write(f"ALT\t{int(time.time()) - 8 * 86400}\nNEU\t{int(time.time())}\nkaputt\n")
pruefe("Eintrag älter als 7 Tage zählt nicht", "/offen" in hook(home, "tschüss", "ALT"))
pruefe("frischer Eintrag zählt", "/offen" not in hook(home, "tschüss", "NEU"))
with open(stempel) as fh:
    pruefe("Stempel ohne kaputte Zeile", "kaputt" not in fh.read())

with open(stempel, "wb") as fh:
    fh.write(b"\xff\xfe\x00kaputt")
pruefe("Review B5: Stempel mit Nicht-UTF-8 wird ersetzt", "/offen" in hook(home, "tschüss", "D"))
pruefe("danach wieder einmal je Sitzung", "/offen" not in hook(home, "tschüss", "D"))

pruefe("Review B6: ohne Sitzungs-ID kein Hinweis", "/offen" not in hook(home, "tschüss", None))
pruefe("ohne Schlüssel kein Hinweis", "/offen" not in hook(tempfile.mkdtemp(), "danke, das wars", "E"))

env = dict(os.environ, HOME=home, CB_NO_AUTOUPDATE="1")
for roh in ("kein json", "[1,2]", ""):
    r = subprocess.run([sys.executable, HOOK], input=roh, capture_output=True, text=True, env=env, timeout=20)
    pruefe(f"Eingabe {roh!r}: Exit 0, still", r.returncode == 0 and "/offen" not in r.stdout)

h = tempfile.mkdtemp()
os.makedirs(os.path.join(h, ".cb-brain"))
with open(os.path.join(h, ".cb-brain", "tool-key"), "w") as fh:
    fh.write("cbw_neu")
pruefe("Begrüßung nennt /offen", "/offen" in hook(h, "hallo", "F"))

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
