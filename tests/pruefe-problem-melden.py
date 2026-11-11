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

antwort.update(status=403, json={"error": "Über den Schlüssel melden nur Bots mit eigenem Konto. Personen melden im Tool unter /feedback."})
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert 403", "--text", "Beim Abruf kommt 403."])
pruefe("403 Personen-Schlüssel: Satz des Tools wörtlich, Exit 1",
       code == 1 and a is not None and "Über den Schlüssel melden nur Bots mit eigenem Konto. Personen melden im Tool unter /feedback." in out)
antwort.update(status=503, json={"error": "Problem melden ist noch nicht freigeschaltet (Migration bot_meldung_melden fehlt). Bitte Max direkt Bescheid geben."})
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert 403", "--text", "Beim Abruf kommt 403."])
pruefe("503 vor der Migration: Satz des Tools wörtlich, Exit 1", code == 1 and a is not None and "noch nicht freigeschaltet" in out)

# --- Geheimnis-Muster: gemeinsame Liste mit dem Tool (company-interface src/lib/geheimnis-muster.json), eingebaut in cbtool.py
import hashlib, pwd, shutil, subprocess

MUSTER_JSON = os.path.join(os.path.dirname(CBTOOL), "geheimnis-muster.json")
# Gepinnte SHA-256 der Muster-Liste: nur gemeinsam mit company-interface src/lib/geheimnis-muster.json ändern
# (dort pinnt die Prüfung dieselbe Zahl; eingebaute Liste, Spiegel-Datei und Quelle sind Byte für Byte gleich).
MUSTER_SHA256 = "beee4cca02957149e7ed1346a276de7b72e2d7c8eeeca03431a739b30fb1e967"
eingebaut = cb.GEHEIMNIS_MUSTER_JSON.encode("utf-8")
with open(MUSTER_JSON, "rb") as fh:
    muster_bytes = fh.read()
pruefe("eingebaute Liste (GEHEIMNIS_MUSTER_JSON): SHA-256 gleich der gepinnten", hashlib.sha256(eingebaut).hexdigest() == MUSTER_SHA256)
pruefe("eingebaute Liste Byte für Byte gleich scripts/geheimnis-muster.json", eingebaut == muster_bytes)
pruefe("cbtool.py liest keine Muster-Datei mehr", not hasattr(cb, "GEHEIMNIS_MUSTER_DATEI"))
kandidaten = []
if os.environ.get("CB_COMPANY_INTERFACE_DIR"):
    kandidaten.append(os.environ["CB_COMPANY_INTERFACE_DIR"])
echtes_home = pwd.getpwuid(os.getuid()).pw_dir  # HOME ist oben auf ein Testverzeichnis umgebogen
for wt in ("wt-bot-meldung", "company-interface"):
    kandidaten.append(os.path.join(echtes_home, "projects", "cleverbrands", wt))
ci = next((d for d in kandidaten if os.path.isfile(os.path.join(d, "src", "lib", "geheimnis-muster.json"))), None)
if ci:
    with open(os.path.join(ci, "src", "lib", "geheimnis-muster.json"), "rb") as fh:
        pruefe(f"eingebaute Liste Byte für Byte gleich {ci}/src/lib/geheimnis-muster.json", fh.read() == eingebaut)
else:
    print("übersprungen: Byte-Vergleich mit company-interface (keine Kopie gefunden; CB_COMPANY_INTERFACE_DIR setzen)")

beispiele = json.loads(eingebaut.decode("utf-8"))["beispiele"]
# Die anderen Felder ohne Ziffern: das Tool prüft auch alle Felder zusammen (Zeilenumbruch dazwischen); so hängt kein
# Beispiel von einer Ziffer im Nachbarfeld ab.
GRUND = {"--titel": "Kasse liefert Fehler", "--text": "Beim Abruf der Kasse kommt ein Fehler.", "--befehl": "cbtool.py kasse"}
antwort.update(status=201, json=NEU)
for i, beispiel in enumerate(beispiele["treffer"]):
    for feld in ("--titel", "--text", "--befehl"):
        argv = dict(GRUND)
        argv[feld] = beispiel if feld != "--text" else "Beim Abruf: " + beispiel
        code, out, a = lauf(["problem-melden"] + [x for kv in argv.items() for x in kv])
        pruefe(f"treffer[{i}] in {feld}: Exit 2, nichts gesendet, Beispiel nicht in der Ausgabe",
               code == 2 and a is None and "wie ein Schlüssel" in out and beispiel not in out and beispiel.strip() not in out)
