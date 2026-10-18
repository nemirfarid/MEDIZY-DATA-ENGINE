"""Validation de parse_single_place_page sur plusieurs cas.

Vérifie que les champs extraits sont plausibles et qu'aucune valeur
factice (bouton d'action, texte d'UI) ne se glisse dans les données.

Usage : python test_single_place.py
"""
import asyncio
import sys
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

import scraper

CAS = [
    ("Boumerdès", "polyclinique"),
    ("Boumerdès", "centre de santé"),
    ("Boumerdès", "sage-femme"),
    ("Boumerdès", "centre d'imagerie médicale"),
    ("Boumerdès", "orthophoniste"),
    ("Tipaza", "dentiste"),
    ("Mila", "pédiatre"),
    ("Tissemsilt", "pharmacie"),
]

# Termes qui ne doivent JAMAIS apparaître comme valeur de donnée.
INTERDITS = ["copier l'adresse", "présentation", "menu", "fermer", "rechercher",
             "partager", "enregistrer", "itinéraire", "se connecter",
             "à propos de ces données", "réduire le panneau"]


async def main():
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    kw = {"headless": True}
    if chrome.exists():
        kw["executable_path"] = str(chrome)

    ok, ko = 0, 0
    async with async_playwright() as p:
        browser = await p.chromium.launch(**kw)
        ctx = await browser.new_context(locale="fr-FR", timezone_id="Africa/Algiers",
                                        viewport={"width": 1440, "height": 1000})
        await ctx.add_cookies([
            {"name": "CONSENT", "value": "YES+cb.20220310-17-p0.en+FX+111",
             "domain": ".google.com", "path": "/"},
            {"name": "SOCS", "value": "CAESHAgBEhIaAB", "domain": ".google.com", "path": "/"},
        ])
        page = await ctx.new_page()

        for wilaya, cat in CAS:
            url = "https://www.google.com/maps/search/" + quote(f"{cat} {wilaya} Algérie") + "?hl=fr&gl=DR"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000)
            except Exception as e:
                print(f"[ERREUR NAV] {wilaya}/{cat} : {type(e).__name__}")
                ko += 1
                continue

            r = await scraper.parse_single_place_page(page, wilaya, cat)
            print(f"\n--- {wilaya} / {cat}")
            if r is None:
                print("    (pas de page lieu unique — feed normal attendu)")
                continue

            problemes = []
            for champ in ("nom", "adresse", "type_google", "telephone"):
                val = (r.get(champ) or "").strip()
                low = val.lower()
                for terme in INTERDITS:
                    if low == terme or low.startswith(terme + ":") or low == terme + ":":
                        problemes.append(f"{champ}={val!r} contient un terme d'UI")
                print(f"    {champ:12s}: {val[:80]!r}")

            # Cohérence : tout résultat doit avoir un nom et des GPS
            if not r["nom"]:
                problemes.append("nom vide")
            if r["latitude"] is None or r["longitude"] is None:
                problemes.append("GPS manquants")
            if r["telephone"] and not any(ch.isdigit() for ch in r["telephone"]):
                problemes.append("téléphone sans chiffre")

            if problemes:
                ko += 1
                print("    !! PROBLEMES :", problemes)
            else:
                ok += 1
                print("    OK")

        await ctx.close()
        await browser.close()

    print(f"\n===== {ok} conformes, {ko} en défaut =====")
    return 0 if ko == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
