import asyncio, re, sys, time
from pathlib import Path
from urllib.parse import quote
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from config import WILAYAS, CATEGORIES

OUT = Path("output"); OUT.mkdir(exist_ok=True)

def clean(x): return re.sub(r"\s+", " ", x or "").strip()

def phone_from_text(s):
    m = re.search(r"(?:\+213|00213|0)?[\s.-]?(5|6|7)[\s.-]?\d{2}[\s.-]?\d{3}[\s.-]?\d{2}", s or "")
    return clean(m.group(0)) if m else ""

def gps_from_url(url):
    for p in (r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)"):
        m = re.search(p, url or "")
        if m: return m.group(1), m.group(2)
    return "", ""

async def scroll_feed(page):
    last = -1
    for _ in range(35):
        feed = page.locator('div[role="feed"]')
        if await feed.count():
            await feed.evaluate("(e)=>e.scrollTo(0,e.scrollHeight)")
        else:
            await page.mouse.wheel(0, 5000)
        await page.wait_for_timeout(1100)
        n = await page.locator('div[role="feed"] a[href*="/maps/place/"]').count()
        if n == last:
            await page.wait_for_timeout(1800)
            n2 = await page.locator('div[role="feed"] a[href*="/maps/place/"]').count()
            if n2 == n: break
        last = n

async def extract(page, wilaya, category):
    out=[]
    links=page.locator('div[role="feed"] a[href*="/maps/place/"]')
    for i in range(await links.count()):
        try:
            a=links.nth(i); href=await a.get_attribute("href") or ""
            card=a.locator("xpath=ancestor::div[contains(@class,'Nv2PK')][1]")
            if not await card.count(): card=a.locator("xpath=..")
            text=clean(await card.inner_text())
            lines=[clean(x) for x in text.split("\n") if clean(x)]
            if not lines: continue
            name=lines[0]
            rating=""; reviews=""
            m=re.search(r"([0-5](?:[.,]\d)?)\s*\(([\d\s.,]+)\)", text)
            if m:
                rating=m.group(1).replace(",","."); reviews=re.sub(r"\D","",m.group(2))
            phone=phone_from_text(text)
            lat,lon=gps_from_url(href)
            address=""
            for x in lines[1:]:
                if len(x)>8 and not re.match(r"^[0-5](?:[.,]\d)?\s*\(",x) and not phone_from_text(x):
                    address=x; break
            out.append({
                "wilaya_code":wilaya[0],"wilaya":wilaya[1],
                "categorie_recherche":category,"nom":name,"adresse":address,
                "telephone":phone,"note":rating,"nombre_avis":reviews,
                "latitude":lat,"longitude":lon,"google_maps_url":href,
                "source":"Google Maps - données visibles dans le navigateur"
            })
        except Exception: pass
    return out

async def one(page,w,c):
    url="https://www.google.com/maps/search/"+quote(f"{c} {w[1]}, Algérie")+"?hl=fr"
    try:
        await page.goto(url,wait_until="domcontentloaded",timeout=60000)
        await page.wait_for_timeout(2500)
        await scroll_feed(page)
        return await extract(page,w,c)
    except PlaywrightTimeoutError:
        print("TIMEOUT:",w[1],c)
    except Exception as e:
        print("ERREUR:",w[1],c,e)
    return []

async def main():
    target=sys.argv[1].strip().lower() if len(sys.argv)>1 else ""
    ws=[w for w in WILAYAS if not target or w[1].lower()==target]
    if not ws:
        print("Wilaya inconnue. Exemple: python scraper.py Mostaganem"); return
    rows=[]; t=time.time()
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=False)
        context=await browser.new_context(locale="fr-FR",viewport={"width":1440,"height":900})
        page=await context.new_page()
        for wi,w in enumerate(ws,1):
            print(f"\n=== {wi}/{len(ws)} {w[1]} ===")
            for ci,c in enumerate(CATEGORIES,1):
                print(f"{ci}/{len(CATEGORIES)} {c}")
                rows += await one(page,w,c)
                pd.DataFrame(rows).to_csv(OUT/"checkpoint.csv",index=False,encoding="utf-8-sig")
                await page.wait_for_timeout(1200)
        await browser.close()
    df=pd.DataFrame(rows)
    if df.empty: print("Aucune donnée."); return
    df["key_url"]=df.google_maps_url.fillna("").str.split("?").str[0]
    df["key_name"]=(df.nom.fillna("").str.lower().str.replace(r"\s+"," ",regex=True).str.strip()+"|"+
                    df.adresse.fillna("").str.lower().str.replace(r"\s+"," ",regex=True).str.strip())
    df["key"]=df.key_url.where(df.key_url.ne(""),df.key_name)
    df=df.drop_duplicates("key").drop(columns=["key_url","key_name","key"])
    df=df.sort_values(["wilaya_code","nom"],kind="stable")
    stats=df.groupby(["wilaya_code","wilaya"],as_index=False).size().rename(columns={"size":"fiches"})
    miss=pd.DataFrame({"champ":["nom","adresse","telephone","note","nombre_avis","latitude","longitude","google_maps_url"],
                       "manquants":[int(df[c].fillna("").eq("").sum()) for c in ["nom","adresse","telephone","note","nombre_avis","latitude","longitude","google_maps_url"]]})
    out=OUT/"SANTE_DZ_GOOGLE_MAPS_NATIONAL.xlsx"
    with pd.ExcelWriter(out,engine="openpyxl") as x:
        df.to_excel(x,"professionnels",index=False); stats.to_excel(x,"stats_wilayas",index=False); miss.to_excel(x,"champs_manquants",index=False)
    print(f"\nTERMINE: {len(df)} fiches uniques")
    print("EXCEL:",out.resolve())
    print(f"Duree: {(time.time()-t)/60:.1f} min")

if __name__=="__main__": asyncio.run(main())
