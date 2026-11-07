"""Test una tantum: da dove arrivano nomi e prezzi nelle pagine offerte di lidl.it? Non modifica nulla dell'app."""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

HOME = "https://www.lidl.it/"
FALLBACK = "https://www.lidl.it/c/store/sottocosto-lidl-black-days-kw-45-26/a10106087"
OUT = Path("out"); OUT.mkdir(exist_ok=True)
LOG = open(OUT / "log.txt", "w", encoding="utf-8")
CHIAVI = ('"price"', "prezzo", "productId", "erpNumber", '"title"', "€")

def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()

def apri(ctx, url, nome):
    say(f"\n===== {nome}: {url}")
    page = ctx.new_page(); risp = []
    def on_resp(r):
        try:
            ct = r.headers.get("content-type", "")
            if "json" in ct:
                risp.append((r.url, r.status, r.text()))
        except Exception:
            pass
    page.on("response", on_resp)
    m = page.goto(url, wait_until="domcontentloaded", timeout=60000)
    say("Stato:", m.status if m else "?", "| titolo:", page.title())
    page.wait_for_timeout(6000)
    for et in ("Accetta tutti", "Accetta", "Accetto", "Consenti tutti"):
        try:
            page.get_by_role("button", name=et).first.click(timeout=1500); say("Cookie: cliccato", et); break
        except Exception:
            pass
    for _ in range(6):
        page.mouse.wheel(0, 2500); page.wait_for_timeout(1200)
    for et in ("Mostra tutte le offerte", "Mostra di più"):
        try:
            page.get_by_text(et).first.click(timeout=2000); say("Cliccato:", et); page.wait_for_timeout(4000)
        except Exception:
            pass
    for _ in range(4):
        page.mouse.wheel(0, 3000); page.wait_for_timeout(1000)
    page.screenshot(path=str(OUT / f"{nome}.png"), full_page=True)
    testo = page.inner_text("body")
    righe = [r.strip() for r in testo.splitlines() if "€" in r]
    say(f"Righe con '€' nel testo visibile: {len(righe)}")
    for r in righe[:25]: say("   ", r[:140])
    utili = [x for x in risp if any(k in x[2] for k in CHIAVI) and "cookielaw" not in x[0] and "onetrust" not in x[0]]
    say(f"Risposte JSON totali: {len(risp)} | con possibili prezzi/prodotti: {len(utili)}")
    for u, st, corpo in utili[:8]:
        say(f"  JSON {st} ({len(corpo)} caratteri) {u[:220]}\n     anteprima: {corpo[:700]!r}")
    links = page.eval_on_selector_all("a[href]", "els=>els.map(e=>[e.href,(e.innerText||'').trim().slice(0,60)])")
    page.close()
    return links

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(locale="it-IT", viewport={"width": 1280, "height": 900})
    links = apri(ctx, HOME, "home")
    sez = []
    for h, t in links:
        if "/c/store/" in h and h not in [s[0] for s in sez]:
            sez.append((h, t))
    say(f"\nSezioni offerte trovate (/c/store/): {len(sez)}")
    for h, t in sez: say("  ", h, "|", t.replace("\n", " "))
    scelte = [h for key in ("sottocosto", "frutta-e-verdura", "lidl-plus") for h, _ in sez if key in h][:3]
    if not scelte: scelte = [FALLBACK]
    for i, h in enumerate(scelte): apri(ctx, h, f"sezione{i+1}")
    br.close()
