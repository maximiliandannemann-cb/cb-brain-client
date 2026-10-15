#!/usr/bin/env python3
"""Selbst-Update des Plugins: holt den Marketplace `cleverbrands` neu und aktualisiert
cb-brain-client@cleverbrands über die `claude`-CLI. Startet losgelöst aus dem Kontext-Hook,
höchstens einmal je 24 Stunden.

Grund: Claude Code holte den Marketplace trotz `autoUpdate: true` nicht neu (beobachtet am
15.10.2026 mit 2.1.300). Ändert sich die installierte Version, legt das Skript
~/.cb-brain/update-note an; der Hook sagt es beim nächsten Prompt einmal an.

Aufruf:  python3 selbst-update.py [<plugin-root>]
Log:     ~/.cb-brain/logs/update.log, eine Zeile je Lauf, keine Geheimnisse.
"""
from __future__ import annotations

import json, os, re, shutil, subprocess, sys, time
from datetime import datetime

PLUGIN = "cb-brain-client@cleverbrands"
MARKETPLACE = "cleverbrands"
HOME = os.path.expanduser("~/.cb-brain")
NOTE = os.path.join(HOME, "update-note")
LOCK = os.path.join(HOME, "update.lock")
LOG = os.path.join(HOME, "logs", "update.log")
TIMEOUT = 120  # je CLI-Aufruf
LOCK_STALE = 15 * 60  # eine Sperre, die älter ist, stammt von einem abgestürzten Lauf


def log(line: str) -> None:
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat(timespec='seconds')} {line}\n")
    except Exception:
        pass


def find_claude() -> str | None:
    found = shutil.which("claude")
    if found:
        return found
    for p in ("~/.local/bin/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude"):
        p = os.path.expanduser(p)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def config_dir() -> str:
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def installed_version() -> str | None:
    """Version laut plugins/installed_plugins.json (Format v2: plugins[id] ist eine Liste von
    Einträgen je Scope mit scope, installPath, version, ...). Bevorzugt den Eintrag mit scope "user"."""
    try:
        with open(os.path.join(config_dir(), "plugins", "installed_plugins.json"), encoding="utf-8") as fh:
            entries = json.load(fh)["plugins"][PLUGIN]
        entry = next((e for e in entries if e.get("scope") == "user"), entries[0])
        return entry.get("version") or None
    except Exception:
        return None


def manifest_version(root: str | None) -> str | None:
    if not root:
        return None
    try:
        with open(os.path.join(root, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            return json.load(fh).get("version") or None
    except Exception:
        return None


def take_lock() -> bool:
    os.makedirs(HOME, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(LOCK) > LOCK_STALE:
                    os.remove(LOCK)
                    continue
            except OSError:
                continue
            return False
    return False


def short(text: str) -> str:
    """Letzte Ausgabezeile für das Log, Zugangsdaten in URLs geschwärzt."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    # Die fatal:-Zeile von git nennt den Grund, die letzte Zeile ist oft nur Fülltext (Review B3).
    last = next((ln for ln in lines if ln.lower().startswith(("fatal:", "error:", "✘"))), lines[-1] if lines else "")
    return re.sub(r"://[^/@\s]+@", "://***@", last)[:200]


def run(cli: str, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run([cli, "plugin", *args], stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=TIMEOUT)
        return p.returncode, short(p.stdout + "\n" + p.stderr)
    except subprocess.TimeoutExpired:
        return -1, f"Zeitlimit {TIMEOUT} s"
    except Exception as e:  # noqa: BLE001
        return -1, type(e).__name__


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDE_PLUGIN_ROOT")
    cli = find_claude()
    if not cli:
        log("claude-CLI nicht gefunden, kein Update")
        return
    if not take_lock():
        log("läuft schon (Sperre), übersprungen")
        return
    try:
        # Vorher aus installed_plugins.json, nicht aus dem laufenden Plugin-Ordner: nach einem Update
        # läuft bis zum Neustart noch die alte Version, und ein Vergleich damit meldete jeden Tag neu.
        before = installed_version() or manifest_version(root)
        rc_m, out_m = run(cli, "marketplace", "update", MARKETPLACE)
        rc_p, out_p = run(cli, "update", PLUGIN)
        after = installed_version()
        if after and before and after != before:
            tmp = NOTE + ".tmp"  # atomar, damit der Hook nie eine halbe Notiz liest (Review B1)
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"version": after, "vorher": before, "zeit": datetime.now().isoformat(timespec="seconds")}, fh)
            os.replace(tmp, NOTE)
            result = "aktualisiert"
        elif not after:
            result = "unbekannt"  # installed_plugins.json nicht lesbar (Review B2)
        elif rc_m == 0 and rc_p == 0:
            result = "aktuell"
        else:
            result = "fehler"
        detail = ""
        if rc_m != 0:
            detail += f" marketplace={rc_m}:{out_m!r}"
        if rc_p != 0:
            detail += f" update={rc_p}:{out_p!r}"
        log(f"vorher={before} nachher={after} ergebnis={result}{detail}")
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 - läuft unbeaufsichtigt, nie mit Traceback enden
        log(f"abbruch: {type(e).__name__}")