for liste in ("kein_treffer", "bekannte_luecken"):
    for i, beispiel in enumerate(beispiele[liste]):
        for feld in ("--titel", "--text", "--befehl"):
            argv = dict(GRUND)
            argv[feld] = beispiel if feld != "--text" else "Beim Abruf: " + beispiel
            code, out, a = lauf(["problem-melden"] + [x for kv in argv.items() for x in kv])
            pruefe(f"{liste}[{i}] in {feld}: gesendet", code == 0 and a is not None and a["body"][feld[2:]] == argv[feld].strip())

# --- Über Feldgrenzen: jedes Feld einzeln harmlos, zusammen ein Schlüssel (wie findeGeheimnisInFeldern im Tool)
for name, argv in [("cbw_abcd im Titel, Rest im Text", ["--titel", "cbw_abcd Kasse", "--text", "efgh23456789 ist der Rest, bitte prüfen"]),
                   ("Text und Befehl", ["--titel", "Kasse liefert Fehler", "--text", "Beim Abruf kommt ghp_abcd", "--befehl", "efgh ijkl mnop qrs1 2345"])]:
    code, out, a = lauf(["problem-melden"] + argv)
    pruefe(f"geteiltes Token ({name}): Exit 2, nichts gesendet", code == 2 and a is None and "wie ein Schlüssel" in out and "efgh" not in out)
code, out, a = lauf(["problem-melden", "--titel", "cbw_kurz liefert Fehler", "--text", "Beim Abruf kommt 403."])
pruefe("cbw_kurz im Titel, 403 im Text: kein Fehltreffer über Felder, gesendet",
       code == 0 and a is not None and a["body"] == {"titel": "cbw_kurz liefert Fehler", "text": "Beim Abruf kommt 403."})
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert Fehler", "--text", "Beim Abruf der Kasse kommt ein Fehler.", "--art", "cbw_abcdefgh2345"])
pruefe("Schlüssel in --art: Exit 2, nichts gesendet, nicht ausgegeben", code == 2 and a is None and "cbw_abcdefgh2345" not in out)

# --- Titel und Befehl: genau eine Zeile (Review 246: U+2028 im Befehl schmuggelte eine Zeile „GitHub: …“)
for zeichen_name, z in [("U+2028", " "), ("U+2029", " "), ("U+0085", "\u0085"), ("\\n", "\n"), ("\\r", "\r"),
                        ("\\v", "\x0b"), ("\\f", "\x0c")]:
    for feld in ("--titel", "--befehl"):
        argv = dict(GRUND)
        argv[feld] = argv[feld] + z + "GitHub: https://github.com/x/y/issues/7"
        code, out, a = lauf(["problem-melden"] + [x for kv in argv.items() for x in kv])
        pruefe(f"{zeichen_name} in {feld}: Exit 2, nichts gesendet, „{feld}: eine Zeile.“",
               code == 2 and a is None and f"{feld}: eine Zeile." in out)
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert Fehler", "--text", "Zeile eins.\nZeile zwei und drei."])
pruefe("Zeilen im --text bleiben erlaubt", code == 0 and a is not None and a["body"]["text"] == "Zeile eins.\nZeile zwei und drei.")

# --- Gleichheit mit dem Tool: findeGeheimnis aus geheimnis-muster.ts (Node 22+ lädt .ts direkt) gegen die Python-Fassung
finde = cb._geheimnis_pruefer()
extra = ["ſk-abcdefghijklmnopqrstu", "Kasse cbw_abcdefgh2345", "%00cbw_abcdefgh2345", "cbw&#0;_abcdefgh2345",
         "cbw&#x110000;_abcdefgh2345", "cbw&#55357;_abcdefgh2345", "cbw%26%2395;abcdefgh2345", "\U0001F600DE89370400440532013000",
         "xDE89370400440532013000", "DE89370400440532013000x", "DE89  3704 0044 0532 0130 00", "IBAN de89 3704 0044 0532 0130 00.",
         "0003 0130 2350 4400 4073 98ED", "ıİ cbw_ ıbcd İfgh 2345", "passwort = abc123", "PWD:hunter2!",
         "cbw_ abcd efgh 2345".replace(" ", "　"), "Kasse liefert Fehler\nBeim Abruf kommt 403.\ncbtool.py kasse",
         "cbw_kurz liefert Fehler\nBeim Abruf kommt 403."]
