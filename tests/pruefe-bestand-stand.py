#!/usr/bin/env python3
"""Prüfskript für den Stand des Amazon-Bestands in `bestand` (19.11.2026). Ohne Framework, ohne Netz, eigenes HOME, Uhr fest,
nur Platzhalter. Das Tool sagt, von wann der Bestand ist (`bestandStand`, `stand.amazonBestandStand`, je SKU `fba.abruf`);
das Plugin zeigt den Satz wörtlich und genau einmal. Fehlfall: ein älteres Tool ohne die Felder ändert die Ausgabe nicht.
Aufruf: /usr/bin/python3 tests/pruefe-bestand-stand.py   (Exit 0 = alles grün)"""
import importlib.util, io, json, os, sys, tempfile
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

UHR = {"jetzt": datetime(2026, 11, 19, 16, 0, tzinfo=timezone.utc)}  # 19.11.2026 17:00 Berlin
cb._jetzt = lambda: UHR["jetzt"]
cb._heute_jahr = lambda: UHR["jetzt"].year

fehler = 0


def pruefe(name, ok, ausgabe=""):
    global fehler
    print(("ok    " if ok else "FEHLER ") + name + ("" if ok else f"\n{ausgabe}"))
    fehler += 0 if ok else 1


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


antwort = {}
cb.urllib.request.urlopen = lambda req, timeout=None: Antwort(json.dumps(antwort["json"]).encode())


def lauf(args, json_antwort):
    antwort["json"] = json_antwort
    alt_out, alt_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = puffer = io.StringIO()
    try:
        cb.main(["cbtool.py"] + list(args))
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code)
    except Exception as e:  # ein Abbruch ist ein Fehlfall, kein Ende des Prüfskripts
        print(f"Abbruch: {type(e).__name__}: {e}")
    finally:
        sys.stdout, sys.stderr = alt_out, alt_err
    return puffer.getvalue()


def stand_zeile(aus):
    return [z for z in aus.splitlines() if z.startswith("Stand: ")]


FBA = {"verfuegbar": 100, "reserviert": 5, "zulaufWorking": 0, "zulaufShipped": 10, "zulaufReceiving": 0, "inUmlagerung": 0, "datum": "2026-11-17"}
B = {"sku": "SKU-123", "name": "Kleber", "marktplatz": "DE", "fba": FBA, "fbaHinweis": None, "lager": [{"standort": "Lager A", "stueck": 40}],
     "lagerGesamt": 40, "beimHersteller": 0, "unterwegs": {"stueck": 0, "anlieferungen": []}, "hinweis": "Reichweite steht im Tool unter Bestandsprognose.", "link": "http://x/p"}
B2 = dict(B, sku="SKU-456", name="Gutschein")
STAND_ALT = {"abgerufen": "2026-11-19T16:00:00Z", "daten": "synchronisiert", "amazonBestandTag": "2026-11-17", "amazonSync": "2026-11-19T05:30:33.666+00:00", "lager": "live"}
ZEILE_ALT = "Stand: abgerufen 19.11.2026 17:00, Daten synchronisiert, Amazon-Bestand vom 17.11., Amazon-Abgleich 19.11.2026 06:30, Lager live"


def mit_abruf(b, abruf):
    return dict(b, fba=dict(b["fba"], abruf=abruf))


def antwort_neu(satz_bot, bs, abruf, tag="2026-11-17"):
    stand = {"abgerufen": "2026-11-19T16:00:00Z", "daten": "synchronisiert", "amazonBestandStand": satz_bot, "amazonBestandTag": tag,
             "amazonSync": "2026-11-19T05:30:33.666+00:00", "lager": "live"}
    return {"bestand": [mit_abruf(B, abruf), mit_abruf(B2, abruf)], "anzahl": 2, "stand": stand,
            "bestandAlter": {"stichtag": tag, "tage": 2, "warnung": False, "schwelleTage": 2}, "bestandStand": bs}


