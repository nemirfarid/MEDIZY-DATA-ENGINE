#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génération du registre cryptographique officiel SHA256SUMS_v1.0.16.txt
Pour la version Santé DZ / Medizy v1.0.16 (Release Client Intégrée).
"""

import datetime
import hashlib
import os

EXPORTS_DIR = r"D:\SANTE_DZ_EXPORTS"
MOBILE_DIR = r"D:\SANTE_DZ_EXPORTS\mobile"
ASSETS_DIR = r"D:\SANTE_DZ_EXPORTS\mobile\assets\data"
WORKSPACE_ASSETS = r"C:\SANTE_DZ_SCRAPER\assets\data"
OUTPUT_FILE = os.path.join(EXPORTS_DIR, "SHA256SUMS_v1.0.16.txt")


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def main():
    files = [
        # 1. Extractions multi-formats
        os.path.join(EXPORTS_DIR, "SANTE_DZ_NATIONAL_35832.csv"),
        os.path.join(EXPORTS_DIR, "sante_dz_full_dataset.json"),
        os.path.join(EXPORTS_DIR, "sante_dz_map_features.geojson"),
        os.path.join(EXPORTS_DIR, "SANTE_DZ_REGISTRE_NATIONAL.xlsx"),
        # 2. Package mobile D:\
        os.path.join(MOBILE_DIR, "medizy_national_cache.json.gz"),
        os.path.join(MOBILE_DIR, "sante_dz_db.json.gz"),
        os.path.join(MOBILE_DIR, "medizy_wilayas_index.json"),
        os.path.join(MOBILE_DIR, "medizy_categories_index.json"),
        os.path.join(MOBILE_DIR, "sante_dz_bundled.db"),
        # 3. Assets déployés D:\
        os.path.join(ASSETS_DIR, "sante_dz_db.json.gz"),
        os.path.join(ASSETS_DIR, "medizy_wilayas_index.json"),
        os.path.join(ASSETS_DIR, "medizy_categories_index.json"),
        os.path.join(ASSETS_DIR, "sante_dz_bundled.db"),
        # 4. Assets application cliente workspace
        os.path.join(WORKSPACE_ASSETS, "sante_dz_db.json.gz"),
        os.path.join(WORKSPACE_ASSETS, "medizy_wilayas_index.json"),
        os.path.join(WORKSPACE_ASSETS, "medizy_categories_index.json"),
        os.path.join(WORKSPACE_ASSETS, "sante_dz_bundled.db"),
    ]

    lines = []
    lines.append("# ==============================================================================")
    lines.append("# SANTÉ DZ / MEDIZY — REGISTRE OFFICIEL DES SOMMES DE CONTRÔLE SHA-256")
    lines.append("# Version : 1.0.16-client-integrated | Jalon : 35 832 Établissements (58 Wilayas)")
    lines.append(f"# Date de scellement : {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    lines.append("# ==============================================================================\n")

    for p in files:
        if os.path.exists(p):
            sha = compute_sha256(p)
            size = os.path.getsize(p)
            lines.append(f"{sha}  {p}  ({size:,} bytes)")
            print(f"Scellé : {os.path.basename(p)} -> {sha} ({size:,} octets)")
        else:
            print(f"[WARN] Fichier absent : {p}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n[SUCCÈS] Registre SHA-256 généré : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