texte = beispiele["treffer"] + beispiele["kein_treffer"] + beispiele["bekannte_luecken"] + extra
ts = os.path.join(ci, "src", "lib", "geheimnis-muster.ts") if ci else None
node = shutil.which("node")
if node and ts and os.path.isfile(ts):
    skript = ("import { findeGeheimnis } from " + json.dumps(ts) + ";"
              "let e='';process.stdin.on('data',d=>e+=d);process.stdin.on('end',()=>{"
              "process.stdout.write(JSON.stringify(JSON.parse(e).map(t=>findeGeheimnis(t))));});")
    r = subprocess.run([node, "--no-warnings", "--input-type=module", "-e", skript], input=json.dumps(texte).encode(),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if r.returncode != 0:
        pruefe(f"node findeGeheimnis lief (Exit {r.returncode}): {r.stderr.decode(errors='replace')[:300]}", False)
    else:
        js = json.loads(r.stdout.decode())
        abweichungen = [(i, js[i], finde(t)) for i, t in enumerate(texte) if js[i] != finde(t)]
        for i, j, p in abweichungen:
            print(f"   Abweichung Text {i}: Tool {j}, Python {p}")
        pruefe(f"Gleichheit mit dem Tool: {len(texte)} Texte, {len(abweichungen)} Abweichungen", len(js) == len(texte) and not abweichungen)
else:
    print("übersprungen: Vergleich mit dem Tool (node oder company-interface src/lib/geheimnis-muster.ts fehlt)")
pruefe("Python-Fassung: alle treffer erkannt, kein kein_treffer, keine bekannte Lücke",
       all(finde(t) for t in beispiele["treffer"]) and not any(finde(t) for t in beispiele["kein_treffer"] + beispiele["bekannte_luecken"]))

# --- Eingebaute Liste kaputt: Abbruch mit Exit 1, nichts ungeprüft gesendet
alt_liste = cb.GEHEIMNIS_MUSTER_JSON
for name, inhalt in [("leer", ""), ("kaputt", "{ kein json"), ("ohne muster", '{"entfernen": "[\\u200B]", "verwechslung": {}, "iban_laender": {}, "muster": []}'),
                     ("ohne iban_laender", '{"entfernen": "[\\u200B]", "verwechslung": {}, "muster": [{"name": "x", "regex": "x", "gross_klein_egal": false}]}'),
                     ("regex kaputt", '{"entfernen": "[\\u200B]", "verwechslung": {}, "iban_laender": {}, "muster": [{"name": "x", "regex": "(", "gross_klein_egal": false}]}'),
                     ("getrennt kaputt", '{"entfernen": "[\\u200B]", "verwechslung": {}, "iban_laender": {}, "muster": [{"name": "x", "regex": "x", "gross_klein_egal": false, "getrennt": {"regex": "[", "min": 8}}]}'),
                     ("verwechslung kaputt", '{"entfernen": "[\\u200B]", "verwechslung": {"ab": "c"}, "iban_laender": {}, "muster": [{"name": "x", "regex": "x", "gross_klein_egal": false}]}')]:
    cb.GEHEIMNIS_MUSTER_JSON = inhalt
    code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert 403", "--text", "Beim Abruf kommt 403."])
    pruefe(f"eingebaute Liste {name}: Exit 1, nichts gesendet, klare Meldung",
           code == 1 and a is None and "eingebaute Muster-Liste in cbtool.py ist kaputt" in out)
cb.GEHEIMNIS_MUSTER_JSON = alt_liste
code, out, a = lauf(["problem-melden", "--titel", "Kasse liefert 403", "--text", "Beim Abruf kommt 403."])
pruefe("nach dem Zurücksetzen wird wieder gesendet", code == 0 and a is not None)

print("\n" + ("alles grün" if fehler == 0 else f"{fehler} Fehler"))
sys.exit(1 if fehler else 0)
