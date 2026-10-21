import os
import sys
import json
import time
import urllib.request
import urllib.error

OUTPUT_FILE = r"D:\SANTE_DZ_EXPORTS\1sante_raw_listings.json"
MAX_PAGES = 70  # 70 * 50 = 3500 entries
PER_PAGE = 50

existing_entries = []
if os.path.exists(OUTPUT_FILE):
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing_entries = json.load(f)
        print(f"Existing entries in {OUTPUT_FILE}: {len(existing_entries)}")
    except Exception as e:
        print(f"Could not read existing file: {e}")

existing_ids = set(item.get("id") for item in existing_entries if isinstance(item, dict) and item.get("id"))

start_page = (len(existing_entries) // PER_PAGE) + 1
print(f"Starting fetch from page {start_page} up to {MAX_PAGES}...")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

all_listings = list(existing_entries)

for page in range(start_page, MAX_PAGES + 1):
    url = f"https://www.1sante.com/online/wp-json/directorist/v1/listings?per_page={PER_PAGE}&page={page}"
    success = False
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not data or not isinstance(data, list):
                    print(f"Page {page}: Empty or invalid response. Stopping.")
                    success = True
                    break
                added = 0
                for item in data:
                    if item.get("id") and item["id"] not in existing_ids:
                        all_listings.append(item)
                        existing_ids.add(item["id"])
                        added += 1
                print(f"Page {page}/{MAX_PAGES}: fetched {len(data)} items (+{added} new). Total now: {len(all_listings)}", flush=True)
                success = True
                break
        except urllib.error.HTTPError as e:
            if e.code == 400: # past end of pages
                print(f"Page {page}: HTTP 400 end of pages.")
                success = True
                break
            print(f"Page {page} attempt {attempt+1} HTTP error {e.code}: {e}")
            time.sleep(2)
        except Exception as e:
            print(f"Page {page} attempt {attempt+1} error: {e}")
            time.sleep(2)
            
    if not success:
        print(f"Page {page}: Failed after 3 attempts.")
        break
        
    # Save checkpoint every 10 pages
    if page % 10 == 0:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_listings, f, ensure_ascii=False)
        print(f"[CHECKPOINT] Saved {len(all_listings)} listings to {OUTPUT_FILE}", flush=True)

    time.sleep(0.5)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_listings, f, ensure_ascii=False)

print(f"COMPLETED. Final total listings in {OUTPUT_FILE}: {len(all_listings)}")
