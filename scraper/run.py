"""Legge le offerte, unisce quelle inserite a mano e scrive web/data/offerte.json."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from mpreis import parse, URL

DATA = Path(__file__).resolve().parent.parent / "web" / "data"

def carica_manuali(cartella):
    """Ogni file in manuale/ ha: negozio, periodo, offerte."""
    return [json.loads(f.read_text()) for f in sorted((cartella / "manuale").glob("*.json"))]

def main():
    html = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 (uso personale)"}).text
    d = parse(html)
    if not d["offerte"]:
        sys.exit("Nessuna offerta trovata: la pagina è cambiata?")
    offerte = [dict(o, negozio="MPreis") for o in d["offerte"]]
    periodi = {"MPreis": d["periodo"]}
    fonti = [{"nome": "MPreis", "ok": True, "n": len(offerte), "periodo": d["periodo"]}]
    for m in carica_manuali(DATA):
        offerte += [dict(o, negozio=m["negozio"]) for o in m["offerte"]]
        periodi[m["negozio"]] = m["periodo"]
        fonti.append({"nome": m["negozio"], "ok": True, "n": len(m["offerte"]), "periodo": m["periodo"] + " (inserite a mano)"})
    (DATA / "offerte.json").write_text(json.dumps({"aggiornato": datetime.now(timezone.utc).isoformat(), "periodi": periodi, "fonti": fonti, "offerte": offerte}, ensure_ascii=False, indent=1))
    print(f"OK: {len(offerte)} offerte da {len(fonti)} fonti")

if __name__ == "__main__":
    main()
