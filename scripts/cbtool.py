#!/usr/bin/env python3
"""Gemeinsamer Kern des Plugins cb-brain-client: spricht mit dem CleverBrands-Tool über den
persönlichen Schlüssel (Bearer cbw_…). Kein GitHub, kein GBrain-Login — das Tool ist die einzige Tür.

Dateien:  ~/.cb-brain/tool-key   der Schlüssel aus dem Tool (Wiki › Verbinden)
          ~/.cb-brain/tool-url   optional, Standard https://company-interface.vercel.app

Befehle:  cbtool.py setup <schlüssel> [url] Schlüssel prüfen (Ping) und speichern; url nur für Vorschau-Adressen
          cbtool.py ping                    Verbindung prüfen
          cbtool.py search <frage> [n]      Treffer als JSON
          cbtool.py drop [--via session] <text>                 Text in die Inbox (session = Sitzungsauszug)
          cbtool.py drop-file [--started <epoch>] [--scanned <n>] <pfad> [...]
                                            Dateien (.md/.txt) in die Inbox; Maße für /wiki-extract

Aufgaben: cbtool.py aufgaben [--fuer ich|alle|<name>] [--status offen|erledigt|alle] [--suche <text>] [--limit <n>]
          cbtool.py aufgabe CB-123
          cbtool.py aufgabe-neu --titel <text> [--beschreibung <text>] [--fuer <name>] [--faellig YYYY-MM-DD] [--prio 1-4]
                                [--groesse klein|mittel|gross]
          cbtool.py aufgabe-aendern CB-123 [--erledigt | --offen] [--notiz <text>] [--faellig YYYY-MM-DD | --faellig-weg]
                                            [--grund <text>] [--prio 1-4] [--fuer <name> | --fuer-weg]
                                            [--groesse klein|mittel|gross]
          cbtool.py erledigt --titel <text> --groesse klein|mittel|gross [--notiz <text>]
                                            erledigte Arbeit für sich selbst eintragen (nur nach Ja der Person)
          --groesse: klein unter 1 Stunde, mittel etwa ein halber Tag, groß ab einem Tag (Punkte 1/3/5).
          --grund: ein Satz (1-300 Zeichen), warum sich eine bestehende Frist ändert; nur mit --faellig
          oder --faellig-weg. Ab 19.10.2026 Pflicht, sobald die Aufgabe schon eine Frist hatte.
          Prio: 1 niedrig, 2 mittel, 3 hoch, 4 dringend. Löschen geht nur im Tool.

Ware:     cbtool.py bestellungen [--status offen|alle] [--suche <text>] [--limit <n>]
          cbtool.py bestellung PO-049                    (wörtlich oder eindeutiger Anfang)
          cbtool.py sendungen [--status offen|alle] [--suche <text>] [--limit <n>]
          cbtool.py sendung IN-2026-0039                 (oder Amazon-Shipment-ID)
          cbtool.py bestand [--suche <sku|name>] [--limit <n>]
          cbtool.py bestellplanung [--status faellig|ueberfaellig|alle|vorschlag|angepasst|bestaetigt]
                                   [--suche <text>] [--marktplatz DE|US|alle] [--limit <n>]
          cbtool.py absatz [--suche <sku|name>] [--von YYYY-MM-DD] [--bis YYYY-MM-DD]
                           [--kanal amazon|shop|alle] [--je produkt|tag|woche]
          Nur lesen. Limit 1-200 (Standard 50, bestand 200). Bis drei Treffer: mit Einzelheiten und Link.

Kasse:    cbtool.py kasse                                    Stand, eigene Meldungen, zu prüfende Meldungen
          cbtool.py kasse-melden --betrag 6,60 --datum YYYY-MM-DD --empfaenger <name> [--fuer <name>]
          cbtool.py kasse-widersprechen --meldung <nr> --grund <text>
          cbtool.py kasse-erlassen --fuer <name> --tag YYYY-MM-DD [--bis YYYY-MM-DD] --grund <text>
          Das Tool rechnet und entscheidet, wer was darf (Kassenwart Mats, für Mats' Beträge Max).
          Das Skript liest keine Bilder: Betrag, Datum und Empfänger liest Claude vom Screenshot ab.
"""
# macOS bringt ab Werk nur Python 3.9 mit, und `python3` zeigt ohne Homebrew darauf (Issue #1, 18.09.).
# Ohne diese Zeile wertet 3.9 die Typhinweise `str | None` beim Laden aus und bricht mit TypeError ab.
from __future__ import annotations

import json, os, re, stat, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~/.cb-brain")
TOKEN_FILE = os.path.join(HOME, "tool-key")
URL_FILE = os.path.join(HOME, "tool-url")
DEFAULT_URL = "https://company-interface.vercel.app"
TIMEOUT = 8.0
# Dateien schreibt der Server einzeln ins Inbox-Repo, ein Commit je Datei, rund 0,7 s je Stück.
# 21 Dateien liefen deshalb am 18.09. in den 8-Sekunden-Abbruch, während der Server weiterschrieb;
# die Wiederholung legte alles doppelt an. Drop und drop-file warten länger (Issue #1 im Tool-Repo).
TIMEOUT_DROP = 180.0
BATCH_FILES = 5  # je Aufruf, damit eine Störung höchstens fünf Dateien betrifft


def _read(path: str) -> str | None:
    try:
        return open(path, encoding="utf-8").read().strip() or None
    except OSError:
        return None


def tool_url() -> str:
    env = os.environ.get("CB_TOOL_URL")
    if env:
        return env.rstrip("/")
    try:
        return open(URL_FILE, encoding="utf-8").read().strip().rstrip("/") or DEFAULT_URL
    except OSError:
        return DEFAULT_URL


def token() -> str | None:
    try:
        t = open(TOKEN_FILE, encoding="utf-8").read().strip()
        return t or None
    except OSError:
        return None


