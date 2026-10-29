#!/usr/bin/env python3
"""Prüfskript für `journal` und `journal-neu` (Betriebs-Journal im Tool, 29.10.2026). Ohne Framework, ohne Netz, eigenes
HOME, Uhr fest (29.10.2026 10:00 Berlin): urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-journal.py   (Exit 0 = alles grün)"""
import importlib.util, io, json, os, sys, tempfile, urllib.error, urllib.parse
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


BELEG = "Mail an Pia (CIS) 29.10. 10:02, https://mail.google.com/mail/u/0/#sent/abc"
UEB = {"nr": "J-1234", "quelle": "journal", "art": "uebergabe", "bereich": "supply_chain", "passiertAm": "2026-10-29T13:12:00.000Z",
       "erfasstAm": "2026-10-29T13:12:00.000Z", "von": "Silver", "imAuftragVon": None, "kanal": "schluessel",
       "text": "Palettenrechnung K+N liegt im Thread, bitte prüfen und buchen.", "beleg": BELEG, "ref": "PO-032-1-2-M-TK-120",
       "refArt": "bestellung", "fuer": "Maxi", "faelligAm": None, "offen": True, "quittiertAm": None, "quittiertVon": None,
       "link": "https://company-interface.vercel.app/journal?eintrag=J-1234"}
FAKT = {"nr": None, "quelle": "station", "art": "station", "bereich": "supply_chain", "passiertAm": "2026-10-28T08:00:00Z", "erfasstAm": "2026-10-28T08:00:00Z",
        "von": "Mats", "kanal": "tool", "text": "Station Produktion fertig PO-040 1.000 St. am 27.10.2026", "beleg": "im Tool erfasst",
        "ref": "PO-040", "refArt": "bestellung", "fuer": None, "offen": False, "quittiertAm": None, "link": None}
AUFG = {**FAKT, "quelle": "journal", "nr": "J-1235", "art": "ereignis", "kanal": "trigger", "text": "Aufgabe CB-501 erledigt: Beleg Lüschow", "beleg": "Aufgabe CB-501 im Tool (Trigger action_items_journal)"}
anfragen = []
antwort = {"status": 200, "json": {"eintraege": [UEB, AUFG, FAKT], "stand": {"abgerufen": "2026-10-29T09:00:00Z", "seit": "2026-10-27T09:00:00.000Z", "anzahl": 3}}}


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
    return code, puffer.getvalue(), (anfragen[-1] if anfragen else None)


def query(a):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(a["url"]).query))


# --- journal (lesen)
code, out, a = lauf("journal", [])
pruefe("lesen: GET /api/brain-read/journal ohne Parameter", code == 0 and a["methode"] == "GET" and a["url"].endswith("/api/brain-read/journal"))
zeilen = out.strip().split("\n")
pruefe("Kopf mit seit", zeilen[0] == "Journal seit 27.10. 10:00: 3 Einträge")
pruefe("Zeile: Nr · Zeit (Berlin) · Verfasser · Art › Empfänger · Text · (Beleg) · OFFEN",
       zeilen[1] == f"J-1234 · 29.10. 14:12 · Silver · uebergabe › Maxi · Palettenrechnung K+N liegt im Thread, bitte prüfen und buchen. · ({BELEG}) · OFFEN")
