#!/usr/bin/env python3
"""Prüfskript für `bestand-herkunft` (#677, 06.11.2026). Ohne Framework, ohne Netz, eigenes HOME: urlopen wird ersetzt, die Prüfung
liest die Anfrage, die `call` wirklich baut. Aufruf: /usr/bin/python3 tests/pruefe-bestand-herkunft.py   (Exit 0 = alles grün)"""
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


def pruefe(name: str, ok: bool, ausgabe: str = "") -> None:
    global fehler
    print(("ok    " if ok else "FEHLER ") + name + ("" if ok else f"\n{ausgabe}"))
    fehler += 0 if ok else 1


anfragen = []
antwort = {}


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def falsches_urlopen(req, timeout=None):
    anfragen.append(req.full_url)
    if antwort.get("status"):
        raise urllib.error.HTTPError(req.full_url, antwort["status"], "x", {}, io.BytesIO(antwort["roh"]))
    return Antwort(json.dumps(antwort["json"]).encode())


cb.urllib.request.urlopen = falsches_urlopen


def lauf(args, json_antwort=None, status=None, roh=b""):
    anfragen.clear()
    antwort.update(json=json_antwort, status=status, roh=roh)
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    try:
        cb.main(["cbtool.py"] + list(args))
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code)
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return puffer.getvalue()


SKU = "SKU-TEST-1"
STAND = {"abgerufen": "2026-11-06T08:47:00Z", "daten": "live"}


def bew(datum, menge, saldo, art="Wareneingang", **x):
    return dict({"datum": datum, "menge": menge, "art": art, "bestellung": None, "einsendung": None, "amazonId": None, "storno": False, "zaehlt": True, "grund": None, "quelle": "manual", "saldo": saldo}, **x)


lager_test = {
    "standort": "Lager-Test", "standortArt": "3pl", "summeBewegungen": 50, "lagerbestand": 50, "stimmt": True,
    "bewegungen": [
        bew("2026-01-02", 100, 100, bestellung="PO-TEST-1"),
        bew("2026-01-03", -100, 0, art="Abholung, unterwegs", einsendung="IN-TEST-1", amazonId="FBA-TEST-1"),
        bew("2026-01-04", 50, 50),
        bew("2026-01-05", -50, 0, art="Korrektur", storno=True),
        bew("2026-01-06", 50, 50),
        bew("2026-01-01", 7, 50, art="Inventur", zaehlt=False, grund="Nicht bestandswirksam, Historie vor der Inventur oder so gebucht", quelle="sheet_import"),
    ],
}
STIMMT = "Stimmt: Rechnung gleich Tool-Bestand, keine Zählung."
gut = {"sku": SKU, "name": "Testprodukt", "link": "https://x/products/" + SKU, "abgleich": {"stimmt": True, "text": STIMMT}, "lager": [lager_test], "stand": STAND}

aus = lauf(["bestand-herkunft", SKU], gut)
pruefe("Pfad mit SKU wörtlich", anfragen[0].endswith(f"/api/brain-read/bestand/{SKU}/herkunft"), anfragen[0])
pruefe("Abgleich steht oben", aus.splitlines()[1] == "Abgleich mit dem Lagerbestand: " + STIMMT, aus)
pruefe("Lager mit beiden Zahlen", "Lager-Test: Bewegungen 50, Lagerbestand 50, stimmt\n" in aus, aus)
pruefe("+100 mit PO wörtlich", "02.01.2026 · +100 · Wareneingang · PO-TEST-1 · Saldo 100\n" in aus, aus)
pruefe("-100 mit Einsendung und Amazon-ID", "03.01.2026 · -100 · Abholung, unterwegs · IN-TEST-1 · FBA-TEST-1 · Saldo 0\n" in aus, aus)
pruefe("Storno sichtbar", "-50 · Korrektur · Storno · Saldo 0\n" in aus, aus)
pruefe("Historie mit Grund", "+7 · Inventur · Saldo 50 · zählt nicht: Nicht bestandswirksam, Historie vor der Inventur oder so gebucht\n" in aus, aus)
pruefe("Stand und Link", "Link: https://x/products/" + SKU in aus and "abgerufen" in aus, aus)

falsch = dict(gut, abgleich={"stimmt": False, "text": "Stimmt nicht. Lager-Test: Bewegungen 50, Lagerbestand 40."}, lager=[dict(lager_test, lagerbestand=40, stimmt=False)])
aus = lauf(["bestand-herkunft", SKU], falsch)
pruefe("Abweichung oben und am Lager", "Stimmt nicht. Lager-Test: Bewegungen 50, Lagerbestand 40." in aus and "Lagerbestand 40, STIMMT NICHT\n" in aus, aus)

# FBA in der echten Form: Trigger setzt posting = false, kein Saldo, keine Summe, eigener Grund, kein „Bewegungen 0“.
GRUND_AMAZON = "Amazon-Lager, wird nicht als Lagerbestand geführt"
fba = dict(gut, abgleich={"stimmt": None, "text": "Nichts zu vergleichen: kein Lager mit Lagerbestand für diese SKU."}, lager=[{"standort": "Amazon FBA", "standortArt": "fba", "summeBewegungen": None, "lagerbestand": None, "stimmt": None, "bewegungen": [bew("2026-01-02", 8, None, zaehlt=False, grund=GRUND_AMAZON)]}])
aus = lauf(["bestand-herkunft", SKU], fba)
pruefe("FBA ohne Vergleich", "Amazon FBA: kein Lagerbestand zum Vergleichen\n" in aus and "Bewegungen 0" not in aus, aus)
pruefe("FBA: Grund statt Saldo und Historie", "+8 · Wareneingang · zählt nicht: " + GRUND_AMAZON + "\n" in aus and "Saldo" not in aus and "Historie" not in aus, aus)
pruefe("Nichts zu vergleichen steht oben", "Nichts zu vergleichen" in aus.splitlines()[1], aus)

aus = lauf(["bestand-herkunft", "A B/C"], gut)
pruefe("Sonderzeichen im Pfad kodiert", anfragen[0].endswith("/bestand/A%20B%2FC/herkunft"), anfragen[0])
aus = lauf(["bestand-herkunft", "UNBEKANNT"], status=404, roh=json.dumps({"error": "SKU UNBEKANNT nicht gefunden."}).encode())
pruefe("Unbekannte SKU: Text des Tools", aus.strip() == "SKU UNBEKANNT nicht gefunden.", aus)
aus = lauf(["bestand-herkunft", SKU], status=404, roh=b"<html>404</html>")
pruefe("Älteres Tool: klarer Satz", cb.HERKUNFT_FEHLT in aus, aus)
aus = lauf(["bestand-herkunft"], gut)
pruefe("Ohne SKU: Bedienfehler, keine Anfrage", "braucht genau eine SKU" in aus and not anfragen, aus)
aus = lauf(["bestand-herkunft", SKU, "--x"], gut)
pruefe("Zu viel: Bedienfehler, keine Anfrage", "braucht genau eine SKU" in aus and not anfragen, aus)
aus = lauf(["bestand-herkunft", "--help"], gut)
pruefe("--help geht nicht als SKU ans Tool", "braucht genau eine SKU" in aus and not anfragen, aus)

print("Alle grün" if not fehler else f"{fehler} Fehler")
sys.exit(1 if fehler else 0)