def call(path: str, body=None, method: str = "POST", key: str | None = None, timeout: float = TIMEOUT, via: str = "skill", plain_errors: bool = False, bei_404: str | None = None):
    # plain_errors: Fehlertext des Servers ohne „Tool antwortet …“ und mit der Liste gültiger Namen (Aufgaben-Befehle).
    # bei_404: eigener Text, wenn es die Route im Tool noch nicht gibt (Kasse vor dem Live-Gang).
    key = key or token()
    if not key:
        raise SystemExit("Kein Schlüssel. Im Tool unter Wiki › Verbinden erzeugen, dann: /wiki-setup <schlüssel>")
    data = json.dumps(body).encode() if body is not None else None
    # X-CB-Via: der Weg der Anfrage für die Messung im Tool (hook | skill | session | extraktion), kein Inhalt.
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json", "X-CB-Via": via}
    bypass = os.environ.get("CB_VERCEL_BYPASS") or _read(os.path.join(HOME, "bypass"))
    if bypass:
        headers["x-vercel-protection-bypass"] = bypass  # nur für Vorschau-Adressen hinter Vercel-SSO
    req = urllib.request.Request(tool_url() + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        msg = ""
        namen = []
        try:
            payload = json.loads(e.read().decode("utf-8"))
            msg = payload.get("error", "")
            namen = payload.get("namen") or []
            treffer = payload.get("treffer") or []  # mehrdeutige Bestellnummer (Lesezugang)
            if len(treffer) > 10:
                namen = treffer[:10] + [f"und {len(treffer) - 10} weitere; die Nummer genauer angeben"]
            elif treffer:
                namen = treffer
            # Der Server nennt bei einem Teilfehler die schon geschriebenen Pfade; sie gehören
            # in die Meldung, sonst wirft der Nutzer alles erneut ein (Astra-Review 18.09.2026).
            for p in payload.get("paths", []):
                print(f"In der Inbox: {p}")
        except Exception:
            pass
        if e.code == 401:
            raise SystemExit("Schlüssel wird nicht angenommen (401). Im Tool unter Wiki › Verbinden prüfen oder neu erzeugen.")
        if e.code == 404 and bei_404:
            raise SystemExit(bei_404)
        if plain_errors:
            if namen and "Möglich:" not in msg:  # nicht doppelt, falls der Server die Namen schon nennt
                msg = (msg.rstrip() + (" " if msg.rstrip().endswith(".") else ". ") if msg else "") + "Möglich: " + ", ".join(namen)
            raise SystemExit(msg or f"Tool antwortet {e.code}.")
        raise SystemExit(f"Tool antwortet {e.code}: {msg}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Tool nicht erreichbar ({tool_url()}): {e.reason}")


def cmd_setup(key: str, url: str | None = None) -> None:
    key = key.strip()
    if not key.startswith("cbw_") or len(key) != 36:
        raise SystemExit("Das sieht nicht wie ein Schlüssel aus (erwartet cbw_ und 32 Zeichen).")
    os.makedirs(HOME, exist_ok=True)
    if url:
        # Vorschau-Adresse aus dem Tool (die Onboarding-Seite hängt sie an, wenn sie nicht auf Produktion läuft).
        with open(URL_FILE, "w", encoding="utf-8") as f:
            f.write(url.strip().rstrip("/") + "\n")
    else:
        # Ohne Adresse gilt wieder Produktion: eine alte Vorschau-Adresse darf nicht hängen bleiben.
        try:
            os.remove(URL_FILE)
        except OSError:
            pass
    res = call("/api/brain-read/ping", method="GET", key=key)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(key + "\n")
    os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print(f"Verbunden als {res.get('name', '?')}. Schlüssel liegt in {TOKEN_FILE}.")


def cmd_ping() -> None:
    res = call("/api/brain-read/ping", method="GET")
    print(f"Verbunden als {res.get('name', '?')} ({tool_url()}).")


def cmd_search(query: str, limit: int = 5) -> None:
    res = call("/api/brain-read/search", {"query": query, "limit": limit})
    print(json.dumps(res.get("hits", []), ensure_ascii=False, indent=2))


def cmd_drop(text: str, via: str | None = None) -> None:
    body = {"text": text}
    if via == "session":
        body["via"] = "session"  # Sitzungsauszug aus /drop session, nur für die Messung
    res = call("/api/brain-read/drop", body, timeout=TIMEOUT_DROP, via=via or "skill")
    for p in res.get("paths", []):
        print(f"In der Inbox: {p}")
    print("Sichtbar im Wiki nach dem nächsten Ingest-Lauf (nachts).")


MAX_CHARS_FILE = 400_000  # Grenze des Eingangs; darüber lehnt der Server ab (413)


def cmd_drop_files(paths: list[str], started: float | None = None, scanned: int | None = None) -> None:
    # Erst alles lesen und prüfen, dann senden: Sonst liegen die ersten Stapel schon im Eingang,
    # während der Abbruch behauptet, es sei nichts eingeworfen (Astra-Review 18.09.2026).
    files = []
    zu_gross = []
    leer = []
    for p in paths:
        p = os.path.expanduser(p)
        if not p.lower().endswith((".md", ".txt", ".markdown")):
            raise SystemExit(f"Nur .md oder .txt: {p}")
        with open(p, encoding="utf-8", errors="replace") as f:
            text = f.read()
        name = os.path.basename(p)
        if len(text.strip()) == 0:
            leer.append(name)
            continue
        # Wie JavaScript zählen (UTF-16-Einheiten), sonst lässt der Client Dateien durch,
        # die der Server ablehnt (Astra-Review 18.09.2026, dritter Durchgang, Befund 3).
        laenge = len(text.strip().encode("utf-16-le")) // 2
        if laenge > MAX_CHARS_FILE:
            zu_gross.append(f"{name} ({laenge} Zeichen)")
            continue
        files.append({"name": name, "text": text})
    if zu_gross:
        raise SystemExit("Zu groß für den Eingang (Grenze %d Zeichen), nichts eingeworfen:\n  %s\nBitte teilen und erneut einwerfen." % (MAX_CHARS_FILE, "\n  ".join(zu_gross)))
    if leer:
        print(f"Übersprungen, weil leer: {', '.join(leer)}")
    if not files:
        raise SystemExit("Keine Datei mit Inhalt.")
    # In Stapeln senden: der Server schreibt einen Commit je Datei, ein großer Aufruf lief am 18.09.
    # in den Abbruch, während er weiterschrieb. Der letzte Stapel trägt die Maße aus /wiki-extract.
    paths = []
    for i in range(0, len(files), BATCH_FILES):
        batch = files[i:i + BATCH_FILES]
        body = {"files": batch}
        if (started or scanned) and i + BATCH_FILES >= len(files):
            # `total` ist die Zahl aller Dateien dieses Einwurfs; ohne sie zählte die Messung nur
            # den letzten Stapel (Astra-Review 18.09.2026, Befund 6).
            body["extract"] = {"ms": int((time.time() - started) * 1000) if started else None, "scanned": scanned, "total": len(files)}
        try:
            res = call("/api/brain-read/drop", body, timeout=TIMEOUT_DROP, via="extraktion")
        except BaseException:  # auch Zeitlimit und Abbruch: der Nutzer muss den Stand sehen
            # Was vorher durchging, liegt im Eingang. Das muss der Nutzer sehen, sonst wirft er
            # alles erneut ein (Astra-Review 18.09.2026, zweiter Durchgang, Befund 3).
            for p in paths:
                print(f"In der Inbox: {p}")
            print(f"Abbruch bei Stapel ab Datei {i + 1} von {len(files)}. Die oben genannten liegen im Eingang; ob dieser Stapel noch angekommen ist, ist offen. Vor einem erneuten Versuch im Tool unter Wiki nachsehen.")
            raise
        paths.extend(res.get("paths", []))
    for p in paths:
        print(f"In der Inbox: {p}")
    print("Sichtbar im Wiki nach dem nächsten Ingest-Lauf (nachts).")


def _pop_option(args: list[str], name: str) -> str | None:
    """Entfernt `--name wert` aus args und gibt wert zurück."""
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            val = args[i + 1]
            del args[i:i + 2]
            return val
        del args[i]
    return None


# ---------------------------------------------------------------- Aufgaben (Vertrag T-15, 14.10.2026)

AUFGABEN = "/api/brain-read/aufgaben"
try:
    from zoneinfo import ZoneInfo  # ab 3.9 dabei
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:  # ohne Zeitzonendaten bleibt der Tag in der Zone des Servers
    BERLIN = None


def _tag(wert: str | None, jahr: bool = False) -> str | None:
    """`2026-10-16` oder ISO-Zeitpunkt → `16.10.` (Zeitpunkte in Europe/Berlin)."""
    if not wert:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$", wert.strip())
    if not m:
        return wert
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if m.group(4) and m.group(7):  # Zeitpunkt mit Zone: auf Berliner Kalendertag umrechnen
        tz = m.group(7)
        off = 0 if tz == "Z" else (1 if tz[0] == "+" else -1) * (int(tz[1:3]) * 60 + int(tz[-2:]))
        try:
            t = datetime(y, mo, d, int(m.group(4)), int(m.group(5)), int(m.group(6) or 0), tzinfo=timezone(timedelta(minutes=off)))
            if BERLIN:
                t = t.astimezone(BERLIN)
            y, mo, d = t.year, t.month, t.day
        except ValueError:
            pass
    return f"{d:02d}.{mo:02d}." + (str(y) if jahr else "")


def _zeile(a: dict) -> str:
    """CB-123 · hoch · fällig 16.10. (überfällig) · Mats · Titel — fehlende Felder fallen weg."""
    teile = [a.get("id") or f"CB-{a.get('nummer', '?')}"]
    if a.get("prioText"):
        teile.append(a["prioText"])
    if a.get("erledigtAm"):
        teile.append(f"erledigt {_tag(a['erledigtAm'])}")
    elif a.get("faellig"):
        teile.append(f"fällig {_tag(a['faellig'])}" + (" (überfällig)" if a.get("ueberfaellig") else ""))
    if a.get("fuer"):
        teile.append(a["fuer"])
    teile.append(a.get("titel") or "(ohne Titel)")
    return " · ".join(teile)


def _nr(wert: str) -> str:
    w = wert.strip()
    if not re.match(r"^(?:cb-)?\d+$", w, re.IGNORECASE):
        _falsch(f"„{wert}“ ist keine Aufgaben-Nummer (erwartet CB-123 oder 123).")
    return urllib.parse.quote(w.upper())


HILFE = "Aufgaben:"  # Abschnitt der Hilfe bei Bedienfehlern; die Ware-Befehle setzen "Ware:"


def _falsch(text: str) -> None:
    """Bedienfehler: Meldung plus Hilfe des Abschnitts (bis zur nächsten Leerzeile) auf stderr, Exit 2."""
    print(text, file=sys.stderr)
    start = __doc__.index(HILFE)
    ende = __doc__.find("\n\n", start)
    print("\n" + __doc__[start:ende if ende != -1 else None].rstrip(), file=sys.stderr)
    raise SystemExit(2)


def _wert(args: list[str], name: str) -> str | None:
    """Wie _pop_option, aber eine Option ohne Wert ist ein Fehler statt still verschluckt."""
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args) or args[i + 1].startswith("--"):
            _falsch(f"{name} braucht einen Wert.")
    return _pop_option(args, name)


def _schalter(args: list[str], name: str) -> bool:
    if name in args:
        args.remove(name)
        return True
    return False


