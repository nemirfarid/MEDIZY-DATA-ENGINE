"""Sonde : libellés (aria-label) d'une page de lieu unique, pour calibrer
l'extraction adresse / téléphone / type.

Usage : python diag_labels.py "Boumerdès" "centre de santé"
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

        print("URL finale :", page.url[:160])
        print("Page lieu  :", "/maps/place/" in page.url)

        labels = await page.evaluate("""
            () => {
                const out = [];
                document.querySelectorAll('button[aria-label], a[aria-label]')
                    .forEach(el => {
                        const a = el.getAttribute('aria-label');
                        if (a && a.length > 2) out.push([el.tagName, a]);
                    });
                return out;
            }
        """)
        print("\nLibellés :")
        for tag, lbl in labels:
            print(f"  [{tag}] {lbl[:120]}")

        # Zone d'adresse : texte du panneau, pour repère
        try:
            addr_btn = page.locator("button[aria-label*='Adresse']").first
            if await addr_btn.count():
                print("\nBouton adresse.inner_text :",
                      repr((await addr_btn.inner_text())[:120]))
        except Exception:
            pass

        await ctx.close()
        await browser.close()


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "Boumerdès"
    c = sys.argv[2] if len(sys.argv) > 2 else "centre de santé"
    asyncio.run(probe(w, c))