# 1. Älteres Tool ohne die neuen Felder: Ausgabe bis aufs Zeichen wie bis 0.20.0
alt = lauf(["bestand", "--suche", "SKU"], {"bestand": [B, B2], "anzahl": 2, "stand": STAND_ALT})
pruefe("älteres Tool: Stand-Zeile unverändert", stand_zeile(alt) == [ZEILE_ALT], alt)
pruefe("älteres Tool: je SKU „(vom 17.11.)“", alt.count("Amazon-Zulauf 10 (vom 17.11.)") == 2, alt)
erwartet_alt = (
    "Bestand zu „SKU“ (2):\n"
    "  SKU-123 · Kleber · DE · FBA 100 verfügbar, 5 reserviert, Amazon-Zulauf 10 (vom 17.11.) · Lager 40 (Lager A 40) · unterwegs 0\n"
    "    Amazon-Zulauf: working 0, shipped 10, receiving 0\n"
    "    Link: http://x/p\n"
    "  SKU-456 · Gutschein · DE · FBA 100 verfügbar, 5 reserviert, Amazon-Zulauf 10 (vom 17.11.) · Lager 40 (Lager A 40) · unterwegs 0\n"
    "    Amazon-Zulauf: working 0, shipped 10, receiving 0\n"
    "    Link: http://x/p\n"
    "Hinweis: Reichweite steht im Tool unter Bestandsprognose.\n"
    + ZEILE_ALT + "\n"
)
pruefe("älteres Tool: ganze Ausgabe wie bis 0.20.0", alt == erwartet_alt, alt)

# 2. Heutiges Live-Tool, Schalter aus: Satz Openbridge, kein Abruf je SKU
OB = {"quelle": "openbridge", "abruf": None, "abrufBerlin": None, "stichtag": "2026-11-17", "satz": "Amazon-Bestand vom 17.11. (Openbridge), 2 Tage alt"}
aus = lauf(["bestand", "--suche", "SKU"], antwort_neu(OB["satz"], OB, None))
zeile = "Stand: abgerufen 19.11.2026 17:00, Daten synchronisiert, Bestand: Amazon-Bestand vom 17.11. (Openbridge), 2 Tage alt, Amazon-Abgleich 19.11.2026 06:30, Lager live"
pruefe("Schalter aus: Satz des Tools wörtlich, Stichtag entfällt", stand_zeile(aus) == [zeile], aus)
pruefe("Schalter aus: kein Rohname", "amazonBestandStand" not in aus and "bestandStand" not in aus, aus)
pruefe("Schalter aus: je SKU weiter „(vom 17.11.)“", aus.count("Amazon-Zulauf 10 (vom 17.11.)") == 2, aus)
pruefe("Schalter aus: außer der Stand-Zeile alles gleich", aus.replace(zeile, ZEILE_ALT) == alt, aus + alt)

# 3. Schalter an, Abruf heute 06:10 (Berlin)
HEUTE = {"quelle": "amazon_direkt", "abruf": "2026-11-19T05:10:00.000Z", "abrufBerlin": "19.11.2026 06:10", "stichtag": "2026-11-18", "satz": "Amazon-Bestand heute 06:10"}
aus = lauf(["bestand", "--suche", "SKU"], antwort_neu("Amazon-Bestand heute 06:10 (Amazon direkt)", HEUTE, HEUTE["abruf"], tag="2026-11-18"))
pruefe("heute: Stand genau einmal, wörtlich", stand_zeile(aus) == ["Stand: abgerufen 19.11.2026 17:00, Daten synchronisiert, Bestand: Amazon-Bestand heute 06:10 (Amazon direkt), Amazon-Abgleich 19.11.2026 06:30, Lager live"], aus)
pruefe("heute: „Amazon-Bestand“ steht genau einmal", aus.count("Amazon-Bestand") == 1, aus)
pruefe("heute: je SKU „(heute 06:10)“, nie „vom 18.11.“", aus.count("Amazon-Zulauf 10 (heute 06:10)") == 2 and "vom 18.11." not in aus and "(vom " not in aus, aus)
pruefe("heute: kein Rohname", "amazonBestandStand" not in aus and "abruf" not in aus, aus)

# 4. Abruf von gestern (Morgenstand von heute fehlt)
GESTERN = {"quelle": "amazon_direkt", "abruf": "2026-11-18T05:10:00Z", "abrufBerlin": "18.11.2026 06:10", "stichtag": "2026-11-17", "satz": "Amazon-Bestand vom 18.11. 06:10, 1 Tag alt"}
aus = lauf(["bestand", "--suche", "SKU"], antwort_neu(GESTERN["satz"] + " (Amazon direkt)", GESTERN, GESTERN["abruf"]))
pruefe("gestern: Satz wörtlich", "Bestand: Amazon-Bestand vom 18.11. 06:10, 1 Tag alt (Amazon direkt), Amazon-Abgleich" in aus and aus.count("Amazon-Bestand") == 1, aus)
pruefe("gestern: je SKU in derselben Form", aus.count("Amazon-Zulauf 10 (vom 18.11. 06:10, 1 Tag alt)") == 2, aus)
UHR["jetzt"] = datetime(2026, 11, 20, 16, 0, tzinfo=timezone.utc)
aus = lauf(["bestand", "--suche", "SKU"], antwort_neu("x", GESTERN, GESTERN["abruf"]))
pruefe("vorgestern: „2 Tage alt“", aus.count("(vom 18.11. 06:10, 2 Tage alt)") == 2, aus)
UHR["jetzt"] = datetime(2026, 11, 19, 16, 0, tzinfo=timezone.utc)