def _zahl(wert: str | None, name: str, lo: int, hi: int) -> int | None:
    if wert is None:
        return None
    try:
        n = int(wert)
    except ValueError:
        n = None
    if n is None or not lo <= n <= hi:
        _falsch(f"{name} erwartet eine ganze Zahl von {lo} bis {hi}, nicht „{wert}“.")
    return n


def _datum(wert: str | None) -> str | None:
    if wert is None:
        return None
    try:
        datetime.strptime(wert, "%Y-%m-%d")
    except ValueError:
        _falsch(f"--faellig erwartet ein Datum als YYYY-MM-DD, nicht „{wert}“.")
    return wert


GRUND_MAX = 300  # wie im Tool (src/lib/aufgaben-api.ts, GRUND_MAX)


def _grund(wert: str | None) -> str | None:
    """Grund einer Friständerung wie im Tool normalisiert: Zeilenumbrüche zu Leerzeichen, außen getrimmt.
    Gezählt wird wie in JavaScript (UTF-16-Einheiten), damit lokal und im Tool dieselbe Grenze gilt."""
    if wert is None:
        return None
    g = re.sub(r"\s*[\r\n]+\s*", " ", wert).strip()
    if not g:
        _falsch("--grund ist leer.")
    if len(g.encode("utf-16-le")) // 2 > GRUND_MAX:
        _falsch(f"--grund darf höchstens {GRUND_MAX} Zeichen lang sein.")
    return g


GRUND_FEHLT = "Bitte kurz begründen, warum die Frist sich ändert."  # Text des Tools (400) ab 19.10.2026

GROESSEN = ("klein", "mittel", "gross")  # wie im Tool (src/lib/aufgaben-view.ts, GROESSEN)
GROESSE_TEXT = {"klein": "klein", "mittel": "mittel", "gross": "groß"}


def _groesse(wert: str | None) -> str | None:
    """--groesse prüfen: klein, mittel oder gross (groß geht auch). Sonst Bedienfehler, nichts wird gesendet."""
    if wert is None:
        return None
    g = wert.strip().lower().replace("ß", "ss")
    if g not in GROESSEN:
        _falsch(f"--groesse erwartet klein, mittel oder gross, nicht „{wert}“.")
    return g


def _rest_leer(args: list[str]) -> None:
    if args:
        _falsch(f"Unbekannt: {' '.join(args)}")


def cmd_aufgaben(args: list[str]) -> None:
    fuer = _wert(args, "--fuer")
    status = _wert(args, "--status")
    suche = _wert(args, "--suche")
    limit = _zahl(_wert(args, "--limit"), "--limit", 1, 200)
    _rest_leer(args)
    if status and status not in ("offen", "erledigt", "alle"):
        _falsch(f"--status erwartet offen, erledigt oder alle, nicht „{status}“.")
    q = {k: v for k, v in (("fuer", fuer), ("status", status), ("suche", suche), ("limit", limit)) if v is not None}
    res = call(AUFGABEN + ("?" + urllib.parse.urlencode(q) if q else ""), method="GET", plain_errors=True)
    liste = res.get("aufgaben") or []
    art = {"offen": "offenen ", "erledigt": "erledigten ", "alle": ""}[status or "offen"]
    wer = res.get("fuer") or fuer
    if not liste:
        text = f"Keine {art}Aufgaben"
        if fuer and fuer.lower() != "ich":
            text += " im Team" if (wer or "").lower() == "alle" else f" für {wer}"
        if suche:
            text += f" zu „{suche}“"
        print(text + ".")
        return
    kopf = {"offen": "Offene Aufgaben", "erledigt": "Erledigte Aufgaben", "alle": "Alle Aufgaben"}[status or "offen"]
    if (wer or "").lower() == "alle":
        kopf += " im Team"
    elif wer:
        kopf += f" für {wer}"
    print(f"{kopf} ({len(liste)}):")
    for a in liste:
        print(_zeile(a))
    if len(liste) >= (limit or 50):
        print("Möglicherweise mehr; mit --limit bis 200 erhöhen.")


def _ausfuehrlich(a: dict) -> None:
    print(f"{a.get('id') or 'CB-' + str(a.get('nummer', '?'))} · {a.get('titel') or '(ohne Titel)'}")
    if a.get("erledigtAm"):
        print(f"Status: erledigt am {_tag(a['erledigtAm'], jahr=True)}")
    else:
        print("Status: offen" + (" (überfällig)" if a.get("ueberfaellig") else ""))
    for label, wert in (
        ("Prio", a.get("prioText")),
        ("Für", a.get("fuer")),
        ("Fällig", _tag(a.get("faellig"), jahr=True)),
        ("Größe", GROESSE_TEXT.get(a.get("groesse") or "")),
        ("Angelegt von", a.get("angelegtVon")),
        ("Aktualisiert", _tag(a.get("aktualisiert"), jahr=True)),
        ("Link", a.get("link")),
    ):
        if wert:
            print(f"{label}: {wert}")
    if (a.get("beschreibung") or "").strip():
        print("\nBeschreibung:\n" + a["beschreibung"].strip())


def cmd_aufgabe(args: list[str]) -> None:
    if len(args) != 1:
        _falsch("aufgabe braucht genau eine Nummer, z. B. CB-123.")
    res = call(f"{AUFGABEN}/{_nr(args[0])}", method="GET", plain_errors=True)
    _ausfuehrlich(res.get("aufgabe") or {})


def cmd_aufgabe_neu(args: list[str]) -> None:
    body = {
        "titel": _wert(args, "--titel"),
        "beschreibung": _wert(args, "--beschreibung"),
        "fuer": _wert(args, "--fuer"),
        "faellig": _datum(_wert(args, "--faellig")),
        "prio": _zahl(_wert(args, "--prio"), "--prio", 1, 4),
        "groesse": _groesse(_wert(args, "--groesse")),
    }
    _rest_leer(args)
    if not (body["titel"] or "").strip():
        _falsch("aufgabe-neu braucht --titel.")
    res = call(AUFGABEN, {k: v for k, v in body.items() if v is not None}, plain_errors=True)
    a = res.get("aufgabe") or {}
    print("Angelegt: " + _zeile(a))
    if a.get("link"):
        print(a["link"])


def cmd_aufgabe_aendern(args: list[str]) -> None:
    erledigt, offen = _schalter(args, "--erledigt"), _schalter(args, "--offen")
    faellig_weg, fuer_weg = _schalter(args, "--faellig-weg"), _schalter(args, "--fuer-weg")
    notiz = _wert(args, "--notiz")
    faellig = _datum(_wert(args, "--faellig"))
    grund = _grund(_wert(args, "--grund"))
    prio = _zahl(_wert(args, "--prio"), "--prio", 1, 4)
    fuer = _wert(args, "--fuer")
    groesse = _groesse(_wert(args, "--groesse"))
    if len(args) != 1:
        _falsch("aufgabe-aendern braucht genau eine Nummer, z. B. CB-123." + (f" Unbekannt: {' '.join(args)}" if args else ""))
    nr = _nr(args[0])
    if erledigt and offen:
        _falsch("--erledigt und --offen schließen sich aus.")
    if faellig and faellig_weg:
        _falsch("--faellig und --faellig-weg schließen sich aus.")
    if grund is not None and not (faellig or faellig_weg):
        _falsch("--grund geht nur zusammen mit --faellig oder --faellig-weg.")
    if fuer and fuer_weg:
        _falsch("--fuer und --fuer-weg schließen sich aus.")
    body = {}
    if erledigt or offen:
        body["erledigt"] = erledigt
    if notiz is not None:
        if not notiz.strip():
            _falsch("--notiz ist leer.")
        body["notiz"] = notiz
    if faellig or faellig_weg:
        body["faellig"] = faellig
    # Nur mitschicken, wenn gesetzt: das Tool vor dem 19.10.2026 lehnt unbekannte Felder mit 400 ab.
    if grund is not None:
        body["grund"] = grund
    if prio is not None:
        body["prio"] = prio
    if fuer or fuer_weg:
        body["fuer"] = fuer
    if groesse is not None:
        body["groesse"] = groesse
    if not body:
        _falsch("Nichts zu ändern.")
    try:
        res = call(f"{AUFGABEN}/{nr}", body, method="PATCH", plain_errors=True)
    except SystemExit as e:
        if GRUND_FEHLT in str(e.code):
            raise SystemExit(f"Nicht geändert: {GRUND_FEHLT}\n{nr} hat schon eine Frist. "
                             f"Die Person nach einem Satz Grund fragen und erneut mit --grund \"<grund>\" aufrufen.")
        raise
    a = res.get("aufgabe") or {}
    texte = {
        "erledigt": "erledigt" if a.get("erledigtAm") else "wieder offen",
        "notiz": "Notiz angehängt",
        "faellig": f"fällig {_tag(a.get('faellig'))}" if a.get("faellig") else "Fälligkeit entfernt",
        "prio": f"Prio {a.get('prioText') or a.get('prio')}",
        "fuer": f"für {a['fuer']}" if a.get("fuer") else "ohne Person",
        "groesse": f"Größe {GROESSE_TEXT.get(a.get('groesse') or '', 'ohne')}",
    }
    geaendert = res.get("geaendert") or []
    print("Geändert: " + (", ".join(texte.get(g, g) for g in geaendert) or "nichts") + ".")
    print(_zeile(a))


