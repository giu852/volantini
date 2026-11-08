"""Trova i volantini Lidl attivi per il negozio di Varna (Via Brennero 35) dal servizio pubblico dei volantini."""
import json, re
import requests

API = "https://endpoints.leaflets.schwarz/v4"
HDR = {"User-Agent": "Mozilla/5.0 (uso personale)", "Accept": "application/json"}
OVERVIEW = {"client_locale": "lidl/it-IT", "region_id": "102", "store_id": "925",
            "subcategories": "05fead62-6251-11e7-a039-005056ab0fb6,1f7cf46b-6251-11e7-a039-005056ab0fb6,ddf80c1c-6ae5-11e7-a039-005056ab0fb6"}
FOOD = re.compile(r"alimentar|frutta|verdura|ortofrutta|carne|pesce|latticin|formagg|salum|prosciutt|yogurt|latte|pasta|pane|dolc|cioccolat|caff[eè]|bevand|birra|vino|gastronom|specialit|tortellin|mozzarella|hamburger|salmone|alici|noci|pistacchi|dessert|freschi", re.I)

def identificatori(testo):
    """Ricava gli identificatori dei volantini da qualunque punto del JSON dell'elenco."""
    trovati = re.findall(r"/l/it/volantini/([^/\"?]+)/", testo)
    trovati += re.findall(r'"(?:flyer_)?(?:identifier|slug)"\s*:\s*"([^"]+)"', testo)
    visti = []
    for t in trovati:
        if t not in visti:
            visti.append(t)
    return visti

def pagine_cibo(pagine):
    return [p["number"] for p in pagine if FOOD.search((p.get("altText") or "") + " " + (p.get("keyWords") or "")[:0])]

def trova_volantini():
    r = requests.get(f"{API}/overview/", params=OVERVIEW, headers=HDR, timeout=30)
    r.raise_for_status()
    ids = identificatori(r.text)
    if not ids:
        raise RuntimeError("Nessun volantino nell'elenco. Inizio risposta: " + r.text[:600])
    out = []
    for i in ids:
        f = requests.get(f"{API}/flyer", params={"flyer_identifier": i}, headers=HDR, timeout=30).json().get("flyer") or {}
        if not (f.get("isActive") and f.get("status") == "current" and (f.get("name") or "").lower().startswith("offerte valide")):
            continue
        pag = f.get("pages") or []
        out.append({"negozio": "Lidl", "id": i, "titolo": f.get("title"), "nome": f.get("name"),
                    "dal": f.get("offerStartDate") or f.get("startDate"), "al": f.get("offerEndDate") or f.get("endDate"),
                    "url": f.get("flyerUrlAbsolute"), "pdf": f.get("pdfUrl"),
                    "pagine": len(pag), "pagine_cibo": pagine_cibo(pag)})
    return out
