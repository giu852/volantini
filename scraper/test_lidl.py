"""Test una tantum: come fornisce Lidl i dati del volantino? Non modifica nulla dell'app."""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

STORE = "https://www.lidl.it/s/it-IT/ricerca-negozio/varna-bz/via-brennero-35/"
FALLBACK = "https://www.lidl.it/l/it/volantini/offerte-valide-dal-2-11-al-11-11-volantino-settimanale-NAZ-sci/view/flyer/page/1"
OUT = Path("out"); OUT.mkdir(exist_ok=True)
LOG = open(OUT / "log.txt", "w", encoding="utf-8")

def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()

def esplora(ctx, url, nome):
    say(f"\n===== {nome}: {url}")
    page = ctx.new_page(); risposte = []
    def on_resp(r):
        try:
            ct = r.headers.get("content-type", "")
            corpo = r.text()[:400] if ("json" in ct or "text/plain" in ct) else ""
            risposte.append((r.url, r.status, ct, corpo))
        except Exception:
            risposte.append((r.url, r.status, "?", ""))
    page.on("response", on_resp)
    main = page.goto(url, wait_until="domcontentloaded", timeout=60000)
    say("Stato pagina:", main.status if main else "?", "| titolo:", page.title())
    page.wait_for_timeout(6000)
    for et in ("Accetta tutti", "Accetta", "Accetto", "Consenti tutti"):
        try:
            page.get_by_role("button", name=et).first.click(timeout=1500); say("Cookie: cliccato", et); break
        except Exception:
            pass
    page.wait_for_timeout(8000)
    page.screenshot(path=str(OUT / f"{nome}.png"), full_page=False)
    html = page.content()
    say("HTML:", len(html), "caratteri | __NEXT_DATA__:", "__NEXT_DATA__" in html, "| ld+json:", "ld+json" in html)
    say("Menzioni di 'price/prezzo' nell'HTML:", len(re.findall(r"price|prezzo", html, re.I)))
    json_r = [r for r in risposte if "json" in r[2]]
    say(f"Richieste totali: {len(risposte)} | risposte JSON: {len(json_r)}")
    for u, st, ct, corpo in json_r:
        say(f"  JSON {st} {u[:150]}\n     anteprima: {corpo[:300]!r}")
    tipi = {}
    for u, st, ct, _ in risposte:
        k = ct.split(";")[0] or "?"; tipi[k] = tipi.get(k, 0) + 1
    say("Tipi di risposta:", tipi)
    imgs = sorted({u for u, st, ct, _ in risposte if ct.startswith("image/") and "leaflet" in u})
    say(f"Immagini dal servizio volantini: {len(imgs)}")
    for u in imgs[:6]: say("  ", u[:160])
    links = page.eval_on_selector_all("a[href]", "els=>els.map(e=>e.href)")
    page.close()
    return links

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(locale="it-IT", viewport={"width": 1280, "height": 900})
    links = esplora(ctx, STORE, "negozio")
    vol = sorted({l for l in links if "/l/it/volantini/" in l})
    say("\nLink a volantini trovati nella pagina del negozio:", len(vol))
    for l in vol: say("  ", l)
    scelto = next((l for l in vol if "settimanale" in l), None) or FALLBACK
    esplora(ctx, scelto, "volantino")
    br.close()
