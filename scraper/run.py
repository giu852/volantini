"""Legge le offerte e scrive web/data/offerte.json (lanciato ogni giorno da GitHub Actions)."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from mpreis import parse, URL

OUT = Path(__file__).resolve().parent.parent / "web" / "data" / "offerte.json"
html = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 (uso personale)"}).text
d = parse(html)
if not d["offerte"]:
    sys.exit("Nessuna offerta trovata: la pagina è cambiata?")
for o in d["offerte"]:
    o["negozio"] = "MPreis"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"aggiornato": datetime.now(timezone.utc).isoformat(), "periodi": {"MPreis": d["periodo"]}, "fonti": [{"nome": "MPreis", "ok": True, "n": len(d["offerte"]), "periodo": d["periodo"]}], "offerte": d["offerte"]}, ensure_ascii=False, indent=1))
print(f"OK: {len(d['offerte'])} offerte MPreis ({d['periodo']})")