def cmd_erledigt(args: list[str]) -> None:
    """Erledigte Arbeit für sich selbst eintragen (Punkte als Produktivitätsscore, 20.10.2026): POST mit
    erledigt: true, ohne Person und ohne Frist; das Tool trägt sie auf das Konto des Schlüssels ein (für andere 403)."""
    titel = _wert(args, "--titel")
    groesse = _groesse(_wert(args, "--groesse"))
    notiz = _wert(args, "--notiz")
    _rest_leer(args)
    if not (titel or "").strip():
        _falsch("erledigt braucht --titel.")
    if groesse is None:
        _falsch("erledigt braucht --groesse klein, mittel oder gross.")
    body = {"titel": titel.strip(), "groesse": groesse, "erledigt": True}
    if notiz is not None:
        if not notiz.strip():
            _falsch("--notiz ist leer.")
        body["beschreibung"] = notiz.strip()
    res = call(AUFGABEN, body, plain_errors=True)
    a = res.get("aufgabe") or {}
    print(f"Eingetragen ({GROESSE_TEXT[groesse]}): " + _zeile(a))
    if a.get("link"):
        print(a["link"])


# ---------------------------------------------------------------- Ware: Lesezugang Supply Chain + Absatz (14.10.2026)
# Nur lesen. Nummern, SKUs und Amazon-Shipment-IDs kommen unverändert aus der Antwort des Tools.

LESEN = "/api/brain-read"
TIMEOUT_LESEN = 30.0  # Bestand und Absatz laden seitenweise; 8 s reichen dafür nicht sicher
WENIGE = 3  # bis zu so vielen Treffern zeigt eine Liste Einzelheiten und Link


def _n(x) -> str:
    """1234 → 1.234; None → –."""
    if x is None:
        return "–"
    if isinstance(x, float) and not x.is_integer():
        return _dez(x)
    return f"{int(x):,}".replace(",", ".")


def _dez(x: float, stellen: int = 2) -> str:
    """88987.06 → 88.987,06"""
    return f"{x:,.{stellen}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _eur(x) -> str:
    return "–" if x is None else _dez(float(x)) + " €"


def _heute_jahr() -> int:
    return (datetime.now(BERLIN) if BERLIN else datetime.now()).year


def _datum_text(wert: str | None, voll: bool = False) -> str | None:
    """`2026-10-28` → `28.10.` (dieses Jahr) bzw. `23.02.2027`; mit voll immer mit Jahr."""
    t = _tag(wert, jahr=True)
    if not t or not re.match(r"^\d{2}\.\d{2}\.\d{4}$", t):
        return t
    return t if voll or int(t[-4:]) != _heute_jahr() else t[:6]


def _zeitpunkt(wert: str | None) -> str | None:
    """ISO-Zeitpunkt → `14.10.2026 07:30` (Europe/Berlin); reiner Tag → `14.10.2026`."""
    if not wert:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?$", wert.strip())
    if not m:
        return _datum_text(wert, voll=True)
    tz = m.group(7) or "Z"
    off = 0 if tz == "Z" else (1 if tz[0] == "+" else -1) * (int(tz[1:3]) * 60 + int(tz[-2:]))
    try:
        t = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6) or 0), tzinfo=timezone(timedelta(minutes=off)))
    except ValueError:
        return wert
    if BERLIN:
        t = t.astimezone(BERLIN)
    return t.strftime("%d.%m.%Y %H:%M")


STAND_TEXT = {
    "amazonBestandTag": ("Amazon-Bestand vom", _datum_text),
    "amazonBisTag": ("Amazon-Verkäufe bis", _datum_text),
    "amazonSync": ("Amazon-Abgleich", _zeitpunkt),
    "shopsBisTag": ("Shops bis", _datum_text),
    "letzterLauf": ("letzter Planungslauf", _zeitpunkt),
    "lager": ("Lager", str),
}


def _stand(res: dict) -> None:
    """Immer ausgeben: wann abgerufen und wie aktuell die Quellen sind."""
    st = res.get("stand") or {}
    teile = [f"abgerufen {_zeitpunkt(st.get('abgerufen')) or '?'}"]
    if st.get("daten"):
        teile.append(f"Daten {st['daten']}")
    for k, v in st.items():
        if k in ("abgerufen", "daten"):
            continue
        label, fmt = STAND_TEXT.get(k, (k, str))
        teile.append(f"{label} {fmt(v) if v else 'unbekannt'}")
    print("Stand: " + ", ".join(teile))


def _kopf(titel: str, res: dict, liste: list) -> None:
    anzahl = res.get("anzahl", len(liste))
    print(f"{titel} ({anzahl}" + (f", gezeigt {len(liste)}" if res.get("gekuerzt") else "") + "):")


def _gekuerzt(res: dict, liste: list) -> None:
    if res.get("gekuerzt"):
        print(f"Gekürzt: {len(liste)} von {res.get('anzahl')} gezeigt; mit --suche eingrenzen oder --limit bis 200 erhöhen.")


def _ware_get(pfad: str, q: dict | None = None) -> dict:
    q = {k: v for k, v in (q or {}).items() if v is not None}
    return call(LESEN + pfad + ("?" + urllib.parse.urlencode(q) if q else ""), method="GET", timeout=TIMEOUT_LESEN, plain_errors=True)


def _wahl(wert: str | None, name: str, erlaubt: tuple) -> str | None:
    """Fester Wertebereich, Groß/klein egal; Rückgabe in der Schreibweise der Liste."""
    if wert is None:
        return None
    for e in erlaubt:
        if e.lower() == wert.strip().lower():
            return e
    _falsch(f"{name} erwartet {', '.join(erlaubt[:-1])} oder {erlaubt[-1]}, nicht „{wert}“.")


def _tag_param(wert: str | None, name: str) -> str | None:
    if wert is None:
        return None
    try:
        datetime.strptime(wert, "%Y-%m-%d")
    except ValueError:
        _falsch(f"{name} erwartet ein Datum als YYYY-MM-DD, nicht „{wert}“.")
    return wert


def _ref(args: list[str], was: str, beispiel: str) -> str:
    if len(args) != 1:
        _falsch(f"{was} braucht genau eine Nummer, z. B. {beispiel}." + (f" Unbekannt: {' '.join(args[1:])}" if len(args) > 1 else ""))
    nr = args[0].strip()
    if not re.match(r"^[A-Za-z0-9._-]+$", nr):
        _falsch(f"„{args[0]}“ ist keine gültige Nummer (erlaubt Buchstaben, Ziffern, Punkt, Binde- und Unterstrich).")
    return urllib.parse.quote(nr)


def _gruppen(liste: list, zeile) -> None:
    """Eine Zeile je Objekt, mit Zwischenkopf, wenn die Gruppe des Tools wechselt."""
    gruppe = object()
    for x in liste:
        if x.get("gruppe") != gruppe:
            gruppe = x.get("gruppe")
            if gruppe:
                print(f"{gruppe}:")
        print("  " + zeile(x))


def _felder(paare) -> None:
    for label, wert in paare:
        if wert not in (None, "", []):
            print(f"{label}: {wert}")


# ---- Bestellungen

def _po_zeile(b: dict) -> str:
    teile = [b.get("po") or "?", b.get("status") or "?"]
    produkt = b.get("produkt") or ""
    if b.get("weitereProdukte"):
        produkt += f" (+{b['weitereProdukte']} weitere)"
    teile.append(produkt)
    weg = " › ".join(x for x in (b.get("lieferant"), b.get("veredler"), b.get("ziel")) if x)
    if weg:
        teile.append(weg)
    m = b.get("menge") or {}
    if b.get("eingegangenAm") and not m.get("offen"):
        teile.append(f"eingegangen {_datum_text(b['eingegangenAm'])}")
    else:
        eta = b.get("etaBestaetigt") or b.get("etaZugesagt")
        teile.append(f"ETA {_datum_text(eta)}" + (" (bestätigt)" if b.get("etaBestaetigt") else " (zugesagt)") if eta else "ohne ETA")
        if b.get("eingegangenAm"):  # Teillieferung: Rest offen
            teile.append(f"eingegangen am {_datum_text(b['eingegangenAm'])}")
    teile.append(f"offen {_n(m.get('offen'))} von {_n(m.get('gesamt'))} St.")
    if b.get("naechsterSchritt"):
        teile.append(f"nächster Schritt: {b['naechsterSchritt']}")
    return " · ".join(teile)


