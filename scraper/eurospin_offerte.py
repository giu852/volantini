"""Legge le offerte Eurospin dal servizio dati del volantino digitale (nessuna immagine, nessuna API a pagamento)."""
import re
import requests

HOME = "https://www.eurospin.it/volantino-nazionale-/"
API = "https://digitalflyer.eurospin.it/api/eurospin/eurospin-italia"
SIGLE = re.compile(r"\b(dop|igp|bio|uht|ogm)\b", re.I)

def _bello(s):
    s = (s or "").strip().lower()
    return SIGLE.sub(lambda m: m.group(1).upper(), s[:1].upper() + s[1:])

def _prop(el):
    return {p.get("code"): p.get("values") for p in el.get("properties", []) if p.get("type") != "FILE"}

def _un(p, k):
    v = p.get(k)
    return v[0] if v else None

def _iso(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if d and len(d) >= 8 else None

def _eur(x):
    return f"{x:.2f}".replace(".", ",") + " €"

def parse_prodotto(el, promo):
    p = _prop(el)
    titolo, marca = _un(p, "TITLE") or el.get("description") or "", (_un(p, "BRAND") or _un(p, "MARK") or "").strip()
    nome = _bello(titolo)
    prodotto = nome if not marca or marca.lower() in titolo.lower() else f"{marca.title()} {nome}"
    prezzo, vecchio = _un(p, "END-PRICE"), _un(p, "INITIAL-PRICE")
    if prezzo is None:
        return None
    if vecchio is not None and p.get("SHOW_INITIAL_PRICE") == [False]:
        vecchio = None
    pct = _un(p, "DISCOUNT-RATE")
    pct = int(round(pct)) if pct else (round(100 * (1 - prezzo / vecchio)) if vecchio else None)
    tipo = (_un(p, "DISCOUNT") or "").upper()
    promo_d = {"tipo": "sottocosto"} if "SOTTOCOSTO" in tipo else ({"tipo": "sconto", "valore": pct} if pct else {"tipo": "altro", "testo": ""})
    um = {"KG": "kg", "LT": "l", "L": "l"}.get((_un(p, "MEASURE-UNIT") or "").upper(), (_un(p, "MEASURE-UNIT") or "").lower())
    unit = f"{_eur(_un(p, 'END-KG-LT-PRICE'))} al {um}" if _un(p, "END-KG-LT-PRICE") and um else None
    c = el.get("code")
    codice = str(c.get("value") if isinstance(c, dict) else c or "").replace("COD-", "")
    dal, al = _iso(_un(p, "START-DATE-VALIDITY") or promo.get("startDate")), _iso(_un(p, "END-DATE-VALIDITY") or promo.get("endDate"))
    dett = [x for x in (unit, f"Dal {dal[8:]}.{dal[5:7]}. al {al[8:]}.{al[5:7]}." if dal and al else None) if x]
    return {"id": f"{promo.get('code')}-{codice or el.get('uniqueId')}", "prodotto": prodotto, "dettagli": " · ".join(dett) or None,
            "formato": _un(p, "DESCRIPTION") or "", "prezzo": prezzo, "prezzo_precedente": vecchio, "sconto_pct": pct,
            "prezzo_effettivo": prezzo, "promo": promo_d, "scade_prima": None, "categoria": (_un(p, "CATEGORY") or "").title(),
            "inizio": dal, "fine": al, "promozione": promo.get("description"),
            "url": f"https://www.eurospin.it/volantino/product?code={codice}&promotion={promo.get('code')}"}

def _chiave():
    from playwright.sync_api import sync_playwright
    tok = {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(); page = br.new_context(locale="it-IT").new_page()
        def on_req(r):
            a = r.headers.get("authorization")
            if a and "digitalflyer.eurospin.it/api" in r.url:
                tok.setdefault("h", a)
        page.on("request", on_req)
        page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
        for _ in range(25):
            if tok.get("h"):
                break
            page.wait_for_timeout(1000)
        br.close()
    if not tok.get("h"):
        raise RuntimeError("Nessuna chiave ottenuta dal sito Eurospin")
    return tok["h"]

def scarica_offerte():
    """Restituisce (offerte, promozioni)."""
    H = {"Authorization": _chiave(), "Accept": "application/json", "User-Agent": "Mozilla/5.0 (uso personale)"}
    def get(u):
        r = requests.get(u, headers=H, timeout=40); r.raise_for_status(); return r.json()
    promozioni, offerte = [], []
    for promo in get(f"{API}/stores/eurospin-italia/promotions"):
        if promo.get("hidden"):
            continue
        B = f"{API}/promotions/{promo['alias']}/stores/eurospin-italia"
        elementi, pagina = [], 0
        while True:
            r = get(f"{B}/products?page={pagina}&size=500")
            elementi += r.get("elements", [])
            pagina += 1
            if r.get("last", True) or pagina >= r.get("totalPages", 1):
                break
        n0 = len(offerte)
        for el in elementi:
            if not el.get("properties"):
                c = el.get("code"); cod = c.get("value") if isinstance(c, dict) else c
                el = get(f"{B}/products-by-code/COD-{str(cod).replace('COD-', '')}")
            o = parse_prodotto(el, promo)
            if o:
                offerte.append(o)
        promozioni.append({"negozio": "Eurospin", "id": promo["alias"], "titolo": promo.get("description"), "nome": promo.get("description"),
                           "dal": _iso(promo.get("startDate")), "al": _iso(promo.get("endDate")),
                           "url": f"https://www.eurospin.it/smt-digitalflyer/punti-vendita/eurospin-italia/promozioni/{promo['alias']}",
                           "pdf": None, "pagine": None, "pagine_cibo": [], "n_offerte": len(offerte) - n0, "stato": "sito"})
        print(f"  Eurospin {promo['alias']}: {len(offerte) - n0} prodotti")
    if not offerte:
        raise RuntimeError("Nessun prodotto Eurospin letto")
    return offerte, promozioni
