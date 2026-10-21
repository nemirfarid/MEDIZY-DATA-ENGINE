#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sauvegarde sécurisée de la production medizy_scraper.db"""
import os, shutil, hashlib
from datetime import datetime

PROD = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
BACKUP_DIR = r"C:\SANTE_DZ_SCRAPER\backups"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1048576), b""):
            h.update(c)
    return h.hexdigest()

def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, "medizy_scraper_backup_pre_merge_" + ts + ".db")
    shutil.copy2(PROD, dest)
    print("Backup created:", dest)
    print("Size:", os.path.getsize(dest))
    print("PROD SHA256: ", sha256(PROD))
    print("BACKUP SHA256:", sha256(dest))

if __name__ == "__main__":
    main()
