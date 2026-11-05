#!/usr/bin/env python3
"""Prüfskript für die Projekt-Befehle (Projekt-Akte, 05.11.2026). Ohne Framework, ohne Netz, eigenes HOME:
urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-projekte.py   (Exit 0 = alles grün)"""
import contextlib, importlib.util, io, json, os, sys, tempfile, urllib.error

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
cb._heute_berlin = lambda: "2026-11-05"

fehler = 0


def pruefe(name: str, ok: bool) -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name)
    fehler += 0 if ok else 1


BELEG = "Mail von Lüschow vom 05.11., Thread 19a"
STAND = {"abgerufen": "2026-11-05T14:37:10.642Z", "daten": "live"}
ZEILE = {"stand": {"text": "Projekt angelegt", "quelle": "J-410", "am": "2026-11-05"}, "naechsterSchritt": {"text": "Sample testing", "quelle": "S-148", "faellig": None},
         "werDran": {"personen": ["Maxi", "Mats"], "wartetAuf": None, "seit": "2026-08-21T18:05:52.225Z", "seitBeleg": None, "seitUngenau": False},
         "blocker": [{"ref": "S-9", "text": "wartet auf Muster"}], "haengt": True, "befunde": [], "hinweise": ["Produktart fehlt"]}
PROJEKT = {"nr": "P-6", "name": "Everyday-Elektrolyt (Pur)", "ziel": "Ziel", "besitzer": "Maxi", "zielBis": None, "offen": True}
AKTE = {"projekt": PROJEKT, "zeile": ZEILE, "aufgaben": ["CB-218 Etikett prüfen"], "produkte": [{"sku": "2-M-TK-120", "name": "Tonkarton"}, {"sku": None, "name": "Neu"}],
        "bestellungen": [{"po": "PO-032-1-2-M-TK-120", "produkt": "Tonkarton", "status": "AB erhalten", "termin": "2026-12-01", "naechsterSchritt": None}],
        "einsendungen": [{"nr": "IN-2026-0039", "status": "unterwegs", "eta": None, "warnung": None}], "journal": ["J-410"], "weitere": {"journal": 3},
        "verweise": {"journal": "/journal?projekt=P-6", "wiki": "/search?q=x", "drive": None}, "stand": STAND,
        "schritte": {"fortschritt": "7 von 28, 21 startbar", "zaehler": {"startbar": 21, "laeuft": 0, "erledigt": 7},
                     "dran": [{"nr": "S-148", "titel": "Sample testing", "zustand": "startbar", "personen": ["Maxi"], "aufgabe": "CB-218", "frist": "2026-11-20", "pflicht": True}], "weitere": 13,
                     "fehlende_pflichtpunkte": [{"schluessel": "pflicht-alle-gtin", "name": "GTIN", "quelle": "SKU-Registry"}], "dokumente_fehlen": 2}}
