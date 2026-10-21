#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 6: MIPH PDF parsing + DB cross-reference with improved matching.
"""
import csv
import re
import sqlite3
import unicodedata
from pathlib import Path
from collections import Counter

BASE = Path(r"C:\SANTE_DZ_SCRAPER")
TXT_PATH = BASE / "etablissements_sante_2025.txt"
EXPORTS = Path(r"D:\SANTE_DZ_EXPORTS")
EXPORTS.mkdir(exist_ok=True)

WILAYA_CODE_TO_NAME = {
    "01": "Adrar", "02": "Chlef", "03": "Laghouat", "04": "Oum El Bouaghi",
    "05": "Batna", "06": "Béjaïa", "07": "Biskra", "08": "Béchar",
    "09": "Blida", "10": "Bouira", "11": "Tamanrasset", "12": "Tébessa",
    "13": "Tlemcen", "14": "Tiaret", "15": "Tizi Ouzou", "16": "Alger",
    "17": "Djelfa", "18": "Jijel", "19": "Sétif", "20": "Saïda",
    "21": "Skikda", "22": "Sidi Bel Abbès", "23": "Annaba", "24": "Guelma",
    "25": "Constantine", "26": "Médéa", "27": "Mostaganem", "28": "M'Sila",
    "29": "Mascara", "30": "Ouargla", "31": "Oran", "32": "El Bayadh",
    "33": "Illizi", "34": "Bordj Bou Arréridj", "35": "Boumerdès",
    "36": "El Tarf", "37": "Tindouf", "38": "Tissemsilt", "39": "El Oued",
    "40": "Khenchela", "41": "Souk Ahras", "42": "Tipaza", "43": "Mila",
    "44": "Aïn Defla", "45": "Naâma", "46": "Aïn Témouchent",
    "47": "Ghardaïa", "48": "Relizane", "49": "Timimoun",
    "50": "Bordj Badji Mokhtar", "51": "Ouled Djellal", "52": "Béni Abbès",
    "53": "In Salah", "54": "In Guezzam", "55": "Touggourt", "56": "Djanet",
    "57": "El M'Ghair", "58": "El Meniaa",
}

# French stopwords for fuzzy matching
STOPWORDS = {"de", "la", "le", "des", "et", "du", "l", "d", "en", "el", "aux", "les", "une", "un", "pour",
             "public", "public", "", "et", "ou", "au", "aux", "dans", "sur", "à", "à", "par", "avec"}


def normalize(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    # Remove Arabic
    s = re.sub(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+", "", s)
    # Remove accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Remove punctuation, collapse spaces
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def token_set(s: str):
    """Extract normalized non-stopword tokens from a string."""
    norm = normalize(s)
    tokens = [t for t in norm.split() if t not in STOPWORDS and len(t) > 2]
    return set(tokens)


def jaccard(tokens_a, tokens_b):
    """Jaccard similarity between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def parse_pdf_text():
    content = TXT_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("--- Page") or line.startswith("id type_etab"):
            continue
        parts = line.split()
        if len(parts) < 4 or not re.match(r"^\d+$", parts[0]):
            continue
        entry_id = parts[0]
        type_etab = parts[1]
        numeric_positions = [i for i, p in enumerate(parts) if re.match(r"^\d+$", p)]
        if len(numeric_positions) < 2:
            continue
        wilaya_code = parts[numeric_positions[-2]]
        code_postal = parts[numeric_positions[-1]]

        arabic_pattern = re.compile(r"[\u0600-\u06FF]")
        arabic_match = arabic_pattern.search(line)
        if arabic_match:
            arabic_start = arabic_match.start()
            prefix = line[:arabic_start]
            prefix_parts = prefix.split()
            etab_fr = " ".join(prefix_parts[2:]) if len(prefix_parts) > 2 else ""
            arabic_and_nums = line[arabic_start:]
            arabic_tokens = arabic_and_nums.split()
            etab_ar = " ".join(arabic_tokens[:-2]) if len(arabic_tokens) > 2 else ""
        else:
            text_parts = parts[2:numeric_positions[-2]]
            etab_fr = " ".join(text_parts).strip()
            etab_ar = ""

        etab_fr = etab_fr.strip()
        wilaya_name = WILAYA_CODE_TO_NAME.get(wilaya_code, f"WilayaCode_{wilaya_code}")
        if not WILAYA_CODE_TO_NAME.get(wilaya_code) and len(wilaya_code) == 1:
            wilaya_name = WILAYA_CODE_TO_NAME.get(f"0{wilaya_code}", f"WilayaCode_{wilaya_code}")

        entries.append({
            "id": entry_id,
            "type_etab": type_etab,
            "etab": etab_fr,
            "etab_ar": etab_ar,
            "wilaya_code": wilaya_code,
            "wilaya": wilaya_name,
            "code_postal": code_postal,
        })
    return entries


