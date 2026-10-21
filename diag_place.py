"""Sonde : que contient la page d'un lieu unique (redirection /maps/place/) ?

Objectif : vérifier si l'on peut extraire nom / adresse / téléphone / GPS
quand Google redirige une recherche mono-résultat vers une page de lieu,
cas quiToday produit PANEL_MISSING alors que la donnée existe.

Usage : python diag_place.py "Boumerdès" "polyclinique"
"""
import asyncio
import sys
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright


async def probe(wilaya: str, categorie: str):
    query = f"{categorie} {wilaya} Algérie"
    url = "https://www.google.com/maps/search/" + quote(query) + "?hl=fr&gl=DR"

    launch_kwargs = {"headless": True}
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if chrome.exists():
        launch_kwargs["executable_path"] = str(chrome)

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        ctx = await browser.new_context(locale="fr-FR", timezone_id="Africa/Algiers",
                                        viewport={"width": 1440, "height": 1000})
        await ctx.add_cookies([
            {"name": "CONSENT", "value": "YES+cb.20220310-17-p0.en+FX+111",
             "domain": ".google.com", "path": "/"},
            {"name": "SOCS", "value": "CAESHAgBEhIaAB", "domain": ".google.com", "path": "/"},
        ])
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        print("URL finale :", page.url[:180])
        print("Est page lieu :", "/maps/place/" in page.url)

        # Nom : premier h1 non vide
        try:
            h1 = page.locator("h1").first
            nom = (await h1.inner_text()).strip()
        except Exception as e:
            nom = f"<erreur {e}>"
        print("h1 :", repr(nom[:120]))

        # aria-labels du panneau de droite
        labels = await page.evaluate("""
            () => {
                const out = [];
                document.querySelectorAll('button[aria-label], a[aria-label]').forEach(el => {
                    const a = el.getAttribute('aria-label');
                    if (a && a.length > 2) out.push(a);
                });
                return out.slice(0, 40);
            }
        """)
        print("\naria-labels :")
        for l in labels:
            print("   ", l[:110])

        # Coordonnées dans l'URL
        print("\nCoordonnées visibles dans l'URL :", "@" in page.url)

        # Métadonnées meta
        for name in ("og:title", "og:url", "description"):
            try:
                content = await page.evaluate(
                    "(n) => { const m = document.querySelector(`meta[property='${n}']`)"
                    " || document.querySelector(`meta[name='${n}']`);"
                    " return m ? m.getAttribute('content') : null; }", name)
                print(f"meta {name} :", (content or "")[:140])
            except Exception:
                pass

        await ctx.close()
        await browser.close()


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "Boumerdès"
    c = sys.argv[2] if len(sys.argv) > 2 else "polyclinique"
    asyncio.run(probe(w, c))
