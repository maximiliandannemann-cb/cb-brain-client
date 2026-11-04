#!/usr/bin/env python3
"""Prüfskript für `kontakt` (Kontaktgeschichte vor jeder Mail, 04.11.2026). Ohne Framework, ohne Netz, eigenes
HOME, Uhr fest (29.10.2026 10:00 Berlin): urlopen wird ersetzt, die Prüfung liest die Anfrage, die `call` wirklich baut.
Aufruf: /usr/bin/python3 tests/pruefe-kontakt.py   (Exit 0 = alles grün)"""
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


ANTWORT = {
    "anfrage": {"domain": "fillhub.de"}, "bekannt_im_tool": True,
    "anrede": "Im Tool bekannt: keine Vorstellung. mail_suche ausführen und auf den letzten Austausch Bezug nehmen.",
    "zuordnung": [{"art": "partner", "name": "Fillhub", "rechtlicher_name": None, "rolle": "warehouse", "land": None, "ueber": "name", "link": "https://company-interface.vercel.app/settings/stammdaten/logistik"}],
    "kontakte": [{"name": "Matthias", "email": None, "kanal": "E-Mail / Whatsapp", "rolle": None, "firma": "Fillhub"}],
    "offen": {"bestellungen": [{"po": "PO-020-1-1-B-22-LS-SET", "produkt": "Lavendelsäckchen Basic (22 Stück)", "status": "Fertig, liegt 12 T", "eta": "2026-11-20", "als": "Ziel"}],
              "sendungen": [{"nr": "IN-2026-0050", "status": "Labels versendet", "eta": None, "von": "Fillhub"}], "weitere": 2},
    "journal": [{"nr": "J-368", "am": "2026-11-04", "art": "ereignis", "text": "Fillhub bestätigt den Eingang der Einsendungsmail.", "ref": None}],
    "wiki": {"titel": "Fillhub", "link": "https://company-interface.vercel.app/wissen/partner/fillhub"},
    "mail_suche": "in:anywhere (from:@fillhub.de OR to:@fillhub.de)",
    "luecken": ["Fillhub: Kontakt ohne Mail-Adresse."],
    "stand": {"abgerufen": "2026-11-04T15:00:00Z", "daten": "live"},
}
anfragen = []
antwort = {"status": 200, "json": ANTWORT}


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



# --- Eingabe erkennen
for eingabe, erwartet in [
    ("pia@fillhub.de", ("adresse", "pia@fillhub.de")), ("Pia@Fillhub.DE", ("adresse", "pia@fillhub.de")), ("mailto:a@b.de", ("adresse", "a@b.de")),
    ("fillhub.de", ("domain", "fillhub.de")), ("@fillhub.de", ("domain", "@fillhub.de")), ("https://www.fillhub.de/kontakt", ("domain", "https://www.fillhub.de/kontakt")),
    ("Fillhub", ("firma", "Fillhub")), ("Glue Tec GmbH", ("firma", "Glue Tec GmbH")), ("Water-i.d. GmbH", ("firma", "Water-i.d. GmbH")),
]:
    pruefe(f"erkannt: {eingabe} › {erwartet[0]}", cb.kontakt_param(eingabe) == erwartet)

# --- Abfrage
code, out, a = lauf("kontakt", ["fillhub.de"])
pruefe("GET /api/brain-read/kontakt?domain=fillhub.de", code == 0 and a["methode"] == "GET" and a["url"].endswith("/api/brain-read/kontakt?domain=fillhub.de"))
pruefe("Ausgabe: bekannt, Anrede, Mail-Suche wörtlich", "Bekannt im Tool: Fillhub (warehouse) · über name" in out and "keine Vorstellung" in out
       and "Mail-Suche (mit der eigenen Gmail-Verbindung ausführen): in:anywhere (from:@fillhub.de OR to:@fillhub.de)" in out)