def map_type_etab(type_etab):
    mapping = {
        "DSP": "Direction de Santé",
        "CHU": "hôpital",
        "EPH": "hôpital",
        "EH": "hôpital",
        "EHS": "clinique",
        "EPSP": "centre de santé",
        "INFSPM": "Institut de formation",
        "INFSSF": "Institut de formation",
        "EST": "Institut de formation",
        "INFPM": "Institut de formation",
        "DRH": "Direction",
        "Structure": "Structure",
        "EHU": "hôpital",
        "EFPM": "Institut de formation",
    }
    return mapping.get(type_etab, type_etab)


def load_db_entries():
    conn = sqlite3.connect(str(BASE / "medizy_scraper.db"))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom, nom_normalized, wilaya, adresse, telephone, site_web, note,
               latitude, longitude, categorie_recherche, source, place_id,
               type_google, commune
        FROM places
        WHERE status = 'active' AND name_status != 'CANDIDATE'
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Build exact lookup (normalized name)
    exact_lookup = {}
    for r in rows:
        nom_norm = (r.get("nom_normalized") or "").strip()
        if nom_norm:
            exact_lookup.setdefault(nom_norm, []).append(r)

    # Build token-set lookup for partial matching (with index)
    token_index = {}  # token -> list of (row_dict, tokenset)
    for r in rows:
        tokens = token_set(r.get("nom") or "")
        for t in tokens:
            token_index.setdefault(t, []).append((r, tokens))

    return {
        "rows": rows,
        "exact_lookup": exact_lookup,
        "token_index": token_index,
    }


def cross_reference_db(entries, db_data):
    exact_lookup = db_data["exact_lookup"]
    token_index = db_data["token_index"]

    results = {
        "total_pdf": len(entries),
        "exact_match": 0,
        "partial_match": 0,
        "no_match": 0,
        "matched": [],
        "new_entities": [],
        "by_type": {},
        "by_wilaya": {},
    }

    JACCARD_THRESHOLD = 0.35  # Require 35% token overlap

    for entry in entries:
        t = entry["type_etab"]
        results["by_type"].setdefault(t, 0)
        results["by_type"][t] += 1
        w = entry["wilaya"]
        results["by_wilaya"].setdefault(w, 0)
        results["by_wilaya"][w] += 1

        etab = entry["etab"]
        nom_norm = normalize(etab)

        # 1. Exact normalized match
        if nom_norm in exact_lookup:
            db_row = exact_lookup[nom_norm][0]
            results["exact_match"] += 1
            results["matched"].append(_match_entry(entry, db_row, "exact"))
            continue

        # 2. Token-based partial match (Jaccard similarity)
        pdf_tokens = token_set(etab)
        if not pdf_tokens:
            # Very short name, try direct substring
            pdf_tokens = set(etab.lower().split())

        # Find candidate DB rows that share at least one token
        candidates = {}  # nom -> (db_row, db_tokens)
        for token in pdf_tokens:
            if token in token_index:
                for db_row, db_tokens in token_index[token]:
                    if db_row["nom"] not in candidates:
                        candidates[db_row["nom"]] = (db_row, db_tokens)

        best_score = 0
        best_db_row = None
        for nom, (db_row, db_tokens) in candidates.items():
            score = jaccard(pdf_tokens, db_tokens)
            if score > best_score:
                best_score = score
                best_db_row = db_row

        if best_db_row and best_score >= JACCARD_THRESHOLD:
            results["partial_match"] += 1
            results["matched"].append(_match_entry(entry, best_db_row, "partial"))
            continue

        # 3. No match
        results["no_match"] += 1
        results["new_entities"].append({
            "pdf_id": entry["id"],
            "type_etab": t,
            "etab_fr": etab,
            "etab_ar": entry["etab_ar"],
            "wilaya": entry["wilaya"],
            "wilaya_code": entry["wilaya_code"],
            "code_postal": entry["code_postal"],
            "type_mapped": map_type_etab(t),
        })

    return results