pruefe("Trigger-Zeile ohne Beleg-Wiederholung", zeilen[2] == "J-1235 · 28.10. 09:00 · Mats · ereignis · Aufgabe CB-501 erledigt: Beleg Lüschow")
pruefe("Fakt ohne Nummer, Quelle als Art", zeilen[3] == "28.10. 09:00 · Mats · station · Station Produktion fertig PO-040 1.000 St. am 27.10.2026")
code, out, a = lauf("journal", ["--seit", "12h", "--von", "Silver", "--art", "Fakten", "--ref", "PO-032", "--bereich", "team", "--limit", "20"])
pruefe("Parameter wörtlich durchgereicht (art klein)", query(a) == {"seit": "12h", "von": "Silver", "art": "fakten", "ref": "PO-032", "bereich": "team", "limit": "20"})
antwort["json"] = {"eintraege": [UEB], "stand": {"abgerufen": "2026-10-29T09:00:00Z", "seit": None}}
code, out, a = lauf("journal", ["--offen-fuer", "ich"])
pruefe("offen für mich: Parameter, Kopf, Hinweis aufs Quittieren", query(a) == {"offen_fuer": "ich"} and out.startswith("Offen für ich: 1") and "journal --quittieren" in out)
antwort["json"] = {"eintrag": {**UEB, "offen": False, "quittiertAm": "2026-10-29T09:00:00Z", "quittiertVon": "Maxi"}, "wiederholt": False}
code, out, a = lauf("journal", ["--quittieren", "j-1234"])
pruefe("quittieren: POST /journal/J-1234/quittieren ohne Body", code == 0 and a["methode"] == "POST" and a["url"].endswith("/api/brain-read/journal/J-1234/quittieren") and a["body"] is None)
pruefe("quittieren: Ausgabe", out.startswith("Quittiert: J-1234") and "quittiert 29.10. 10:00 von Maxi" in out)
code, out, a = lauf("journal", ["--quittieren", "1234"])
pruefe("quittieren: Nummer ohne J", a["url"].endswith("/journal/J-1234/quittieren"))
antwort["json"]["wiederholt"] = True
code, out, a = lauf("journal", ["--quittieren", "J-1234"])
pruefe("quittieren: schon quittiert", out.startswith("Schon quittiert: J-1234"))
for name, args, text in [
    ("--seit falsch", ["--seit", "gestern"], "--seit erwartet"),
    ("--art falsch", ["--art", "quittung"], "--art erwartet"),
    ("--bereich falsch", ["--bereich", "geheim"], "--bereich erwartet"),
    ("--limit 0", ["--limit", "0"], "--limit erwartet"),
    ("--quittieren falsch", ["--quittieren", "CB-12"], "Journal-Nummer"),
    ("unbekannte Option", ["--suche", "x"], "Unbekannt"),
]:
    code, out, a = lauf("journal", args)
    pruefe(f"lesen {name}: Exit 2, keine Anfrage, Hilfe Journal", code == 2 and a is None and text in out and "Journal:" in out)

# --- journal-neu (schreiben)
antwort.update(status=200, json={"eintrag": UEB, "wiederholt": False})
NEU = ["--art", "uebergabe", "--text", "Palettenrechnung K+N liegt im Thread,\nbitte prüfen und buchen.", "--beleg", BELEG, "--ref", "PO-032", "--fuer", "Max", "--bereich", "supply_chain"]
code, out, a = lauf("journal-neu", NEU)
schluessel = a["body"]["idempotenz_schluessel"] if a else ""
pruefe("schreiben: POST /api/brain-read/journal", code == 0 and a["methode"] == "POST" and a["url"].endswith("/api/brain-read/journal"))
pruefe("schreiben: Body nach Vertrag (Umbrüche › Leerzeichen, kein Verfasser)", {k: v for k, v in a["body"].items() if k != "idempotenz_schluessel"} == {
    "art": "uebergabe", "text": "Palettenrechnung K+N liegt im Thread, bitte prüfen und buchen.", "beleg": BELEG, "ref": "PO-032", "offen_fuer": "Max", "bereich": "supply_chain"})
pruefe("Schlüssel aus Inhalt und Tag", schluessel.startswith("cbtool-") and len(schluessel) == 47)
pruefe("Ausgabe: Eingetragen + Link", out.startswith("Eingetragen: J-1234 ·") and "journal?eintrag=J-1234" in out)
code, out, a2 = lauf("journal-neu", NEU)
pruefe("gleicher Befehl: gleicher Schlüssel", a2["body"]["idempotenz_schluessel"] == schluessel)
code, out, a3 = lauf("journal-neu", NEU[:-2] + ["--bereich", "team"])
pruefe("anderer Inhalt: anderer Schlüssel", a3["body"]["idempotenz_schluessel"] != schluessel)
cb._jetzt = lambda: datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)
code, out, a4 = lauf("journal-neu", NEU)
pruefe("nächster Tag: anderer Schlüssel (neue Zeile)", a4["body"]["idempotenz_schluessel"] != schluessel)
cb._jetzt = lambda: datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc)
antwort["json"] = {"eintrag": UEB, "wiederholt": True}
code, out, a = lauf("journal-neu", NEU)
pruefe("wiederholt: Schon eingetragen", out.startswith("Schon eingetragen (gleicher Befehl): J-1234"))
antwort["json"] = {"eintrag": UEB, "wiederholt": False}
code, out, a = lauf("journal-neu", ["--art", "zusage", "--text", "Ramin (BMP): Muster Stick Anfang KW 44.", "--beleg", BELEG, "--faellig", "2026-10-30", "--ref", "18c2f3a9b", "--ref-art", "mail", "--passiert", "2026-10-29T08:30"])
pruefe("Zusage: faellig_am, ref_art, passiert_am", {k: a["body"].get(k) for k in ("faellig_am", "ref", "ref_art", "passiert_am")} == {"faellig_am": "2026-10-30", "ref": "18c2f3a9b", "ref_art": "mail", "passiert_am": "2026-10-29T08:30"})
code, out, a = lauf("journal-neu", ["--art", "entscheidung", "--text", "Max 21.10.: Kaffeereiniger-Beutel aus China.", "--beleg", BELEG, "--schluessel", "silver-0001-abcd"])
pruefe("eigener --schluessel geht durch", a["body"]["idempotenz_schluessel"] == "silver-0001-abcd" and "offen_fuer" not in a["body"])