def _po_einzeln(b: dict) -> None:
    m = b.get("menge") or {}
    _felder((
        ("Produkte", ", ".join(b.get("skus") or [])),
        ("Lieferant", b.get("lieferant")),
        ("Veredler", b.get("veredler")),
        ("Ziel", (b.get("ziel") or "?") + (f" ({b['marktplatz']})" if b.get("marktplatz") else "")),
        ("Gruppe", b.get("gruppe")),
        ("Bestellt am", _datum_text(b.get("bestelltAm"), voll=True)),
        ("ETA zugesagt", _datum_text(b.get("etaZugesagt"), voll=True)),
        ("ETA bestätigt", _datum_text(b.get("etaBestaetigt"), voll=True)),
        ("Eingegangen am", _datum_text(b.get("eingegangenAm"), voll=True)),
        ("Menge", f"{_n(m.get('gesamt'))} gesamt, {_n(m.get('eingegangen'))} eingegangen, {_n(m.get('offen'))} offen"),
        ("Nächster Schritt", b.get("naechsterSchritt")),
        ("AB-Nummer", b.get("abNummer")),
        ("Teil von", b.get("teilVon")),
        ("Link", b.get("link")),
    ))


def cmd_bestellungen(args: list[str]) -> None:
    status = _wahl(_wert(args, "--status"), "--status", ("offen", "alle"))
    suche = _wert(args, "--suche")
    limit = _zahl(_wert(args, "--limit"), "--limit", 1, 200)
    _rest_leer(args)
    res = _ware_get("/bestellungen", {"status": status, "suche": suche, "limit": limit})
    liste = res.get("bestellungen") or []
    art = "Offene Bestellungen" if (status or "offen") == "offen" else "Bestellungen"
    if not liste:
        print(f"Keine {'offenen ' if status != 'alle' else ''}Bestellungen" + (f" zu „{suche}“" if suche else "") + ".")
    else:
        _kopf(art + (f" zu „{suche}“" if suche else ""), res, liste)
        _gruppen(liste, _po_zeile)
        if len(liste) <= WENIGE:
            for b in liste:
                print(f"  Link {b.get('po')}: {b.get('link')}")
        _gekuerzt(res, liste)
    _stand(res)


def cmd_bestellung(args: list[str]) -> None:
    res = _ware_get("/bestellungen/" + _ref(args, "bestellung", "PO-049"))
    b = res.get("bestellung") or {}
    print(f"{b.get('po')} · {b.get('status')} · {b.get('produkt')}")
    _po_einzeln(b)
    if b.get("positionen"):
        print("Positionen:")
        for p in b["positionen"]:
            kartons = f" · {_n(p['kartons'])} Kartons" if p.get("kartons") is not None else ""
            print(f"  {p.get('sku')} · {p.get('produkt')} · bestellt {_n(p.get('bestellt'))} · eingegangen {_n(p.get('eingegangen'))} · offen {_n(p.get('offen'))}{kartons}")
    if b.get("meilensteine"):
        print("Meilensteine:")
        for x in b["meilensteine"]:
            print(f"  [{'x' if x.get('erledigt') else ' '}] {x.get('schritt')}: {x.get('text')}")
    if b.get("stationen"):
        print("Stationen: " + " › ".join(f"{s.get('name')}" + (f" ({s['rolle']})" if s.get("rolle") else "") for s in b["stationen"]))
    if b.get("etaAenderungen"):
        print("ETA-Änderungen:")
        for c in b["etaAenderungen"]:
            print(f"  {_zeitpunkt(c.get('am'))}: {_datum_text(c.get('alt'), voll=True) or '–'} › {_datum_text(c.get('neu'), voll=True) or '–'}" + (f" ({c['von']})" if c.get("von") else ""))
    else:
        print("ETA-Änderungen: keine")
    _stand(res)


# ---- Sendungen

def _sendung_zeile(s: dict) -> str:
    teile = [s.get("nr") or "?", s.get("amazonId") or "ohne Amazon-ID", s.get("status") or "?"]
    if s.get("von"):
        teile.append(f"von {s['von']}")
    teile.append(f"ETA {_datum_text(s['eta'])}" if s.get("eta") else "ohne ETA")
    menge = f"{_n(s.get('stueck'))} St."
    if s.get("kartons") is not None:
        menge += f", {_n(s['kartons'])} Kartons"
    teile.append(menge)
    produkt = s.get("produkt") or ""
    weitere = len(s.get("positionen") or []) - 1
    if weitere > 0:
        produkt += f" (+{weitere} weitere)"
    teile.append(produkt)
    return " · ".join(teile)


def cmd_sendungen(args: list[str]) -> None:
    status = _wahl(_wert(args, "--status"), "--status", ("offen", "alle"))
    suche = _wert(args, "--suche")
    limit = _zahl(_wert(args, "--limit"), "--limit", 1, 200)
    _rest_leer(args)
    res = _ware_get("/sendungen", {"status": status, "suche": suche, "limit": limit})
    liste = res.get("sendungen") or []
    art = "Offene Sendungen" if (status or "offen") == "offen" else "Sendungen"
    if not liste:
        print(f"Keine {'offenen ' if status != 'alle' else ''}Sendungen" + (f" zu „{suche}“" if suche else "") + ".")
    else:
        _kopf(art + (f" zu „{suche}“" if suche else ""), res, liste)
        _gruppen(liste, _sendung_zeile)
        if len(liste) <= WENIGE:
            for s in liste:
                print(f"  Link {s.get('nr')}: {s.get('link')}")
        _gekuerzt(res, liste)
    _stand(res)


def cmd_sendung(args: list[str]) -> None:
    res = _ware_get("/sendungen/" + _ref(args, "sendung", "IN-2026-0039 oder FBA15MM4GTB5"))
    s = res.get("sendung") or {}
    print(f"{s.get('nr')} · {s.get('status')}")
    _felder((
        ("Amazon-Shipment-ID", s.get("amazonId") or "noch keine"),
        ("Gruppe", s.get("gruppe")),
        ("Von", s.get("von")),
        ("ETA", _datum_text(s.get("eta"), voll=True)),
        ("Angelegt am", _datum_text(s.get("angelegtAm"), voll=True)),
        ("Stück", _n(s.get("stueck"))),
        ("Kartons", _n(s["kartons"]) if s.get("kartons") is not None else "keine Angabe"),
        ("Link", s.get("link")),
    ))
    if s.get("positionen"):
        print("Positionen:")
        for p in s["positionen"]:
            kartons = f" · {_n(p['kartons'])} Kartons" if p.get("kartons") is not None else ""
            print(f"  {p.get('sku')} · {p.get('produkt')} · {_n(p.get('stueck'))} St.{kartons}")
    _stand(res)


# ---- Bestand

def _bestand_zeile(b: dict) -> str:
    teile = [b.get("sku") or "?", b.get("name") or "", b.get("marktplatz") or ""]
    f = b.get("fba")
    if f:
        zulauf = (f.get("zulaufWorking") or 0) + (f.get("zulaufShipped") or 0) + (f.get("zulaufReceiving") or 0)
        teile.append(f"FBA {_n(f.get('verfuegbar'))} verfügbar, {_n(f.get('reserviert'))} reserviert, Amazon-Zulauf {_n(zulauf)} (vom {_datum_text(f.get('datum'))})")
    else:
        teile.append("FBA unbekannt")
    if b.get("lagerGesamt") is None:
        teile.append("Lager unbekannt")
    else:
        orte = ", ".join(f"{l.get('standort')} {_n(l.get('stueck'))}" for l in b.get("lager") or [])
        teile.append(f"Lager {_n(b['lagerGesamt'])}" + (f" ({orte})" if orte else ""))
    if b.get("beimHersteller"):
        teile.append(f"beim Hersteller {_n(b['beimHersteller'])}")
    teile.append(f"unterwegs {_n((b.get('unterwegs') or {}).get('stueck'))}")
    return " · ".join(t for t in teile if t)


def _bestand_einzeln(b: dict) -> None:
    f = b.get("fba")
    if f:
        print(f"    Amazon-Zulauf: working {_n(f.get('zulaufWorking'))}, shipped {_n(f.get('zulaufShipped'))}, receiving {_n(f.get('zulaufReceiving'))}")
    elif b.get("fbaHinweis"):
        print(f"    FBA: {b['fbaHinweis']}")
    for a in (b.get("unterwegs") or {}).get("anlieferungen") or []:
        spaet = f" (+{a['ueberfaelligTage']} T überfällig)" if a.get("ueberfaelligTage") else ""
        print(f"    unterwegs: {a.get('ref')} · {a.get('art')} · {_n(a.get('stueck'))} St. · ETA {_datum_text(a.get('eta')) or '–'}{spaet}")
    print(f"    Link: {b.get('link')}")