def _match_entry(entry, db_row, status):
    return {
        "pdf_id": entry["id"],
        "type_etab": entry["type_etab"],
        "etab_fr": entry["etab"],
        "etab_ar": entry["etab_ar"],
        "wilaya": entry["wilaya"],
        "code_postal": entry["code_postal"],
        "db_nom": db_row.get("nom", ""),
        "db_wilaya": db_row.get("wilaya", ""),
        "db_adresse": db_row.get("adresse", ""),
        "db_telephone": db_row.get("telephone", ""),
        "db_site_web": db_row.get("site_web", ""),
        "db_note": db_row.get("note", ""),
        "db_source": db_row.get("source", ""),
        "db_categorie": db_row.get("categorie_recherche", ""),
        "db_place_id": db_row.get("place_id", ""),
        "db_commune": db_row.get("commune", ""),
        "match_status": status,
    }


def write_outputs(results):
    matched_path = EXPORTS / "miph_crossref_matched.csv"
    with open(matched_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "pdf_id", "type_etab", "etab_fr", "etab_ar", "wilaya", "code_postal",
            "db_nom", "db_wilaya", "db_adresse", "db_telephone", "db_site_web",
            "db_note", "db_source", "db_categorie", "db_place_id", "db_commune", "match_status"
        ])
        writer.writeheader()
        for r in results["matched"]:
            writer.writerow(r)

    new_path = EXPORTS / "miph_crossref_new.csv"
    with open(new_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "pdf_id", "type_etab", "etab_fr", "etab_ar", "wilaya", "wilaya_code",
            "code_postal", "type_mapped"
        ])
        writer.writeheader()
        for r in results["new_entities"]:
            writer.writerow(r)

    # Also write full parsed PDF dataset
    all_path = EXPORTS / "miph_parsed_all.csv"
    with open(all_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "type_etab", "etab", "etab_ar", "wilaya_code", "wilaya", "code_postal"
        ])
        writer.writeheader()
        for e in results.get("_parsed_entries", []):
            writer.writerow(e)

    print(f"Matched (exact+partial): {matched_path} ({len(results['matched'])})")
    print(f"New/unmatched:           {new_path} ({len(results['new_entities'])})")
    print(f"Full parsed PDF data:    {all_path}")


def main():
    print("Phase 6: MIPH PDF source parsing + DB cross-reference (v2)")
    print("=" * 65)

    entries = parse_pdf_text()
    print(f"Parsed {len(entries)} establishment entries from PDF")

    print("Loading DB entries into memory...")
    db_data = load_db_entries()
    print(f"DB loaded: {len(db_data['rows'])} active entries")

    print("Cross-referencing...")
    results = cross_reference_db(entries, db_data)
    results["_parsed_entries"] = entries

    print(f"\nResults:")
    print(f"  Exact matches:    {results['exact_match']}")
    print(f"  Partial matches:  {results['partial_match']}")
    print(f"  New (no match):   {results['no_match']}")

    print(f"\nBy type_etab:")
    for t, c in sorted(results["by_type"].items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Data quality analysis
    matched = results["matched"]
    missing_addr = sum(1 for r in matched if not r["db_adresse"] or r["db_adresse"] == "-")
    missing_phone = sum(1 for r in matched if not r["db_telephone"] or r["db_telephone"] == "-")
    missing_site = sum(1 for r in matched if not r["db_site_web"])
    missing_note = sum(1 for r in matched if not r["db_note"] or r["db_note"] == "-")

    print(f"\nFields missing in matched DB entries (enrichment opportunity):")
    print(f"  Address:    {missing_addr}/{len(matched)} ({100*missing_addr/len(matched):.1f}%)")
    print(f"  Phone:      {missing_phone}/{len(matched)} ({100*missing_phone/len(matched):.1f}%)")
    print(f"  Website:    {missing_site}/{len(matched)} ({100*missing_site/len(matched):.1f}%)")
    print(f"  Note:       {missing_note}/{len(matched)} ({100*missing_note/len(matched):.1f}%)")

    miph_missing_postal = sum(1 for r in matched if r["code_postal"] == "0")
    total_postal = sum(1 for e in entries if e["code_postal"] != "0")
    print(f"\nMIPH data quality:")
    print(f"  Entries with postal code: {total_postal}/{len(entries)}")
    print(f"  Entries with postal=0 (missing): {len(entries) - total_postal}")

    write_outputs(results)
    print("\nDone.")


if __name__ == "__main__":
    main()