TXT, B = "Mail an Pia: Entladefenster angefragt.", BELEG
for name, args, text in [
    ("ohne --art", ["--text", TXT, "--beleg", B], "--art erwartet"),
    ("freigabe gibt es nicht", ["--art", "freigabe", "--text", TXT, "--beleg", B], "Freigaben schreibt nur eine Tür"),
    ("--text zu kurz", ["--art", "ereignis", "--text", "kurz", "--beleg", B], "--text"),
    ("--text zu lang", ["--art", "ereignis", "--text", "x" * 1001, "--beleg", B], "--text"),
    ("Aufgaben-Ereignis von Hand", ["--art", "ereignis", "--text", "Aufgabe CB-123 erledigt: Etiketten", "--beleg", B], "schreibt das Tool selbst"),
    ("ohne --beleg", ["--art", "ereignis", "--text", TXT], "--beleg fehlt"),
    ("Übergabe ohne --fuer", ["--art", "uebergabe", "--text", TXT, "--beleg", B], "braucht --fuer"),
    ("Zusage ohne --faellig", ["--art", "zusage", "--text", TXT, "--beleg", B], "braucht --faellig"),
    ("--faellig falsch", ["--art", "zusage", "--text", TXT, "--beleg", B, "--faellig", "30.10.2026"], "--faellig erwartet"),
    ("--passiert falsch", ["--art", "ereignis", "--text", TXT, "--beleg", B, "--passiert", "heute 10 Uhr"], "--passiert erwartet"),
    ("--ref mit Leerzeichen", ["--art", "ereignis", "--text", TXT, "--beleg", B, "--ref", "PO 032"], "--ref ist eine Nummer"),
    ("--ref-art ohne --ref", ["--art", "ereignis", "--text", TXT, "--beleg", B, "--ref-art", "mail"], "nur zusammen mit --ref"),
    ("--bereich falsch", ["--art", "ereignis", "--text", TXT, "--beleg", B, "--bereich", "geheim"], "--bereich erwartet"),
    ("unbekannte Option", ["--art", "ereignis", "--text", TXT, "--beleg", B, "--wer", "Silver"], "Unbekannt"),
]:
    code, out, a = lauf("journal-neu", args)
    pruefe(f"schreiben {name}: Exit 2, keine Anfrage", code == 2 and a is None and text in out)

# Antworten des Tools: Text unverändert; vor dem Live-Gang ein klarer Satz.
for status, text in [
    (403, "Silver schreibt nicht in den Bereich finanzen. Möglich: supply_chain, sales, team, allgemein."),
    (409, "Der Schlüssel gehört schon zu einem anderen Eintrag. Für einen neuen Eintrag einen neuen Schlüssel nehmen."),
    (400, "„Jannes“ passt zu keiner Person."),
    (503, "Das Journal ist im Tool noch nicht freigeschaltet (Migration 2026-10-30-betriebs-journal.sql fehlt)."),
]:
    antwort.update(status=status, json={"error": text})
    code, out, a = lauf("journal-neu", NEU)
    pruefe(f"schreiben {status}: Text des Tools", code != 0 and out.strip() == f"Nicht eingetragen: {text}")
antwort.update(status=503, json={"error": "Das Journal ist im Tool noch nicht freigeschaltet (Migration 2026-10-30-betriebs-journal.sql fehlt)."})
code, out, a = lauf("journal", [])
pruefe("lesen 503: Text des Tools, Exit ungleich 0", code != 0 and "noch nicht freigeschaltet" in out)
antwort.update(status=404, roh=b"<html>404</html>")
code, out, a = lauf("journal", ["--offen-fuer", "ich"])
pruefe("404 ohne Route (älteres Tool): klarer Satz, Exit ungleich 0", code != 0 and out.strip() == cb.JOURNAL_FEHLT)
code, out, a = lauf("journal-neu", NEU)
pruefe("404 beim Schreiben: klarer Satz", code != 0 and out.strip() == cb.JOURNAL_FEHLT)

print(f"\n{'Alles grün' if not fehler else f'{fehler} Fehler'} (Python {sys.version.split()[0]})")
sys.exit(1 if fehler else 0)