def cmd_bestand(args: list[str]) -> None:
    suche = _wert(args, "--suche")
    # Ohne Suche sind es über 50 Produkte; die Voreinstellung des Tools (50) schnitte sonst ab.
    limit = _zahl(_wert(args, "--limit"), "--limit", 1, 200) or 200
    _rest_leer(args)
    res = _ware_get("/bestand", {"suche": suche, "limit": limit})
    liste = res.get("bestand") or []
    if not liste:
        print("Kein Bestand" + (f" zu „{suche}“" if suche else "") + ".")
    else:
        _kopf("Bestand" + (f" zu „{suche}“" if suche else ""), res, liste)
        for b in liste:
            print("  " + _bestand_zeile(b))
            if len(liste) <= WENIGE:
                _bestand_einzeln(b)
        _gekuerzt(res, liste)
        hinweise = sorted({b.get("hinweis") for b in liste if b.get("hinweis")})
        for h in hinweise:
            print(f"Hinweis: {h}")
    _stand(res)


# ---- Bestellplanung

PLAN_STATUS = ("faellig", "ueberfaellig", "alle", "vorschlag", "angepasst", "bestaetigt")


def _plan_zeile(z: dict) -> str:
    teile = [z.get("sku") or "?", z.get("produkt") or ""]
    if z.get("lieferant"):
        teile.append(z["lieferant"])
    teile.append(z.get("marktplatz") or "")
    teile.append(f"bestellen bis {_datum_text(z.get('bestellenBis'))}" + (" (überfällig)" if z.get("ueberfaellig") else ""))
    teile.append(f"Ankunft {_datum_text(z.get('ankunft'))}")
    teile.append(f"{_n(z.get('menge'))} St.")
    teile.append(z.get("status") or "")
    weitere = len(z.get("bestellungen") or []) - 1
    if weitere > 0:
        teile.append(f"+{weitere} weitere geplant")
    return " · ".join(t for t in teile if t)


def cmd_bestellplanung(args: list[str]) -> None:
    status = _wahl(_wert(args, "--status"), "--status", PLAN_STATUS)
    suche = _wert(args, "--suche")
    markt = _wahl(_wert(args, "--marktplatz"), "--marktplatz", ("DE", "US", "alle"))
    limit = _zahl(_wert(args, "--limit"), "--limit", 1, 200)
    _rest_leer(args)
    res = _ware_get("/bestellplanung", {"status": status, "suche": suche, "marktplatz": markt, "limit": limit})
    liste = res.get("bestellplanung") or []
    rahmen = f"Marktplatz {res.get('marktplatz') or markt or 'alle'}" + (f", Status {status}" if status else "") + (f", zu „{suche}“" if suche else "")
    if not liste:
        print(f"Keine geplanten Bestellungen ({rahmen}).")
    else:
        _kopf(f"Bestellplanung, {rahmen}", res, liste)
        for z in liste:
            print("  " + _plan_zeile(z))
            if len(liste) <= WENIGE:
                for o in (z.get("bestellungen") or [])[1:]:
                    print(f"    danach: bestellen bis {_datum_text(o.get('bestellenBis'))} · Ankunft {_datum_text(o.get('ankunft'))} · {_n(o.get('menge'))} St. · {o.get('status')}")
        _gekuerzt(res, liste)
        print(f"Link: {liste[0].get('link')}")
    _stand(res)


# ---- Absatz

def _conv(z: dict) -> str:
    """Conversion wie das Tool; markiert, wenn Tage ohne Sitzungen mitzählen (Historie vor 11.07.2026)."""
    if z.get("conversionPct") is None:
        return "Conversion –"
    text = f"Conversion {_dez(z['conversionPct'])} %"
    if (z.get("sitzungsTage") or 0) < (z.get("datentage") or 0):
        text += f" (zu hoch: nur {_n(z.get('sitzungsTage'))} von {_n(z.get('datentage'))} Tagen mit Sitzungen)"
    return text


def _umsatz(z: dict) -> str:
    if z.get("umsatz") is None:
        return "Umsatz unbekannt"
    text = _eur(z["umsatz"])
    if (z.get("umsatzTage") or 0) < (z.get("datentage") or 0):
        text += f" (nur {_n(z.get('umsatzTage'))} von {_n(z.get('datentage'))} Tagen mit Umsatz)"
    return text


def _periode(p: str | None) -> str:
    return _datum_text(p) if p and re.match(r"^\d{4}-\d{2}-\d{2}$", p) else (p or "?")


def _amazon_zahlen(z: dict) -> str:
    return " · ".join((f"{_n(z.get('stueck'))} St.", _umsatz(z), f"{_n(z.get('sitzungen'))} Sitzungen", _conv(z)))


def cmd_absatz(args: list[str]) -> None:
    suche = _wert(args, "--suche")
    von = _tag_param(_wert(args, "--von"), "--von")
    bis = _tag_param(_wert(args, "--bis"), "--bis")
    kanal = _wahl(_wert(args, "--kanal"), "--kanal", ("amazon", "shop", "alle"))
    je = _wahl(_wert(args, "--je"), "--je", ("produkt", "tag", "woche"))
    _rest_leer(args)
    res = _ware_get("/absatz", {"suche": suche, "von": von, "bis": bis, "kanal": kanal, "je": je})
    zr = res.get("zeitraum") or {}
    print(f"Absatz {_datum_text(zr.get('von'), voll=True)} bis {_datum_text(zr.get('bis'), voll=True)}, je {res.get('je')}, Kanal {res.get('kanal')}" + (f", zu „{suche}“" if suche else "") + ":")
    zu_hoch = False
    a = res.get("amazon")
    if a is not None:
        zeilen = a.get("zeilen") or []
        g = a.get("gesamt") or {}
        print(f"Amazon gesamt ({_n(a.get('skus'))} SKU{'' if a.get('skus') == 1 else 's'}): {_amazon_zahlen(g)}")
        zu_hoch = (g.get("sitzungsTage") or 0) < (g.get("datentage") or 0)
        for z in zeilen:
            kopf = f"{z.get('sku')} · {z.get('produkt')}" if z.get("sku") else _periode(z.get("periode"))
            print(f"  {kopf} · {_amazon_zahlen(z)}")
            if z.get("link") and len(zeilen) <= WENIGE:
                print(f"    Link: {z['link']}")
        if not zeilen:
            print("  keine Amazon-Verkäufe im Zeitraum")
    sh = res.get("shops")
    if sh is not None:
        shops = sh.get("shops") or []
        produkte = sh.get("produkte") or []
        if suche:
            # Die Summen je Shop filtert das Tool nicht nach der Suche; die Produktzeilen schon (gleiche Regel wie
            # hier: SKU oder Name enthält den Text). Hier noch einmal gefiltert, damit nie eine fremde Zeile durchrutscht.
            s_klein = suche.strip().lower()
            produkte = [p for p in produkte if s_klein in (p.get("sku") or "").lower() or s_klein in (p.get("produkt") or "").lower()]
        if produkte:
            print("Shops je Produkt:")
            for p in produkte:
                teile = [p.get("shop") or "?"]
                if p.get("periode"):
                    teile.append(_periode(p["periode"]))
                teile += [p.get("sku") or "ohne SKU", p.get("produkt") or "", f"{_n(p.get('stueck'))} St.", f"{_n(p.get('bestellungen'))} Bestellungen"]
                if p.get("positionenOhneStueck"):
                    teile.append(f"{_n(p['positionenOhneStueck'])} Positionen ohne Stückzahl")
                print("  " + " · ".join(t for t in teile if t))
        elif suche:
            print(f"Shops: kein Verkauf zu „{suche}“.")
        if suche:
            kopf = "Shops gesamt (nicht nach Suche gefiltert):"
        else:
            kopf = "Shops:" if shops else "Shops: keine"
        if shops or not suche:
            print(kopf)
        for s in shops:
            teile = [s.get("shop") or "?"]
            if s.get("periode"):
                teile.append(_periode(s["periode"]))
            teile += [f"{_n(s.get('bestellungen'))} Bestellungen", f"Netto {_eur(s.get('umsatzNetto'))}"]
            if s.get("bestellungenOhneNetto"):
                teile.append(f"{_n(s['bestellungenOhneNetto'])} Bestellungen ohne Netto")
            print("  " + " · ".join(teile) + (f" · {s['link']}" if s.get("link") and len(shops) <= WENIGE else ""))
        if sh.get("hinweis"):
            print(f"Hinweis Shops: {sh['hinweis']}")
    if zu_hoch:
        print("Hinweis Conversion: Für Tage vor dem 11.07.2026 (alte Flieber-Historie) fehlen die Sitzungen. Werte mit „zu hoch“ "
              "zählen Stück ohne Sitzungen mit und können über 100 % liegen; nicht als echte Conversion lesen.")
    _stand(res)


