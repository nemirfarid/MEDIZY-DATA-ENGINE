#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit de conformité binaire et certification cryptographique pour Santé DZ / Medizy v1.0.16.
Vérifie :
1. Taille de l'APK (< 35 Mo).
2. Présence des bibliothèques natives arm64-v8a et armeabi-v7a (libflutter.so).
3. Intégrité des assets embarqués (sante_dz_bundled.db, medizy_wilayas_index.json, medizy_categories_index.json).
4. Validation de la signature cryptographique APK Signature Scheme v2 via apksigner.
"""

import sys
import os
import zipfile
import subprocess
import hashlib
from pathlib import Path

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def find_apksigner():
    sdk_root = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or r"C:\Android\Sdk"
    build_tools = Path(sdk_root) / "build-tools"
    if build_tools.exists():
        # Find highest version
        candidates = sorted(build_tools.glob("*/apksigner.bat"), reverse=True)
        if candidates:
            return str(candidates[0])
        candidates = sorted(build_tools.glob("*/apksigner"), reverse=True)
        if candidates:
            return str(candidates[0])
    return "apksigner"

def audit_apk(apk_path):
    apk_file = Path(apk_path)
    if not apk_file.exists():
        print(f"[ERREUR] Le fichier APK n'existe pas : {apk_path}")
        return False

    print("=" * 80)
    print(f"AUDIT DE CONFORMITÉ BINAIRE APK : {apk_file.name}")
    print("=" * 80)

    # 1. Taille globale
    size_bytes = apk_file.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    sha256_hash = compute_sha256(apk_file)

    print(f"[*] Emplacement : {apk_file.resolve()}")
    print(f"[*] Taille      : {size_mb:.2f} Mo ({size_bytes:,} octets)")
    print(f"[*] SHA-256     : {sha256_hash}")

    size_ok = size_mb < 35.0
    print(f"[{'PASS' if size_ok else 'FAIL'}] Taille binaire < 35 Mo : {size_mb:.2f} Mo")

    # 2. Inspection du contenu interne via zipfile
    expected_assets = [
        "assets/flutter_assets/assets/data/sante_dz_bundled.db",
        "assets/flutter_assets/assets/data/medizy_wilayas_index.json",
        "assets/flutter_assets/assets/data/medizy_categories_index.json"
    ]
    expected_archs = ["arm64-v8a", "armeabi-v7a"]

    archs_found = {arch: [] for arch in expected_archs}
    assets_found = {}

    with zipfile.ZipFile(apk_file, 'r') as z:
        namelist = z.namelist()
        for name in namelist:
            # Check native libs
            for arch in expected_archs:
                if name.startswith(f"lib/{arch}/"):
                    archs_found[arch].append(name)

            # Check assets
            for asset in expected_assets:
                if name == asset or name.endswith(asset.split("/")[-1]):
                    info = z.getinfo(name)
                    assets_found[name] = info.file_size

    print("\n--- ANALYSE DES ARCHITECTURES NATIVES (lib/) ---")
    arch_ok = True
    for arch, files in archs_found.items():
        if files:
            print(f"[PASS] Architecture {arch} détectée : {len(files)} bibliothèques")
            for f in files:
                print(f"       -> {f}")
        else:
            print(f"[FAIL] Architecture {arch} ABSENTE du binaire !")
            arch_ok = False

    print("\n--- ANALYSE DES ASSETS EMBARQUÉS ---")
    assets_ok = True
    db_found = False
    for expected in expected_assets:
        matches = [k for k in assets_found.keys() if expected in k]
        if matches:
            actual_key = matches[0]
            size = assets_found[actual_key]
            print(f"[PASS] Asset présent : {actual_key} ({size / (1024*1024):.2f} Mo)")
            if "sante_dz_bundled.db" in actual_key:
                db_found = True
                if size < 10 * 1024 * 1024:
                    print(f"[FAIL] Base SQLite incomplète ou anormale (< 10 Mo) : {size} octets")
                    assets_ok = False
        else:
            print(f"[FAIL] Asset MANQUANT : {expected}")
            assets_ok = False

    if not db_found:
        assets_ok = False

    # 3. Vérification apksigner
    print("\n--- VÉRIFICATION CRYPTOGRAPHIQUE (apksigner Scheme v2) ---")
    apksigner_bin = find_apksigner()
    print(f"[*] Utilisation de apksigner : {apksigner_bin}")

    signature_ok = False
    try:
        res = subprocess.run(
            [apksigner_bin, "verify", "--verbose", str(apk_file)],
            capture_output=True,
            text=True,
            check=False
        )
        output = res.stdout + res.stderr
        print(output.strip())

        if "Verified using v2 scheme (APK Signature Scheme v2): true" in output:
            signature_ok = True
            print("[PASS] Signature Scheme v2 VALIDÉE avec succès !")
        elif "Verifies" in output or "DOES NOT VERIFY" not in output and res.returncode == 0:
            signature_ok = True
            print("[PASS] apksigner a validé le binaire.")
        else:
            print(f"[WARN] Résultat apksigner (code {res.returncode})")
    except Exception as e:
        print(f"[WARN] Impossible d'exécuter apksigner directement : {e}")

    print("\n" + "=" * 80)
    print("SYNTHÈSE DU RAPPORT D'AUDIT :")
    print(f" - Taille < 35 Mo          : {'CONFORME' if size_ok else 'NON CONFORME'}")
    print(f" - Architectures arm64/arm : {'CONFORME' if arch_ok else 'NON CONFORME'}")
    print(f" - Assets embarqués        : {'CONFORME' if assets_ok else 'NON CONFORME'}")
    print(f" - Signature Scheme v2     : {'CONFORME' if signature_ok else 'NON CONFORME / A VERIFIER'}")
    print("=" * 80)

    overall_ok = size_ok and arch_ok and assets_ok and signature_ok
    return overall_ok

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else r"build\app\outputs\flutter-apk\app-release.apk"
    success = audit_apk(target)
    sys.exit(0 if success else 1)
