"""Legge le offerte, unisce quelle inserite a mano e scrive web/data/offerte.json."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from mpreis import parse, URL
import lidl
import lidl_offerte

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
    lidl_off = []
    try:
        lidl_off = lidl_offerte.scarica_offerte()
        date = sorted({o["valido_dal"] for o in lidl_off if o["valido_dal"]}) + sorted({o["valido_al"] for o in lidl_off if o["valido_al"]})
        per = f"{min(date)} – {max(date)}" if date else "settimana"
        offerte += [dict(o, negozio="Lidl") for o in lidl_off]
        periodi["Lidl"] = per
        fonti.append({"nome": "Lidl", "ok": True, "n": len(lidl_off), "periodo": per + " (dal sito)"})
        print(f"Lidl: {len(lidl_off)} offerte dal sito")
    except Exception as e:
        print("ATTENZIONE Lidl offerte (uso quelle inserite a mano):", e)
    for m in carica_manuali(DATA):
        if m["negozio"] == "Lidl" and lidl_off:
            continue
        offerte += [dict(o, negozio=m["negozio"]) for o in m["offerte"]]
        periodi[m["negozio"]] = m["periodo"]
        fonti.append({"nome": m["negozio"], "ok": True, "n": len(m["offerte"]), "periodo": m["periodo"] + " (inserite a mano)"})
    volantini = []
    try:
        letti = set(next((m.get("letto_da", []) for m in carica_manuali(DATA) if m["negozio"] == "Lidl"), []))
        volantini = lidl.trova_volantini()
        for v in volantini:
            v["stato"] = "sito" if lidl_off else ("parziale" if v["id"] in letti else "da_leggere")
        print(f"Lidl: {len(volantini)} volantini attivi")
    except Exception as e:
        print("ATTENZIONE Lidl:", e)
    (DATA / "offerte.json").write_text(json.dumps({"aggiornato": datetime.now(timezone.utc).isoformat(), "periodi": periodi, "fonti": fonti, "volantini": volantini, "offerte": offerte}, ensure_ascii=False, indent=1))
    print(f"OK: {len(offerte)} offerte da {len(fonti)} fonti")

if __name__ == "__main__":
    main()