WARE = {
    "bestellungen": cmd_bestellungen,
    "bestellung": cmd_bestellung,
    "sendungen": cmd_sendungen,
    "sendung": cmd_sendung,
    "bestand": cmd_bestand,
    "bestellplanung": cmd_bestellplanung,
    "absatz": cmd_absatz,
}


# ---------------------------------------------------------------- Kasse: Bruno-Kaffeekasse (Vertrag vertrag-kasse.md, 16.10.2026)
# Das Skript rechnet nichts: Beträge, Fälligkeit, Zinsen und wer was darf entscheidet das Tool (kasse-core.ts).
# Es liest keine Bilder und nimmt keine Dateien: Claude liest den Screenshot und übergibt nur Betrag, Datum, Empfänger.

KASSE = "/api/brain-read/kasse"
KASSE_FEHLT = "Die Kasse ist im Tool noch nicht da."
KASSE_MAX_CENT = 100_000  # wie im Tool (kasse-core.ts, MAX_CENT)
KASSE_EMPFAENGER_MAX = 80
KASSE_GRUND_MAX = 300
KASSE_NAME_MAX = 80
WOCHENTAG = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
AMPEL_TEXT = {"gruen": "grün", "gelb": "gelb", "rot": "rot"}


def _cent(wert: str | None) -> int:
    """„6,60“, „6.60“, „6,6“, „6“, „6,60 €“ → 660. Alles andere ist ein Bedienfehler vor jedem Netzaufruf."""
    if wert is None:
        _falsch("kasse-melden braucht --betrag, z. B. --betrag 6,60.")
    w = re.sub(r"\s+", "", wert).replace("€", "").replace("EUR", "")
    m = re.match(r"^(\d{1,6})(?:[,.](\d{1,2}))?$", w)
    if not m:
        _falsch(f"--betrag erwartet Euro wie 6,60, nicht „{wert}“.")
    cent = int(m.group(1)) * 100 + int((m.group(2) or "0").ljust(2, "0"))
    if not 1 <= cent <= KASSE_MAX_CENT:
        _falsch(f"--betrag muss zwischen 0,01 € und {KASSE_MAX_CENT // 100} € liegen, nicht „{wert}“.")
    return cent


def _kasse_text(wert: str | None, name: str, hoechstens: int, pflicht: bool = True) -> str | None:
    """Wie im Tool normalisiert (Leerraum zu einem Leerzeichen, außen getrimmt), gezählt in UTF-16-Einheiten wie JavaScript."""
    if wert is None:
        if pflicht:
            _falsch(f"{name} fehlt.")
        return None
    t = re.sub(r"\s+", " ", wert).strip()
    if not t:
        _falsch(f"{name} ist leer.")
    if len(t.encode("utf-16-le")) // 2 > hoechstens:
        _falsch(f"{name} darf höchstens {hoechstens} Zeichen lang sein.")
    return t


def _kasse_tag(wert: str | None, name: str, pflicht: bool = True) -> str | None:
    if wert is None:
        if pflicht:
            _falsch(f"{name} fehlt (YYYY-MM-DD).")
        return None
    return _tag_param(wert, name)


def _ct(c) -> str:
    """660 → „6,60 €“, 123456 → „1.234,56 €“ (ganze Cent, kein Gleitkomma)."""
    c = int(c or 0)
    vz, c = ("-" if c < 0 else ""), abs(c)
    return vz + f"{c // 100:,}".replace(",", ".") + f",{c % 100:02d} €"


def _wann(wert: str | None) -> str:
    """ISO-Zeitpunkt → „Di 20.10. 12:00“ (Europe/Berlin)."""
    if not wert:
        return "?"
    try:
        t = datetime.fromisoformat(wert.strip().replace("Z", "+00:00"))
    except ValueError:
        return wert
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    if BERLIN:
        t = t.astimezone(BERLIN)
    return f"{WOCHENTAG[t.weekday()]} {t:%d.%m.} {t:%H:%M}"


def _wtag(tag: str | None) -> str:
    """„2026-10-19“ → „Mo 19.10.“"""
    try:
        d = datetime.strptime(tag or "", "%Y-%m-%d")
    except ValueError:
        return tag or "?"
    return f"{WOCHENTAG[d.weekday()]} {d:%d.%m.}"


def _offen(stand: dict) -> int:
    """Was eine Meldung decken müsste: fällig (mit Zinsen) plus bald fällig. Dieselbe Zahl, gegen die das Tool die Abweichung misst."""
    return int(stand.get("faelligCent") or 0) + int(stand.get("baldCent") or 0)


def _posten_zeile(p: dict) -> str:
    n = len(p.get("aufgaben") or [])
    zins = int(p.get("wertCent") or 0) - int(p.get("sollCent") or 0)
    teile = [_wtag(p.get("tag")), f"{n} Aufgabe{'' if n == 1 else 'n'} × {p.get('satz')} € = {_ct(p.get('sollCent'))}" + (f" + {_ct(zins)} Zinsen" if zins > 0 else "")]
    status = p.get("status")
    if status == "erlassen":
        e = p.get("erlass") or {}
        teile.append("erlassen" + (f" („{e['grund']}“)" if e.get("grund") else ""))
    elif status == "bald":
        teile.append(f"fällig {_wann(p.get('faelligAb'))}")
    elif status == "faellig":
        teile.append(f"offen {_ct(p.get('restCent'))}, fällig seit {_wann(p.get('faelligAb'))}")
    elif status == "gemeldet":
        teile.append("gemeldet" + (f", offen {_ct(p.get('restCent'))}" if p.get("restCent") else ""))
    else:
        teile.append(status or "?")
    if p.get("vorlaeufig"):
        teile.append("vorläufig")
    return " · ".join(teile)


def _meldung_zeile(m: dict, mit_name: bool = False) -> str:
    teile = [f"Nr. {m.get('nr')}"]
    if mit_name:
        # Der Name kommt nur, wenn das Tool ihn mitliefert; sonst das Kürzel des Kontos (nie raten).
        teile.append(m.get("name") or m.get("zahlerName") or f"Konto {str(m.get('zahler') or '?')[:8]}")
    teile += [_ct(m.get("cent")), m.get("beleg") or "?"]
    status = m.get("status")
    if status == "offen":
        teile.append(f"offen, ohne Widerspruch bestätigt ab {_wann(m.get('bestaetigtAb'))}")
    elif status == "widersprochen":
        w = m.get("widerspruch") or {}
        teile.append("widersprochen" + (f": {w['grund']}" if w.get("grund") else ""))
    else:
        teile.append(status or "?")
    if mit_name and m.get("offenVorherCent") is not None and m.get("offenVorherCent") != m.get("cent"):
        teile.append(f"offen waren {_ct(m['offenVorherCent'])}")
    return " · ".join(teile)


def _stand_kurz(s: dict) -> str:
    """Ein Satz nach einer Buchung: offen jetzt, Erinnerung an oder aus."""
    f = int(s.get("faelligCent") or 0)
    text = f"Offen jetzt: {_ct(_offen(s))}"
    if f:
        text += f", davon fällig {_ct(f)}; Erinnerung läuft weiter"
        if s.get("naechste"):
            text += f", {_wann(s['naechste'].get('at'))} werden es {_ct(s['naechste'].get('cent'))}"
    else:
        text += ". Nichts fällig, Erinnerungen aus"
    return text + "."


def _kasse_call(body: dict | None) -> dict:
    if body is None:
        return call(KASSE, method="GET", plain_errors=True, bei_404=KASSE_FEHLT)
    return call(KASSE, body, plain_errors=True, bei_404=KASSE_FEHLT)


