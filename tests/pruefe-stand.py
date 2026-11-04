#!/usr/bin/env python3
"""Prüfskript für die Kontextzeile des Hooks mit Stand und „überholt" (Wiki-Aktualität, 04.11.2026). Ohne Framework,
ohne Netz, eigenes HOME (der Hook wird nur geladen, nicht ausgeführt).
Aufruf: /usr/bin/python3 tests/pruefe-stand.py   (Exit 0 = alles grün)"""
import importlib.util, os, sys, tempfile

os.environ["HOME"] = tempfile.mkdtemp()
HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "brain-context.py")
spec = importlib.util.spec_from_file_location("hook", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

fehler = 0


def pruefe(name: str, ist: str, soll: str) -> None:
    global fehler
    ok = ist == soll
    print(("ok    " if ok else "FEHLER ") + name + ("" if ok else f"\n  ist:  {ist}\n  soll: {soll}"))
    fehler += 0 if ok else 1


basis = {"title": "Kronas / RSK", "slug": "suppliers/kronas-rsk", "type": "lieferant", "source": "shared", "snippet": "AG0045 gilt bis 31.12.2026"}
pruefe("mit Stand", hook.treffer_zeile(dict(basis, date="2026-11-02", ueberholt=False)),
       "- [lieferant · Stand 02.11.2026] Kronas / RSK (suppliers/kronas-rsk): AG0045 gilt bis 31.12.2026")
pruefe("überholt statt Stand", hook.treffer_zeile(dict(basis, date="2026-11-02", ueberholt=True)),
       "- [lieferant · überholt, gilt nicht mehr] Kronas / RSK (suppliers/kronas-rsk): AG0045 gilt bis 31.12.2026")
pruefe("älteres Tool ohne Felder", hook.treffer_zeile(basis),
       "- [lieferant] Kronas / RSK (suppliers/kronas-rsk): AG0045 gilt bis 31.12.2026")
pruefe("kaputtes Datum", hook.treffer_zeile(dict(basis, date="gestern")),
       "- [lieferant] Kronas / RSK (suppliers/kronas-rsk): AG0045 gilt bis 31.12.2026")
pruefe("Tool-Treffer", hook.treffer_zeile(dict(basis, source="tool", date="2026-10-29")),
       "- [Tool · Stand 29.10.2026] Kronas / RSK (suppliers/kronas-rsk): AG0045 gilt bis 31.12.2026")

sys.exit(1 if fehler else 0)