BEZUG = {"vorschau": True, "wiederholt": False, "unveraendert": False, "richtung": "setzen", "projekt": "P-6", "art": "aufgabe", "ziel": "CB-218", "journal": None, "gebuchtAm": None, "link": "https://t/projekte/P-6"}
anfragen = []
antwort = {"status": 200, "json": {}}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append({"methode": req.get_method(), "url": req.full_url, "body": json.loads(req.data.decode()) if req.data else None})
    if antwort["status"] >= 400:
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "Fehler", {}, io.BytesIO(antwort.get("roh") or json.dumps(antwort["json"]).encode()))
    return Antwort(json.dumps(antwort["json"]).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(*args, status=200, js=None, roh=None):
    """Gibt (Ausgabe, Exit-Text oder None) zurück."""
    anfragen.clear()
    antwort.update(status=status, json=js if js is not None else {}, roh=roh)
    aus, err = io.StringIO(), io.StringIO()
    code = None
    with contextlib.redirect_stdout(aus), contextlib.redirect_stderr(err):
        try:
            cb.main(["cbtool.py"] + list(args))
        except SystemExit as e:
            code = e.code
    return aus.getvalue(), code


# ---- Lesen
aus, code = lauf("projekte", js={"projekte": [{"projekt": PROJEKT, "zeile": ZEILE}, {"projekt": {"nr": "P-9", "name": "Fertig", "offen": False}, "zeile": {"werDran": {"personen": ["Maxi"]}}}], "stand": STAND})
pruefe("projekte fragt alle=1", anfragen[0]["url"].endswith("/api/brain-read/projekte?alle=1") and anfragen[0]["methode"] == "GET")
pruefe("Zeile: Kennung, Name, Stand, dran, nächster Schritt", "P-6 · Everyday-Elektrolyt (Pur) · offen · Stand 05.11.: Projekt angelegt (J-410) · dran: Maxi, Mats seit 21.08. · nächster Schritt: Sample testing (S-148)" in aus)
pruefe("Blocker und hängt in der Zeile", "Blocker: 1" in aus and "hängt" in aus)
pruefe("abgeschlossen ohne Stand", "P-9 · Fertig · abgeschlossen · Stand kein Stand · dran: Maxi" in aus)
pruefe("Stand:-Zeile", "Stand: abgerufen 05.11.2026 15:37, Daten live" in aus)
aus, _ = lauf("projekte", "--ausnahmen", js={"befunde": [{"art": "ueberfaellig", "seit": "2026-11-01", "ref": "CB-1", "besitzer": "Maxi", "naechsterSchritt": None, "link": None, "projekte": ["P-6", "P-7"]}], "zaehler": {"projekte": 5, "offen": 3, "haengen": 1, "aufgabenOhneProjekt": 83, "journalOhneBezug": 25}, "stand": STAND})
pruefe("--ausnahmen ohne Parameter", anfragen[0]["url"].endswith("/projekte"))
pruefe("Befund mit Projekten, Zähler", "ueberfaellig · CB-1 · seit 01.11. · P-6, P-7" in aus and "hängen 1" in aus)
lauf("projekte", "--neu-seit", "2026-11-01", js={"stand": STAND})
pruefe("--neu-seit", anfragen[0]["url"].endswith("/projekte?neu_seit=2026-11-01"))
aus, _ = lauf("projekte", "--ref", "2-M-TK-120", js={"treffer": [{"projekt": "P-9", "name": "Fertig", "offen": False, "ref": "2-M-TK-120", "art": "produkt", "herkunft": "bezug"}], "stand": STAND})
pruefe("--ref", anfragen[0]["url"].endswith("/projekte?ref=2-M-TK-120") and "P-9 · Fertig · abgeschlossen · produkt 2-M-TK-120" in aus)
_, code = lauf("projekte", "--ausnahmen", "--ref", "CB-1")
pruefe("zwei Lesarten: Bedienfehler, nichts gesendet", code == 2 and not anfragen)

aus, _ = lauf("projekt", "P-6", js=AKTE)
pruefe("projekt fragt P-6", anfragen[0]["url"].endswith("/projekte/P-6"))
for teil in ("P-6 · Everyday-Elektrolyt (Pur) · offen", "Letzter Stand: 05.11.: Projekt angelegt (J-410)", "Wer dran: Maxi, Mats seit 21.08.", "S-9 · wartet auf Muster", "Produktart fehlt",
             "Schritte: 7 von 28, 21 startbar (startbar 21, erledigt 7)", "S-148 · startbar · Sample testing · Maxi · CB-218 · Frist 20.11. · Pflicht", "und 13 weitere",
             "pflicht-alle-gtin · GTIN · Quelle: SKU-Registry", "Dokumente fehlen: 2", "CB-218 Etikett prüfen", "2-M-TK-120 · Tonkarton", "ohne SKU · Neu",
             "PO-032-1-2-M-TK-120 · AB erhalten · Tonkarton · Termin 01.12.", "IN-2026-0039 · unterwegs · ohne ETA", "Journal (und 3 weitere):", "http://127.0.0.1:9/journal?projekt=P-6", "Stand: abgerufen"):
    pruefe("projekt zeigt: " + teil, teil in aus)
aus, _ = lauf("projekt", "Everyday-Elektrolyt (Pur)", "--schritte-alle", js={**AKTE, "schritte": {**AKTE["schritte"], "alle": [{"nr": "S-141", "zustand": "laeuft", "titel": "Ordner", "verantwortlich": ["Maxi"], "aufgabe": None, "blockiertDurch": ["S-1"], "pflicht": False, "dokument": {"stand": "fehlt"}, "schluessel": "pipeline-1-1"}]}})
pruefe("Name wird Pfadteil, schritte=alle", anfragen[0]["url"].endswith("/projekte/Everyday-Elektrolyt%20%28Pur%29?schritte=alle"))
pruefe("alle Schritte", "S-141 · läuft · Ordner · Maxi · braucht S-1 · Dokument fehlt · [pipeline-1-1]" in aus)
aus, _ = lauf("projekt", "P-6", js={**AKTE, "schritte": None})
pruefe("Akte ohne Schritte-Block bricht nicht", "Schritte: keine Angabe" in aus)
_, code = lauf("projekt", "..")
pruefe("„..“ wird nicht gesendet", code == 2 and not anfragen)

# ---- Fehler: wörtlich
GESPERRT = "Dieses Konto darf keine Projekt-Schritte buchen (Tür projekt_schritte)."
for befehl in (["schritt-aktion", "S-1", "--aktion", "loesen", "--beleg", BELEG], ["projekt-schritte", "P-6", "--pflichtpunkte", "--beleg", BELEG], ["schritt-uebernehmen", "S-1", "--fuer", "Max", "--beleg", BELEG], ["projekt-bezug", "P-6", "--produkt", "X", "--beleg", BELEG]):
    _, code = lauf(*befehl, status=403, js={"error": GESPERRT})
    pruefe("403 wörtlich: " + befehl[0], code == GESPERRT)
_, code = lauf("projekt", "P-999", status=404, js={"error": "Projekt P-999 gibt es nicht."})
pruefe("404 mit Text wörtlich", code == "Projekt P-999 gibt es nicht.")
_, code = lauf("projekte", status=404, roh=b"<html>")
pruefe("404 ohne Text: Route fehlt", code == cb.PROJEKTE_FEHLT)
_, code = lauf("projekt", "Ev", status=400, js={"error": "Projekt „Ev“ passt auf mehrere Projekte.", "treffer": ["A (P-1)", "B (P-2)"]})
pruefe("mehrdeutig nennt Treffer", "A (P-1), B (P-2)" in str(code))

# ---- projekt-bezug
aus, code = lauf("projekt-bezug", "P-6", "--aufgabe", "CB-218", "--beleg", BELEG, js={"aenderung": BEZUG})
a = anfragen[0]
pruefe("Vorschau: POST, Body, kein Schlüssel", a["methode"] == "POST" and a["url"].endswith("/projekte/P-6/bezuege") and a["body"] == {"aufgabe": "CB-218", "beleg": BELEG, "vorschau": True})
pruefe("Vorschau sagt es", "Vorschau, nichts geschrieben: aufgabe CB-218 zu P-6" in aus and "--ausfuehren" in aus)
aus, _ = lauf("projekt-bezug", "P-6", "--aufgabe", "CB-218", "--beleg", BELEG, "--ausfuehren", js={"aenderung": {**BEZUG, "vorschau": False, "journal": "J-500"}})
k1 = anfragen[0]["body"]
pruefe("Ausführen: ein Aufruf, vorschau false, Schlüssel gültig", len(anfragen) == 1 and k1["vorschau"] is False and cb.re.match(r"^[A-Za-z0-9._:-]{8,100}$", k1["idempotenz_schluessel"]) is not None)
pruefe("Eingetragen mit Journal", "Zugeordnet: aufgabe CB-218 zu P-6" in aus and "Journal: J-500" in aus)
lauf("projekt-bezug", "P-6", "--aufgabe", "CB-218", "--beleg", BELEG, "--ausfuehren", js={"aenderung": BEZUG})
pruefe("gleicher Befehl, gleicher Schlüssel", anfragen[0]["body"]["idempotenz_schluessel"] == k1["idempotenz_schluessel"])
aus, _ = lauf("projekt-bezug", "P-6", "--aufgabe", "CB-218", "--beleg", BELEG, "--loesen", "--ausfuehren", js={"aenderung": {**BEZUG, "vorschau": False, "richtung": "loesen"}})
pruefe("--loesen: DELETE, anderer Schlüssel", anfragen[0]["methode"] == "DELETE" and anfragen[0]["body"]["idempotenz_schluessel"] != k1["idempotenz_schluessel"] and "Gelöst:" in aus)
aus, _ = lauf("projekt-bezug", "P-6", "--aufgabe", "CB-218", "--beleg", BELEG, js={"aenderung": {**BEZUG, "unveraendert": True}})
pruefe("nichts zu tun: kein Hinweis auf --ausfuehren", "Schon so" in aus and "--ausfuehren" not in aus)
aus, _ = lauf("projekt-bezug", "P-6", "--aufgabe", "CB-218", "--beleg", BELEG, "--ausfuehren", js={"aenderung": {**BEZUG, "vorschau": False, "wiederholt": True, "gebuchtAm": "2026-11-05T10:00:00Z"}})
pruefe("wiederholt sagt es", "Schon eingetragen (gleicher Befehl, 05.11.2026)" in aus)
lauf("projekt-bezug", "P-6", "--aufgabe", "CB-218", "--beleg", BELEG, "--schluessel", "mein-schluessel-1", js={"aenderung": BEZUG})
pruefe("--schluessel in der Vorschau", anfragen[0]["body"]["idempotenz_schluessel"] == "mein-schluessel-1" and anfragen[0]["body"]["vorschau"] is True)
for name, args in (("kein Ziel", ["P-6", "--beleg", BELEG]), ("zwei Ziele", ["P-6", "--aufgabe", "CB-1", "--produkt", "X", "--beleg", BELEG]), ("Beleg kurz", ["P-6", "--aufgabe", "CB-1", "--beleg", "kurz", "--ausfuehren"]),
                   ("Schlüssel ungültig", ["P-6", "--aufgabe", "CB-1", "--beleg", BELEG, "--schluessel", "a b"]), ("kein Projekt", ["--aufgabe", "CB-1", "--beleg", BELEG]), ("unbekannte Option", ["P-6", "--aufgabe", "CB-1", "--beleg", BELEG, "--quatsch"])):
    _, code = lauf("projekt-bezug", *args)
    pruefe("Bezug lokal abgelehnt: " + name, code == 2 and not anfragen)

# ---- projekt-schritte
ANLEGEN = {"projekt": "P-6", "angelegt": [{"nr": "S-900", "schluessel": "pflicht-alle-gtin", "art": "pflicht-alle-gtin"}], "pflichtpunkte_ergaenzt": [{"nr": "S-900", "art": "pflicht-alle-gtin", "quelle": "SKU-Registry", "quelle_art": "learning"}],
           "geaendert": [], "unveraendert": [], "neue_arten": [], "vorschau": True, "wiederholt": False, "geschrieben": False, "link": "https://t/projekte/P-6"}
aus, _ = lauf("projekt-schritte", "P-6", "--pflichtpunkte", "--beleg", BELEG, js=ANLEGEN)
pruefe("--pflichtpunkte: leere Liste, Vorschau", anfragen[0]["url"].endswith("/projekte/P-6/schritte") and anfragen[0]["body"] == {"schritte": [], "beleg": BELEG, "vorschau": True})
pruefe("Vorschau ohne Nummern", "S-900" not in aus and "+ pflicht-alle-gtin" in aus and "Vorschau, nichts geschrieben: P-6: 1 neu" in aus)
aus, _ = lauf("projekt-schritte", "P-6", "--pflichtpunkte", "--beleg", BELEG, "--ausfuehren", js={**ANLEGEN, "vorschau": False, "geschrieben": True})
pruefe("Eintragen mit Nummern", "Eingetragen: P-6: 1 neu" in aus and "+ S-900 · pflicht-alle-gtin" in aus and anfragen[0]["body"]["vorschau"] is False)
k_heute = anfragen[0]["body"]["idempotenz_schluessel"]
cb._heute_berlin = lambda: "2026-11-06"
lauf("projekt-schritte", "P-6", "--pflichtpunkte", "--beleg", BELEG, "--ausfuehren", js=ANLEGEN)
pruefe("Anlegen: anderer Tag, anderer Schlüssel", anfragen[0]["body"]["idempotenz_schluessel"] != k_heute)
cb._heute_berlin = lambda: "2026-11-05"
aus, _ = lauf("projekt-schritte", "P-6", "--pflichtpunkte", "--beleg", BELEG, js={**ANLEGEN, "angelegt": [], "pflichtpunkte_ergaenzt": [], "unveraendert": ["S-1"]})
pruefe("nichts Neues: Schon so", "Schon so, nichts zu ändern: P-6: 0 neu, 0 geändert, 1 unverändert" in aus)
lauf("projekt-schritte", "P-6", "--art", "haccp", "--titel", "HACCP liegt vor", "--sku", "2-M-TK-120", "--schritt-schluessel", "haccp-x", "--hinweis", "H", "--braucht", "S-1, haccp-y", "--beleg", BELEG, js=ANLEGEN)
pruefe("ein Schritt: Felder wie die API", anfragen[0]["body"]["schritte"] == [{"art": "haccp", "titel": "HACCP liegt vor", "sku": "2-M-TK-120", "schluessel": "haccp-x", "hinweis": "H", "braucht_vorher": ["S-1", "haccp-y"]}])
LISTE = [{"art": {"neu": {"schluessel": "neu-art", "name": "Neu", "zustaendigkeit": "operations"}}, "titel": "Neuer Schritt"}]
pfad = os.path.join(home, "liste.json")
with open(pfad, "w", encoding="utf-8") as fh:
    json.dump(LISTE, fh)
lauf("projekt-schritte", "P-6", "--liste", pfad, "--beleg", BELEG, js=ANLEGEN)
pruefe("--liste geht unverändert hinaus", anfragen[0]["body"]["schritte"] == LISTE)
with open(pfad, "w", encoding="utf-8") as fh:
    fh.write('{"art": "x"}')
_, code = lauf("projekt-schritte", "P-6", "--liste", pfad, "--beleg", BELEG)
pruefe("--liste kein Array", code == 2 and not anfragen)
with open(pfad, "w", encoding="utf-8") as fh:
    fh.write("[kaputt")
_, code = lauf("projekt-schritte", "P-6", "--liste", pfad, "--beleg", BELEG)
pruefe("--liste kein JSON", code == 2 and not anfragen)
_, code = lauf("projekt-schritte", "P-6", "--liste", os.path.join(home, "fehlt.json"), "--beleg", BELEG)
pruefe("--liste fehlt", code == 2 and not anfragen)
for name, args in (("nichts gewählt", ["P-6", "--beleg", BELEG]), ("zwei gewählt", ["P-6", "--pflichtpunkte", "--art", "x", "--titel", "Titel", "--beleg", BELEG]), ("ohne Titel", ["P-6", "--art", "x", "--beleg", BELEG]), ("ohne Beleg", ["P-6", "--pflichtpunkte", "--ausfuehren"])):
    _, code = lauf("projekt-schritte", *args)
    pruefe("Schritte lokal abgelehnt: " + name, code == 2 and not anfragen)

# ---- schritt-aktion
AKTION = {"nr": "S-431", "projekt": "P-6", "aktion": "erledigen", "vorher": "startbar", "gemacht_von": "ki_mit_freigabe", "unveraendert": False, "journal": None, "vorschau": True, "wiederholt": False, "geschrieben": False, "link": "https://t/projekte/P-6"}
aus, _ = lauf("schritt-aktion", "s431", "--aktion", "erledigen", "--beleg", BELEG, "--fundort", "https://drive/x", "--freigabe-von", "Max", "--freigabe-beleg", "J-1234567890", js=AKTION)
a = anfragen[0]
pruefe("Aktion: S-n normiert, Felder in API-Namen", a["url"].endswith("/schritte/S-431") and a["body"] == {"aktion": "erledigen", "beleg": BELEG, "fundort": "https://drive/x", "freigabe_von": "Max", "freigabe_beleg": "J-1234567890", "vorschau": True})
pruefe("Aktion Vorschau", "Vorschau, nichts geschrieben: S-431 (P-6) · erledigen" in aus and "Zustand jetzt: startbar" in aus and "ki_mit_freigabe" in aus)
aus, _ = lauf("schritt-aktion", "S-431", "--aktion", "wieder-offen", "--grund", "Zertifikat falsch", "--beleg", BELEG, "--ausfuehren", js={**AKTION, "aktion": "wieder_offen", "vorher": "erledigt", "zustand": "startbar", "vorschau": False, "geschrieben": True, "journal": "J-7"})
k2 = anfragen[0]["body"]
pruefe("Bindestrich normiert, Schlüssel gesetzt", k2["aktion"] == "wieder_offen" and k2["grund"] == "Zertifikat falsch" and k2["vorschau"] is False and k2["idempotenz_schluessel"].startswith("cbtool-"))
pruefe("Zustand vorher und nachher", "Gebucht: S-431 (P-6) · wieder_offen" in aus and "Zustand: erledigt › startbar" in aus)
lauf("schritt-aktion", "431", "--aktion", "wieder_offen", "--grund", "Zertifikat falsch", "--beleg", BELEG, "--ausfuehren", js=AKTION)
pruefe("431 und S-431 sind derselbe Schlüssel", anfragen[0]["body"]["idempotenz_schluessel"] == k2["idempotenz_schluessel"])
lauf("schritt-aktion", "S-431", "--aktion", "wieder_offen", "--grund", "Anderer Grund", "--beleg", BELEG, "--ausfuehren", js=AKTION)
pruefe("anderer Inhalt, anderer Schlüssel", anfragen[0]["body"]["idempotenz_schluessel"] != k2["idempotenz_schluessel"])
for name, args in (("kein Schritt", ["X-1", "--aktion", "loesen", "--beleg", BELEG]), ("ohne Aktion", ["S-1", "--beleg", BELEG]), ("falsche Aktion", ["S-1", "--aktion", "quatsch", "--beleg", BELEG]), ("ohne Beleg", ["S-1", "--aktion", "loesen", "--ausfuehren"])):
    _, code = lauf("schritt-aktion", *args)
    pruefe("Aktion lokal abgelehnt: " + name, code == 2 and not anfragen)

# ---- schritt-uebernehmen
UEBER = {"aufgabe": "CB-999", "titel": "Everyday: Sample testing", "schritt": {"nr": "S-148", "zustand": "startbar", "folgt": "CB-999"}, "vorschau": True, "wiederholt": False, "geschrieben": False, "link": "https://t/projekte/P-6"}
aus, _ = lauf("schritt-uebernehmen", "S-148", "--fuer", "Maxi", "--frist", "2026-11-20", "--beleg", BELEG, js=UEBER)
a = anfragen[0]
pruefe("Übernehmen: POST /aufgaben mit schritt", a["url"].endswith("/api/brain-read/aufgaben") and a["body"] == {"schritt": "S-148", "fuer": "Maxi", "frist": "2026-11-20", "beleg": BELEG, "vorschau": True})
pruefe("Vorschau ohne CB-Nummer", "CB-999" not in aus and "Vorschau, nichts geschrieben: S-148 an Maxi, Frist 20.11.2026" in aus)
aus, _ = lauf("schritt-uebernehmen", "S-148", "--fuer", "Maxi", "--beleg", BELEG, "--ausfuehren", js={**UEBER, "vorschau": False, "geschrieben": True, "schritt": {"nr": "S-148", "zustand": "laeuft", "folgt": "CB-999"}})
pruefe("Übernommen mit CB-Nummer", "Übernommen: S-148 an Maxi als CB-999" in aus and "Zustand: läuft" in aus and anfragen[0]["body"]["idempotenz_schluessel"].startswith("cbtool-"))
for name, args in (("ohne fuer", ["S-1", "--beleg", BELEG]), ("Frist falsch", ["S-1", "--fuer", "Max", "--frist", "morgen", "--beleg", BELEG]), ("ohne Beleg", ["S-1", "--fuer", "Max", "--ausfuehren"])):
    _, code = lauf("schritt-uebernehmen", *args)
    pruefe("Übernehmen lokal abgelehnt: " + name, code == 2 and not anfragen)

# ---- Hilfe
for befehl in ("projekt-bezug", "projekt-schritte", "schritt-aktion", "schritt-uebernehmen"):
    aus, code = lauf(befehl, "--help")
    pruefe("--help: " + befehl, "--ausfuehren" in aus and code is None and not anfragen)

print("\nFEHLER: " + str(fehler) if fehler else "\nAlles grün.")
sys.exit(1 if fehler else 0)