def cmd_kasse(args: list[str]) -> None:
    _rest_leer(args)
    res = _kasse_call(None)
    s = res.get("stand") or {}
    jetzt = datetime.now(BERLIN) if BERLIN else datetime.now()
    print(f"Kasse {s.get('name') or '?'} · Stand {WOCHENTAG[jetzt.weekday()]} {jetzt:%d.%m. %H:%M}")
    f = int(s.get("faelligCent") or 0)
    if f:
        seit = sorted(p.get("faelligAb") for p in s.get("posten") or [] if p.get("status") == "faellig" and p.get("faelligAb"))
        zins = int(s.get("davonZinsenCent") or 0)
        print(f"Fällig: {_ct(f)}" + (f" seit {_wann(seit[0])}" if seit else "") + (f" (davon {_ct(zins)} Zinsen)" if zins else ""))
    else:
        print("Fällig: nichts")
    if s.get("baldCent"):
        print(f"Noch nicht fällig: {_ct(s['baldCent'])} (je Tag erst bei seiner 12:00, ohne Zinsen)")
    print(f"Offen gesamt (fällig + bald): {_ct(_offen(s))}")
    h = s.get("heute")
    if h is None:
        print("Heute: Wochenende, zählt nicht")
    elif not h.get("cent"):
        print("Heute: 0,00 €")
    else:
        n = len(h.get("aufgaben") or [])
        print(f"Heute: {_ct(h['cent'])} ({n} Aufgabe{'' if n == 1 else 'n'} × {h.get('satz')} €, Ampel {AMPEL_TEXT.get(h.get('ampel'), h.get('ampel'))})")
    if s.get("naechste"):
        print(f"Ohne Meldung {_wann(s['naechste'].get('at'))}: {_ct(s['naechste'].get('cent'))}")
    if s.get("gemeldetCent"):
        print(f"Gemeldet, noch nicht bestätigt: {_ct(s['gemeldetCent'])}")
    if s.get("guthabenCent"):
        print(f"Guthaben: {_ct(s['guthabenCent'])} (wird auf die nächsten Tage angerechnet)")
    print(f"Seit Start insgesamt: {_ct(s.get('gesamtCent'))}")
    posten = [p for p in s.get("posten") or [] if p.get("sollCent") and p.get("status") != "bezahlt"]
    bezahlt = sum(1 for p in s.get("posten") or [] if p.get("sollCent") and p.get("status") == "bezahlt")
    if posten:
        print("Tage mit Betrag:")
        for p in posten:
            print("  " + _posten_zeile(p))
    if bezahlt:
        print(f"Bezahlt: {bezahlt} Tag{'' if bezahlt == 1 else 'e'}")
    meldungen = s.get("meldungen") or []
    if meldungen:
        zeigen = [m for m in meldungen if m.get("status") != "bestaetigt"] + [m for m in meldungen if m.get("status") == "bestaetigt"][-5:]
        print("Meldungen:")
        for m in sorted(zeigen, key=lambda x: x.get("nr") or 0):
            print("  " + _meldung_zeile(m))
    pruefen = res.get("zuPruefen") or []
    if pruefen:
        print("Zu prüfen (du bist Kassenwart; ohne Widerspruch gilt jede Meldung ab der genannten Zeit):")
        for m in pruefen:
            print("  " + _meldung_zeile(m, mit_name=True))


def cmd_kasse_melden(args: list[str]) -> None:
    cent = _cent(_wert(args, "--betrag"))
    datum = _kasse_tag(_wert(args, "--datum"), "--datum")
    empfaenger = _kasse_text(_wert(args, "--empfaenger"), "--empfaenger", KASSE_EMPFAENGER_MAX)
    fuer = _kasse_text(_wert(args, "--fuer"), "--fuer", KASSE_NAME_MAX, pflicht=False)
    _rest_leer(args)
    body = {"aktion": "melden", "cent": cent, "datum": datum, "empfaenger": empfaenger}
    if fuer is not None:  # nur gesetzte Felder: das Tool lehnt unbekannte und leere ab
        body["fuer"] = fuer
    res = _kasse_call(body)
    if res.get("schonGebucht"):
        print(f"Schon gemeldet (Nr. {res['schonGebucht']}), nichts doppelt gebucht. " + _stand_kurz(res.get("stand") or {}))
        return
    g = (res.get("gebucht") or [{}])[0]
    z = res.get("zahler") or res.get("stand") or {}
    m = next((x for x in z.get("meldungen") or [] if x.get("nr") == g.get("nr")), {})
    if g.get("von") and g.get("von") != g.get("zahler"):
        print(f"Für {z.get('name') or '?'} gemeldet (Nr. {g.get('nr')}): {_ct(g.get('cent'))}, sofort bestätigt (vom Kassenwart).")
    else:
        print(f"Gemeldet (Nr. {g.get('nr')}): {_ct(g.get('cent'))}, „{g.get('beleg') or '?'}“. "
              f"Der Kassenwart kann bis {_wann(m.get('bestaetigtAb'))} widersprechen, sonst gilt es.")
    ab = res.get("abweichungCent")  # gegen offen gesamt (fällig + noch nicht fällig), wie das Tool rechnet
    if ab and ab > 0:
        print(f"Abweichung: {_ct(ab)} mehr als offen war; das wird Guthaben für die nächsten Tage.")
    elif ab and z.get("faelligCent"):
        print(f"Abweichung: {_ct(z['faelligCent'])} vom Fälligen bleiben offen; Erinnerung und Zinsen laufen darauf weiter.")
    elif ab:
        print(f"Fälliges ist gedeckt; {_ct(-ab)} für noch nicht fällige Tage bleiben offen (je Tag ab seiner 12:00).")
    print(_stand_kurz(z))


def cmd_kasse_widersprechen(args: list[str]) -> None:
    nr = _zahl(_wert(args, "--meldung"), "--meldung", 1, 2_000_000_000)
    grund = _kasse_text(_wert(args, "--grund"), "--grund", KASSE_GRUND_MAX)
    _rest_leer(args)
    if nr is None:
        _falsch("kasse-widersprechen braucht --meldung <nr>.")
    res = _kasse_call({"aktion": "widersprechen", "meldung": nr, "grund": grund})
    z = res.get("zahler") or {}
    print(f"Widersprochen (Nr. {nr}), Grund „{grund}“. Steht im Verlauf.")
    print(f"{z.get('name') or 'Zahler'}: " + _stand_kurz(z))


def cmd_kasse_erlassen(args: list[str]) -> None:
    fuer = _kasse_text(_wert(args, "--fuer"), "--fuer", KASSE_NAME_MAX)
    tag = _kasse_tag(_wert(args, "--tag"), "--tag")
    bis = _kasse_tag(_wert(args, "--bis"), "--bis", pflicht=False)
    grund = _kasse_text(_wert(args, "--grund"), "--grund", KASSE_GRUND_MAX)
    _rest_leer(args)
    body = {"aktion": "erlassen", "fuer": fuer, "tag": tag, "grund": grund}
    if bis is not None:
        body["bis"] = bis
    res = _kasse_call(body)
    z = res.get("zahler") or {}
    soll = {p.get("tag"): p.get("sollCent") for p in z.get("posten") or []}
    tage = [b.get("tag") for b in res.get("gebucht") or [] if b.get("tag")]
    liste = ", ".join(f"{_wtag(t)} ({_ct(soll.get(t))})" for t in tage) or "?"
    print(f"Erlassen: {z.get('name') or fuer} {liste}, Grund „{grund}“. Steht im Verlauf.")
    print(_stand_kurz(z))


KASSE_BEFEHLE = {
    "kasse": cmd_kasse,
    "kasse-melden": cmd_kasse_melden,
    "kasse-widersprechen": cmd_kasse_widersprechen,
    "kasse-erlassen": cmd_kasse_erlassen,
}


def main(argv: list[str]) -> None:
    global HILFE
    if len(argv) < 2:
        print(__doc__)
        return
    cmd, args = argv[1], argv[2:]
    if cmd == "setup" and args:
        cmd_setup(args[0], args[1] if len(args) > 1 else None)
    elif cmd == "ping":
        cmd_ping()
    elif cmd == "search" and args:
        cmd_search(args[0], int(args[1]) if len(args) > 1 else 5)
    elif cmd == "drop" and args:
        via = _pop_option(args, "--via")
        text = " ".join(args).strip()
        if text.startswith("-") or text.lower() in {"help", "hilfe", "?"}:
            # 14.09.: „/drop --help“ landete wortwörtlich in der Inbox. Optionen und Hilfe-Wörter sind kein Wissen.
            print("Nicht eingeworfen: Das sieht nach einer Option oder Hilfe-Anfrage aus.\n" + __doc__)
            raise SystemExit(2)
        cmd_drop(text, via)
    elif cmd == "drop-file" and args:
        started = _pop_option(args, "--started")
        scanned = _pop_option(args, "--scanned")
        cmd_drop_files(args, float(started) if started else None, int(scanned) if scanned else None)
    elif cmd == "aufgaben":
        cmd_aufgaben(args)
    elif cmd == "aufgabe":
        cmd_aufgabe(args)
    elif cmd == "aufgabe-neu":
        cmd_aufgabe_neu(args)
    elif cmd == "aufgabe-aendern":
        cmd_aufgabe_aendern(args)
    elif cmd == "erledigt":
        cmd_erledigt(args)
    elif cmd in WARE:
        HILFE = "Ware:"
        WARE[cmd](args)
    elif cmd in KASSE_BEFEHLE:
        HILFE = "Kasse:"
        KASSE_BEFEHLE[cmd](args)
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main(sys.argv)
