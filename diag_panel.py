"""Diagnostic : pourquoi le panneau de résultats est introuvable ?

Ouvre une page Google Maps pour une wilaya/catégorie donnée, capture le
contenu HTML et les sélecteurs présents, afin de distinguer :
  - page de consentement Google (consent)
  - CAPTCHA / trafic inhabituel
  - changement réel de DOM Maps (nouveau sélecteur de feed)
  - page vide / navigation ratée

Usage :
    python diag_panel.py "Boumerdès" "médecin"
    python diag_panel.py "El Tarf" "pharmacie"
"""
import asyncio
import sys
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

OUT_DIR = Path(r"D:\SANTE_DZ_EXPORTS\diagnostics")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def slug(text):
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -_":
            keep.append("-")
    return "".join(keep).strip("-") or "x"


async def diagnose(wilaya: str, categorie: str, headless: bool = True):
    query = f"{categorie} {wilaya} Algérie"
    url = "https://www.google.com/maps/search/" + quote(query) + "?hl=fr&gl=DR"

    launch_kwargs = {"headless": headless, "slow_mo": 0}
    system_chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if system_chrome.exists():
        launch_kwargs["executable_path"] = str(system_chrome)

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            locale="fr-FR",
            timezone_id="Africa/Algiers",
            viewport={"width": 1440, "height": 1000},
        )
        # Cookie de consentement : évite la page interstitial bloquante
        await context.add_cookies([
            {"name": "CONSENT", "value": "YES+cb.20220310-17-p0.en+FX+111",
             "domain": ".google.com", "path": "/"},
            {"name": "SOCS", "value": "CAESHAgBEhIaAB",
             "domain": ".google.com", "path": "/"},
        ])
        page = await context.new_page()

        print("URL :", url)
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("HTTP status :", resp.status if resp else "n/a")
        except Exception as e:
            print("ERREUR navigation :", type(e).__name__, e)

        await page.wait_for_timeout(4000)

        title = await page.title()
        final_url = page.url
        html = await page.content()

        print("Titre      :", title[:160])
        print("URL finale :", final_url[:200])
        print("Longueur HTML :", len(html))

        low = html.lower()
        marqueurs = {
            "consent": ["consent", "conditions d'utilisation", "before you continue"],
            "captcha": ["captcha", "recaptcha", "unusual traffic", "verify you are human",
                        "automated queries", "not a robot"],
            "rate_limit": ["429", "too many requests", "rate limit"],
            "no_result": ["aucun résultat", "no results", "找不到", "did not match"],
        }
        for nom, mots in marqueurs.items():
            trouve = [m for m in mots if m in low]
            print(f"Marqueur {nom:10s} : {trouve if trouve else 'ABSENT'}")

        # Sélecteurs de feed / résultats
        selecteurs = {
            'div[role="feed"]': 'div[role="feed"]',
            'div[role="article"]': 'div[role="article"]',
            'div[role="region"]': 'div[role="region"]',
            'input[aria-label*="Rechercher"]': 'input[aria-label*="Rechercher"]',
            'input[aria-label*="Search"]': 'input[aria-label*="Search"]',
            "searchbox": '[role="searchbox"]',
            "canvas": "canvas",
            "iframe": "iframe",
        }
        print("\nSélecteurs présents :")
        for libelle, sel in selecteurs.items():
            try:
                n = await page.locator(sel).count()
            except Exception:
                n = -1
            print(f"  {libelle:34s} -> {n}")

        # Les 15 premiers liens de fiche Maps détectés
        liens = await page.evaluate("""
            () => {
                const out = [];
                document.querySelectorAll('a[href*="/maps/place/"]').forEach(a => {
                    out.push(a.getAttribute('href'));
                    if (out.length >= 15) return;
                });
                return out;
            }
        """)
        print(f"\nLiens /maps/place/ trouvés : {len(liens)}")
        for l in liens[:10]:
            print("   ", (l or "")[:110])

        nom_fichier = OUT_DIR / f"panel_{slug(wilaya)}_{slug(categorie)}.html"
        nom_fichier.write_text(html, encoding="utf-8", errors="replace")
        print("\nHTML sauvegardé :", nom_fichier)

        await context.close()
        await browser.close()


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "Boumerdès"
    c = sys.argv[2] if len(sys.argv) > 2 else "médecin"
    headless = "--visible" not in sys.argv
    asyncio.run(diagnose(w, c, headless=headless))