# 5. Abruf kurz nach Mitternacht Berliner Zeit (UTC noch Vortag) zählt als heute; Sommerzeit
aus = lauf(["bestand", "--suche", "SKU"], antwort_neu("x", HEUTE, "2026-11-18T23:30:00Z"))
pruefe("Berliner Tag: 23:30 UTC am Vortag ist heute 00:30", aus.count("(heute 00:30)") == 2, aus)
UHR["jetzt"] = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
aus = lauf(["bestand", "--suche", "SKU"], antwort_neu("x", HEUTE, "2026-07-01T04:10:00Z"))
pruefe("Sommerzeit: 04:10 UTC ist 06:10", aus.count("(heute 06:10)") == 2, aus)
UHR["jetzt"] = datetime(2026, 11, 19, 16, 0, tzinfo=timezone.utc)

# 6. Rückfall auf Openbridge bei eingeschaltetem Schalter: Satz mit Openbridge, je SKU „(vom …)“
RUECK = dict(OB, stichtag="2026-11-16", satz="Amazon-Bestand vom 16.11. (Openbridge), 3 Tage alt")
s = antwort_neu(RUECK["satz"], RUECK, None, tag="2026-11-16")
s["stand"]["hinweis"] = "Amazon-Bestand vom 16.11., 3 Tage alt: Die Prognose rechnet ihn als heutigen Bestand, Verkäufe seither sind nicht abgezogen (normal höchstens 2 Tage)."
s["bestand"] = [dict(b, fba=dict(b["fba"], datum="2026-11-16", abruf=None)) for b in s["bestand"]]
aus = lauf(["bestand", "--suche", "SKU"], s)
pruefe("Rückfall: Satz Openbridge wörtlich, kein Stichtag daneben", "Bestand: Amazon-Bestand vom 16.11. (Openbridge), 3 Tage alt, Amazon-Abgleich" in aus and ", Amazon-Bestand vom 16.11., Amazon-Abgleich" not in aus, aus)
pruefe("Rückfall: je SKU „(vom 16.11.)“", aus.count("Amazon-Zulauf 10 (vom 16.11.)") == 2, aus)
pruefe("Rückfall: Stand genau einmal, Hinweis ohne die Standangabe unter „Hinweis:“",
       stand_zeile(aus) == ["Stand: abgerufen 19.11.2026 17:00, Daten synchronisiert, Bestand: Amazon-Bestand vom 16.11. (Openbridge), 3 Tage alt, Amazon-Abgleich 19.11.2026 06:30, Lager live, "
                            "Hinweis: Die Prognose rechnet ihn als heutigen Bestand, Verkäufe seither sind nicht abgezogen (normal höchstens 2 Tage)."]
       and aus.count("16.11.") == 3 and "hinweis" not in aus, aus)  # 16.11.: Stand-Zeile und zwei SKU-Zeilen
s["stand"]["hinweis"] = "Amazon-Bestand vom 15.11., 4 Tage alt: Anderer Stichtag."
aus = lauf(["bestand", "--suche", "SKU"], s)
pruefe("Rückfall: Hinweis mit anderem Anfang ganz unter „Hinweis:“", ", Hinweis: Amazon-Bestand vom 15.11., 4 Tage alt: Anderer Stichtag." in aus and "hinweis" not in aus, aus)
s["stand"]["hinweis"] = "Shops sind gerade nicht abgeglichen."
aus = lauf(["bestand", "--suche", "SKU"], s)
pruefe("Rückfall: Hinweis ohne Doppelpunkt ganz", ", Hinweis: Shops sind gerade nicht abgeglichen." in aus, aus)
alt_hinweis = lauf(["bestand", "--suche", "SKU"], {"bestand": [B], "anzahl": 1, "stand": dict(STAND_ALT, hinweis="Amazon-Bestand vom 17.11., 3 Tage alt: Rest.")})
pruefe("älteres Tool mit Hinweis: wie bis 0.20.0 („hinweis“ klein, ganz)", stand_zeile(alt_hinweis) == [ZEILE_ALT + ", hinweis Amazon-Bestand vom 17.11., 3 Tage alt: Rest."], alt_hinweis)

