"""Legge le offerte, unisce quelle inserite a mano e scrive web/data/offerte.json."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from mpreis import parse, URL
import lidl
import lidl_offerte
import eurospin_offerte

DATA = Path(__file__).resolve().parent.parent / "web" / "data"

def _iso(gm):
    """'05.11.' -> '2026-11-05' (anno corrente; a cavallo d'anno sposta l'anno)."""
    if not gm:
        return None
    g, m = int(gm[:2]), int(gm[3:5])
    oggi = datetime.now(timezone.utc)
    anno = oggi.year + (1 if (oggi.month >= 11 and m <= 2) else 0)
    return f"{anno}-{m:02d}-{g:02d}"

def carica_manuali(cartella):
    """Ogni file in manuale/ ha: negozio, periodo, offerte."""
    return [json.loads(f.read_text()) for f in sorted((cartella / "manuale").glob("*.json"))]

def main():
    html = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 (uso personale)"}).text
    d = parse(html)
    if not d["offerte"]:
        sys.exit("Nessuna offerta trovata: la pagina è cambiata?")
    offerte = [dict(o, negozio="MPreis", inizio=d["dal"], fine=d["al"]) for o in d["offerte"]]
    periodi = {"MPreis": d["periodo"]}
    fonti = [{"nome": "MPreis", "ok": True, "n": len(offerte), "periodo": d["periodo"]}]
    lidl_off = []
    try:
        lidl_off = lidl_offerte.scarica_offerte()
        date = sorted({o["valido_dal"] for o in lidl_off if o["valido_dal"]}) + sorted({o["valido_al"] for o in lidl_off if o["valido_al"]})
        per = f"{min(date)} – {max(date)}" if date else "settimana"
        offerte += [dict(o, negozio="Lidl", inizio=_iso(o["valido_dal"]), fine=_iso(o["valido_al"])) for o in lidl_off]
        periodi["Lidl"] = per
        fonti.append({"nome": "Lidl", "ok": True, "n": len(lidl_off), "periodo": per + " (dal sito)"})
        print(f"Lidl: {len(lidl_off)} offerte dal sito")
    except Exception as e:
        print("ATTENZIONE Lidl offerte (uso quelle inserite a mano):", e)
    eur_off, eur_vol = [], []
    try:
        eur_off, eur_vol = eurospin_offerte.scarica_offerte()
        offerte += [dict(o, negozio="Eurospin") for o in eur_off]
        d1 = min(o["inizio"] for o in eur_off if o["inizio"]); d2 = max(o["fine"] for o in eur_off if o["fine"])
        per = f"{d1[8:]}.{d1[5:7]}. – {d2[8:]}.{d2[5:7]}."
        periodi["Eurospin"] = per
        fonti.append({"nome": "Eurospin", "ok": True, "n": len(eur_off), "periodo": per + " (dal sito)"})
        print(f"Eurospin: {len(eur_off)} offerte dal sito")
    except Exception as e:
        print("ATTENZIONE Eurospin:", e)
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
    volantini += eur_vol
    (DATA / "offerte.json").write_text(json.dumps({"aggiornato": datetime.now(timezone.utc).isoformat(), "periodi": periodi, "fonti": fonti, "volantini": volantini, "offerte": offerte}, ensure_ascii=False, indent=1))
    print(f"OK: {len(offerte)} offerte da {len(fonti)} fonti")

if __name__ == "__main__":
    main()
