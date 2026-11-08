"""Legge le offerte dalle sezioni 'offerte attuali' di lidl.it (prezzi scritti nella pagina, nessuna API a pagamento)."""
import json, re
from urllib.parse import unquote

HOME = "https://www.lidl.it/"
SEZIONI = ("sottocosto", "frutta-e-verdura", "carne-e-pesce", "grandi-marche", "mega-offerte", "super-offerte",
           "deluxe", "favorina", "lidl-plus", "eridanous")
NEW = re.compile(r"^(\d+[.,]\d{2})\s?€\*$")
OLD = re.compile(r"^(\d+[.,]\d{2})\s?€$")
JS = r"""() => [...document.querySelectorAll('.product-grid-box')].map(t => ({
  impr: t.getAttribute('data-gridbox-impression') || '', testo: t.innerText,
  href: (t.querySelector('a.odsc-tile__link') || {}).href || ''}))"""

def _f(s):
    return float(s.replace(",", "."))

def parse_tile(testo, impr, href):
    righe = [r.strip() for r in testo.splitlines() if r.strip()]
    try:
        meta = json.loads(unquote(impr))
    except Exception:
        meta = {}
    i = next((k for k, r in enumerate(righe) if NEW.match(r)), None)
    if i is None:
        return None
    prezzo = _f(NEW.match(righe[i]).group(1))
    prima, dopo = righe[:i], righe[i + 1:]
    vecchio = next((_f(OLD.match(r).group(1)) for r in prima if OLD.match(r)), None)
    pct = next((int(m.group(1)) for r in prima for m in [re.match(r"^-\s*(\d+)\s*%$", r)] if m), None)
    if pct is None and vecchio:
        pct = round(100 * (1 - prezzo / vecchio))
    formato = dopo[0] if dopo and "=" not in dopo[0] and not dopo[0].lower().startswith("solo in punto") else ""
    unit = next((r for r in dopo if "=" in r and re.match(r"^\d", r)), None)
    val = next((m for r in righe for m in [re.search(r"dal (\d{2}\.\d{2}\.) al (\d{2}\.\d{2}\.)", r)] if m), None)
    plus = any("lidl plus" in r.lower() for r in righe)
    sotto = any(r.upper() == "SOTTOCOSTO" for r in righe)
    nome = meta.get("name") or (righe[1] if len(righe) > 1 else "")
    marca = (meta.get("brand") or "").strip()
    prodotto = nome if not marca or marca.lower().strip("®™ ") in nome.lower() else f"{marca.title()} {nome}"
    cat = " / ".join((meta.get("wonCategoryPrimary") or "").split("/")[2:])
    dett = [x for x in (unit, "Con Lidl Plus" if plus else None, f"Dal {val.group(1)} al {val.group(2)}" if val else None) if x]
    promo = {"tipo": "sottocosto"} if sotto else ({"tipo": "sconto", "valore": pct} if pct else {"tipo": "altro", "testo": ""})
    return {"id": str(meta.get("id") or href), "prodotto": prodotto, "dettagli": " · ".join(dett) or None, "formato": formato,
            "prezzo": prezzo, "prezzo_precedente": vecchio, "sconto_pct": pct, "prezzo_effettivo": prezzo, "promo": promo,
            "scade_prima": None, "categoria": cat, "valido_dal": val.group(1) if val else None, "valido_al": val.group(2) if val else None,
            "url": href}

def _cookie(page):
    for et in ("Accetta tutti", "Accetta", "Accetto"):
        try:
            page.get_by_role("button", name=et).first.click(timeout=1500); return
        except Exception:
            pass

def _espandi(page):
    ultimo = -1
    for _ in range(10):
        for _ in range(5):
            page.mouse.wheel(0, 2500); page.wait_for_timeout(700)
        n = page.locator(".product-grid-box").count()
        try:
            page.get_by_text("Mostra di più").first.click(timeout=2000); page.wait_for_timeout(2500)
        except Exception:
            break
        if n == ultimo:
            break
        ultimo = n

def scarica_offerte():
    from playwright.sync_api import sync_playwright
    prodotti = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        page = br.new_context(locale="it-IT", viewport={"width": 1280, "height": 900}).new_page()
        page.goto(HOME, wait_until="domcontentloaded", timeout=60000); page.wait_for_timeout(5000); _cookie(page)
        _espandi(page)
        links = page.eval_on_selector_all("a[href]", "els=>els.map(e=>e.href)")
        sez = []
        for h in links:
            if "/c/store/" in h and any(k in h for k in SEZIONI) and h not in sez:
                sez.append(h)
        if not sez:
            raise RuntimeError("Nessuna sezione offerte trovata nella pagina principale")
        for h in sez:
            nome = (re.search(r"/c/store/(.+?)-kw-", h) or re.search(r"/c/store/([^/]+)/", h)).group(1)
            page.goto(h, wait_until="domcontentloaded", timeout=60000); page.wait_for_timeout(5000)
            _espandi(page)
            for t in page.evaluate(JS):
                o = parse_tile(t["testo"], t["impr"], t["href"])
                if o:
                    prodotti.setdefault(o["id"], dict(o, sezioni=[]))["sezioni"].append(nome)
            print(f"  {nome}: {len(prodotti)} prodotti finora")
        br.close()
    if not prodotti:
        raise RuntimeError("Nessun prodotto letto")
    return list(prodotti.values())
