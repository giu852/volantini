#!/usr/bin/env python3
"""Legge le offerte attuali dalla homepage MPreis (https://www.mpreis.it/it).
Uso: pip install requests beautifulsoup4 && python mpreis_test.py
Salva mpreis_offerte.json e stampa una tabella."""
import json, re, sys
from datetime import date
import requests
from bs4 import BeautifulSoup

URL = "https://www.mpreis.it/it"

def euro(txt):
    m = re.search(r"(\d+(?:\.\d{3})*,\d{2})", txt or "")
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None

def periodo(txt):
    """'VEN 30.10. – VEN 13.11.' -> ('2026-10-30', '2026-11-13')"""
    d = re.findall(r"(\d{2})\.(\d{2})\.", txt or "")
    if len(d) < 2:
        return None, None
    y = date.today().year
    (d1, m1), (d2, m2) = d[0], d[1]
    y2 = y + 1 if (int(m2), int(d2)) < (int(m1), int(d1)) else y
    return f"{y}-{m1}-{d1}", f"{y2}-{m2}-{d2}"

def testo(el):
    return el.get_text(" ", strip=True) if el else ""

def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    widget = soup.select_one(".c3-products-widget")
    if widget is None:
        raise RuntimeError("Widget offerte non trovato: la pagina è cambiata?")
    titolo_periodo = testo(widget.select_one(".c3-products-widget__heading-title"))
    dal, al = periodo(titolo_periodo)
    offerte = []
    for p in widget.select(".c3-product"):
        prezzo_el = p.select_one(".c3-product__price")
        vecchio_el = prezzo_el.select_one("del") if prezzo_el else None
        vecchio = euro(testo(vecchio_el)) if vecchio_el else None
        if vecchio_el:
            vecchio_el.extract()
        nuovo = euro(testo(prezzo_el))
        b_tit = testo(p.select_one(".c3-product__badge-title"))
        b_sub = testo(p.select_one(".c3-product__badge-subtitle"))
        dettagli = testo(p.select_one(".c3-product__content"))
        # tipo di promo dal badge
        if re.match(r"-\s*\d+\s*%", b_tit):
            promo = {"tipo": "sconto", "valore": int(re.search(r"\d+", b_tit).group())}
        elif b_tit.startswith("1+1"):
            promo = {"tipo": "1+1"}
        elif re.match(r"da\s*\d+", b_tit):
            promo = {"tipo": "multi", "quantita": int(re.search(r"\d+", b_tit).group()), "unita": b_sub}
        else:
            promo = {"tipo": "altro", "testo": f"{b_tit} {b_sub}".strip()}
        m = re.search(r"valido fino al (\d{2}\.\d{2}\.)", dettagli)
        sconto = round(100 * (1 - nuovo / vecchio)) if vecchio and nuovo else None
        offerte.append({
            "prodotto": testo(p.select_one(".c3-product__title")),
            "dettagli": dettagli or None,
            "formato": testo(p.select_one(".c3-product__unit")).rstrip(", "),
            "prezzo": nuovo,
            "prezzo_precedente": vecchio,
            "sconto_pct": promo.get("valore") or sconto,
            "prezzo_effettivo": round(nuovo / 2, 2) if promo["tipo"] == "1+1" and nuovo else nuovo,
            "promo": promo,
            "scade_prima": m.group(1) if m else None,
        })
    return {"periodo": titolo_periodo, "dal": dal, "al": al, "offerte": offerte}

if __name__ == "__main__":
    html = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 (uso personale)"}).text
    dati = parse(html)
    json.dump(dati, open("mpreis_offerte.json", "w"), ensure_ascii=False, indent=2)
    print(f"Periodo: {dati['periodo']} | offerte: {len(dati['offerte'])}")
    for o in dati["offerte"]:
        print(f"- {o['prodotto'][:42]:<42} {str(o['prezzo_precedente'] or ''):>6} -> {o['prezzo']}  {o['promo']['tipo']}")
