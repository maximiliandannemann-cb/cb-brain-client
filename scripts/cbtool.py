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
          cbtool.py aufgabe-aendern CB-123 [--erledigt | --offen] [--notiz <text>] [--faellig YYYY-MM-DD | --faellig-weg]
                                            [--prio 1-4] [--fuer <name> | --fuer-weg]
          Prio: 1 niedrig, 2 mittel, 3 hoch, 4 dringend. Löschen geht nur im Tool.
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


def call(path: str, body=None, method: str = "POST", key: str | None = None, timeout: float = TIMEOUT, via: str = "skill", plain_errors: bool = False):
    # plain_errors: Fehlertext des Servers ohne „Tool antwortet …“ und mit der Liste gültiger Namen (Aufgaben-Befehle).
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
            # Der Server nennt bei einem Teilfehler die schon geschriebenen Pfade; sie gehören
            # in die Meldung, sonst wirft der Nutzer alles erneut ein (Astra-Review 18.09.2026).
            for p in payload.get("paths", []):
                print(f"In der Inbox: {p}")
        except Exception:
            pass
        if e.code == 401:
            raise SystemExit("Schlüssel wird nicht angenommen (401). Im Tool unter Wiki › Verbinden prüfen oder neu erzeugen.")
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


def _falsch(text: str) -> None:
    """Bedienfehler: Meldung plus Hilfe auf stderr, Exit 2."""
    print(text, file=sys.stderr)
    print("\n" + __doc__[__doc__.index("Aufgaben:"):].rstrip(), file=sys.stderr)
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
    prio = _zahl(_wert(args, "--prio"), "--prio", 1, 4)
    fuer = _wert(args, "--fuer")
    if len(args) != 1:
        _falsch("aufgabe-aendern braucht genau eine Nummer, z. B. CB-123." + (f" Unbekannt: {' '.join(args)}" if args else ""))
    nr = _nr(args[0])
    if erledigt and offen:
        _falsch("--erledigt und --offen schließen sich aus.")
    if faellig and faellig_weg:
        _falsch("--faellig und --faellig-weg schließen sich aus.")
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
    if prio is not None:
        body["prio"] = prio
    if fuer or fuer_weg:
        body["fuer"] = fuer
    if not body:
        _falsch("Nichts zu ändern.")
    res = call(f"{AUFGABEN}/{nr}", body, method="PATCH", plain_errors=True)
    a = res.get("aufgabe") or {}
    texte = {
        "erledigt": "erledigt" if a.get("erledigtAm") else "wieder offen",
        "notiz": "Notiz angehängt",
        "faellig": f"fällig {_tag(a.get('faellig'))}" if a.get("faellig") else "Fälligkeit entfernt",
        "prio": f"Prio {a.get('prioText') or a.get('prio')}",
        "fuer": f"für {a['fuer']}" if a.get("fuer") else "ohne Person",
    }
    geaendert = res.get("geaendert") or []
    print("Geändert: " + (", ".join(texte.get(g, g) for g in geaendert) or "nichts") + ".")
    print(_zeile(a))


def main(argv: list[str]) -> None:
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
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main(sys.argv)