pruefe("Ausgabe: Nummern wörtlich, ETA deutsch", "Offen: PO-020-1-1-B-22-LS-SET · Lavendelsäckchen Basic (22 Stück) · Fertig, liegt 12 T · ETA 20.11." in out and "Offen: IN-2026-0050 · Labels versendet · von Fillhub" in out)
pruefe("Ausgabe: Journal, Wiki, Lücke, weitere", "J-368 · 04.11." in out and "Wiki: Fillhub ·" in out and "Lücke: Fillhub: Kontakt ohne Mail-Adresse." in out and "und 2 weitere offene" in out)
code, out, a = lauf("kontakt", ["Glue Tec GmbH"])
pruefe("Firma mit Leerzeichen als firma=", query(a) == {"firma": "Glue Tec GmbH"})
code, out, a = lauf("kontakt", ["Pia@Fillhub.de", "--json"])
pruefe("--json: Antwort roh, Adresse klein", code == 0 and query(a) == {"adresse": "pia@fillhub.de"} and json.loads(out)["mail_suche"] == ANTWORT["mail_suche"])
antwort["json"] = {**ANTWORT, "bekannt_im_tool": False, "zuordnung": [], "kontakte": [], "offen": {"bestellungen": [], "sendungen": [], "weitere": 0}, "journal": [], "wiki": None, "luecken": [],
                   "anrede": "Im Tool unbekannt. Erst mail_suche ausführen: gibt es Treffer, keine Vorstellung; nur ohne Treffer kurz vorstellen.",
                   "mail_suche": "in:anywhere (from:@neu-gmbh.de OR to:@neu-gmbh.de)"}
code, out, a = lauf("kontakt", ["neu-gmbh.de"])
pruefe("unbekannt: Satz und trotzdem Suche", "Im Tool unbekannt" in out and "Erst mail_suche ausführen" in out and "in:anywhere (from:@neu-gmbh.de OR to:@neu-gmbh.de)" in out)
antwort["json"] = {**ANTWORT, "journal": None}
code, out, a = lauf("kontakt", ["fillhub.de"])
pruefe("Journal null: kein Zugang", "Journal: kein Zugang für dieses Konto." in out)

# --- Namensweg unsicher (Review B1), Journal-Fehler (K3)
antwort["json"] = {**ANTWORT, "bekannt_im_tool": False, "anrede": "Zuordnung nur über den Namen, unsicher. Erst mail_suche prüfen: mit Treffern auf den letzten Austausch Bezug nehmen, ohne Treffer kurz vorstellen."}
code, out, a = lauf("kontakt", ["fillhub.de"])
pruefe("Namensweg: Achtung-Zeile, nie „keine Vorstellung“", "Achtung: nur über den Namen zugeordnet, unsicher" in out and "keine Vorstellung" not in out)
pruefe("Namensweg: Kopf „Zugeordnet (unsicher):“, nie „Bekannt im Tool“", "Zugeordnet (unsicher): Fillhub (warehouse) · über name" in out and "Bekannt im Tool" not in out)
antwort["json"] = {**ANTWORT, "journal": None, "luecken": ["Journal gerade nicht ladbar, Antwort ohne Journal-Zeilen."]}
code, out, a = lauf("kontakt", ["fillhub.de"])
pruefe("Journal-Fehler: nicht als „kein Zugang“, Lücke genannt", "kein Zugang" not in out and "Lücke: Journal gerade nicht ladbar" in out)
for eingabe in ("a<b@x.de", "a,b@x.de"):
    pruefe(f"K1: {eingabe} ist keine Adresse", cb.kontakt_param(eingabe)[0] != "adresse")
pruefe("K1: plus-Adresse ok", cb.kontakt_param("first.last+tag@x-y.de") == ("adresse", "first.last+tag@x-y.de"))

# --- Bedienfehler
for name, args in [("ohne Angabe", []), ("zwei Angaben", ["a.de", "b.de"]), ("Option statt Angabe", ["--domain"])]:
    code, out, a = lauf("kontakt", args)
    pruefe(f"{name}: Exit 2, keine Anfrage, Hilfe Kontakt", code == 2 and a is None and "Kontakt:" in out)

# --- Route fehlt (Tool älter)
antwort.update(status=404, json={"error": "Nicht gefunden."})
code, out, a = lauf("kontakt", ["fillhub.de"])
pruefe("404: Route fehlt, Satz mit Ersatz-Suche", code == 1 and "gibt es im Tool noch nicht" in out and "in:anywhere" in out)

print("\n" + ("alles grün" if fehler == 0 else f"{fehler} Fehler"))
sys.exit(1 if fehler else 0)