# 7. bestandStand ohne stand.amazonBestandStand: Satz an der Stelle des Stichtags
s = antwort_neu("x", HEUTE, HEUTE["abruf"])
del s["stand"]["amazonBestandStand"]
aus = lauf(["bestand", "--suche", "SKU"], s)
pruefe("nur bestandStand: Satz an der Stelle des Stichtags", stand_zeile(aus) == ["Stand: abgerufen 19.11.2026 17:00, Daten synchronisiert, Bestand: Amazon-Bestand heute 06:10, Amazon-Abgleich 19.11.2026 06:30, Lager live"], aus)

# 8. Unbekannte künftige Schlüssel: erscheinen gar nicht (kein Rohname, keine nackte Zahl, kein leeres Glied)
s = {"bestand": [B], "anzahl": 1, "stand": dict(STAND_ALT, kuenftigSatz="Shops bis gestern vollständig", kuenftigZeit="2026-11-19T05:10:00Z",
                                                  kuenftigZahl=3, kuenftigNull=0, kuenftigLeer=None, kuenftigBlank="   ", kuenftigListe=["a"])}
aus = lauf(["bestand", "--suche", "SKU"], s)
pruefe("unbekannt: kein Rohname", "kuenftig" not in aus, aus)
pruefe("unbekannt: nichts davon in der Stand-Zeile", stand_zeile(aus) == [ZEILE_ALT], aus)

# 9. Unerwartete Typen der neuen Felder: nie Abbruch, gilt als fehlend (alte Anzeige)
for name, fba_abruf, bs, satz_bot in (
    ("abruf Zahl", 1763529000, None, None),
    ("abruf Objekt", {"zeit": "06:10"}, None, None),
    ("abruf Liste", ["2026-11-19T05:10:00Z"], None, None),
    ("abruf Text, kein Zeitpunkt", "gleich", None, None),
    ("bestandStand Text", None, "Amazon-Bestand heute 06:10", None),
    ("satz Zahl", None, {"quelle": "amazon_direkt", "satz": 5}, None),
    ("satz Liste", None, {"satz": ["Amazon-Bestand heute 06:10"]}, None),
    ("amazonBestandStand Objekt", None, None, {"satz": "x"}),
    ("amazonBestandStand Zahl", None, None, 7),
):
    s = {"bestand": [mit_abruf(B, fba_abruf), mit_abruf(B2, fba_abruf)], "anzahl": 2, "stand": dict(STAND_ALT)}
    if bs is not None:
        s["bestandStand"] = bs
    if satz_bot is not None:
        s["stand"] = dict(list(STAND_ALT.items())[:2] + [("amazonBestandStand", satz_bot)] + list(STAND_ALT.items())[2:])
    aus = lauf(["bestand", "--suche", "SKU"], s)
    pruefe(f"Typ: {name} › kein Abbruch, alte Anzeige", aus == alt, aus)

# 10. stand.amazonBestandStand null oder leer: gilt als fehlend
for leer in (None, "", "  "):
    st = dict(list(STAND_ALT.items())[:2] + [("amazonBestandStand", leer)] + list(STAND_ALT.items())[2:])
    aus = lauf(["bestand", "--suche", "SKU"], {"bestand": [B, B2], "anzahl": 2, "stand": st})
    pruefe(f"amazonBestandStand {leer!r} ohne bestandStand: alte Anzeige, nie „Bestand: unbekannt“", aus == alt, aus)
    aus = lauf(["bestand", "--suche", "SKU"], {"bestand": [B, B2], "anzahl": 2, "stand": st, "bestandStand": OB})
    pruefe(f"amazonBestandStand {leer!r} mit bestandStand: dessen Satz", stand_zeile(aus) == [zeile], aus)

# 11. Andere Befehle: bestellplanung mit hinweis wie bisher (Beschriftung „hinweis“ unverändert)
aus = lauf(["bestellplanung"], {"zeilen": [], "anzahl": 0, "stand": {"abgerufen": "2026-11-19T16:00:00Z", "daten": "live", "amazonBestandTag": "2026-11-17", "amazonBisTag": "2026-11-17", "letzterLauf": None, "hinweis": "Vorschläge eben gerechnet."}})
pruefe("bestellplanung: Stand-Zeile wie bis 0.20.0", "Stand: abgerufen 19.11.2026 17:00, Daten live, Amazon-Bestand vom 17.11., Amazon-Verkäufe bis 17.11., letzter Planungslauf unbekannt, hinweis Vorschläge eben gerechnet." in aus, aus)

print("Alle grün" if not fehler else f"{fehler} Fehler")
sys.exit(1 if fehler else 0)
