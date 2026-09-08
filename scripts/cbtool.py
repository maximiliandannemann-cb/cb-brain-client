#!/usr/bin/env python3
"""Gemeinsamer Kern des Plugins cb-brain-client: spricht mit dem CleverBrands-Tool über den
persönlichen Schlüssel (Bearer cbw_…). Kein GitHub, kein GBrain-Login — das Tool ist die einzige Tür.

Dateien:  ~/.cb-brain/tool-key   der Schlüssel aus dem Tool (Wiki › Verbinden)
          ~/.cb-brain/tool-url   optional, Standard https://company-interface.vercel.app

Befehle:  cbtool.py setup <schlüssel> [url] Schlüssel prüfen (Ping) und speichern; url nur für Vorschau-Adressen
          cbtool.py ping                    Verbindung prüfen
          cbtool.py search <frage> [n]      Treffer als JSON
          cbtool.py drop <text>             Text in die Inbox
          cbtool.py drop-file <pfad> [...]  Dateien (.md/.txt) in die Inbox
"""
import json, os, stat, sys, urllib.error, urllib.request

HOME = os.path.expanduser("~/.cb-brain")
TOKEN_FILE = os.path.join(HOME, "tool-key")
URL_FILE = os.path.join(HOME, "tool-url")
DEFAULT_URL = "https://company-interface.vercel.app"
TIMEOUT = 8.0


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


def call(path: str, body=None, method: str = "POST", key: str | None = None, timeout: float = TIMEOUT):
    key = key or token()
    if not key:
        raise SystemExit("Kein Schlüssel. Im Tool unter Wiki › Verbinden erzeugen, dann: /wiki-setup <schlüssel>")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"}
    bypass = os.environ.get("CB_VERCEL_BYPASS") or _read(os.path.join(HOME, "bypass"))
    if bypass:
        headers["x-vercel-protection-bypass"] = bypass  # nur für Vorschau-Adressen hinter Vercel-SSO
    req = urllib.request.Request(tool_url() + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error", "")
        except Exception:
            msg = ""
        if e.code == 401:
            raise SystemExit("Schlüssel wird nicht angenommen (401). Im Tool unter Wiki › Verbinden prüfen oder neu erzeugen.")
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


def cmd_drop(text: str) -> None:
    res = call("/api/brain-read/drop", {"text": text})
    for p in res.get("paths", []):
        print(f"In der Inbox: {p}")
    print("Sichtbar im Wiki nach dem nächsten Ingest-Lauf (nachts).")


def cmd_drop_files(paths: list[str]) -> None:
    files = []
    for p in paths:
        p = os.path.expanduser(p)
        if not p.lower().endswith((".md", ".txt", ".markdown")):
            raise SystemExit(f"Nur .md oder .txt: {p}")
        with open(p, encoding="utf-8", errors="replace") as f:
            files.append({"name": os.path.basename(p), "text": f.read()})
    res = call("/api/brain-read/drop", {"files": files})
    for p in res.get("paths", []):
        print(f"In der Inbox: {p}")
    print("Sichtbar im Wiki nach dem nächsten Ingest-Lauf (nachts).")


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
        cmd_drop(" ".join(args))
    elif cmd == "drop-file" and args:
        cmd_drop_files(args)
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main(sys.argv)
