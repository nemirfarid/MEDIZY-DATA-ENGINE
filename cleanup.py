# -*- coding: utf-8 -*-
"""Nettoyage conservateur C: pour libérer de l'espace."""
import os, shutil

def free_gb(path):
    usage = shutil.disk_usage(path)
    return usage.free / (1024**3)

c_before = free_gb("C:\\")
print(f"C: libre AVANT : {c_before:.2f} Go")

errors = []
freed = 0

# 1. Vider Temp
temp = r"C:\Users\pc lenovo\AppData\Local\Temp"
if os.path.exists(temp):
    before = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(temp) for f in fs)
    try:
        for item in os.listdir(temp):
            p = os.path.join(temp, item)
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    os.remove(p)
            except Exception as e:
                errors.append(f"Temp/{item}: {e}")
        after = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(temp) for f in fs)
        freed += (before - after) / (1024**3)
        print(f"  Temp: {before/(1024**3):.2f} Go -> {after/(1024**3):.2f} Go")
    except Exception as e:
        errors.append(f"Temp: {e}")

# 2. Supprimer navigateurs Playwright
pw = r"C:\Users\pc lenovo\AppData\Local\ms-playwright"
for sub in ["chromium-1234", "chromium_headless_shell-1234", "ffmpeg-1011", "winldd-1007"]:
    p = os.path.join(pw, sub)
    if os.path.exists(p):
        before = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(p) for f in fs)
        try:
            shutil.rmtree(p, ignore_errors=True)
            freed += before / (1024**3)
            print(f"  Playwright/{sub}: {before/(1024**3):.2f} Go supprimé")
        except Exception as e:
            errors.append(f"Playwright/{sub}: {e}")

# 3. Vider NuGet
nuget = r"C:\Users\pc lenovo\AppData\Local\NuGet"
if os.path.exists(nuget):
    before = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(nuget) for f in fs)
    try:
        shutil.rmtree(nuget, ignore_errors=True)
        os.makedirs(nuget, exist_ok=True)
        freed += before / (1024**3)
        print(f"  NuGet: {before/(1024**3):.2f} Go supprimé")
    except Exception as e:
        errors.append(f"NuGet: {e}")

c_after = free_gb("C:\\")
d_free = free_gb("D:\\")
e_free = free_gb("E:\\")

print()
print(f"C: libre APRES : {c_after:.2f} Go")
print(f"D: libre : {d_free:.2f} Go")
print(f"E: libre : {e_free:.2f} Go")
print(f"Espace recuperé (calcule) : {freed:.2f} Go")
print(f"Reel (C apres - C avant) : {c_after - c_before:.2f} Go")
print()
if errors:
    print("ERREURS :")
    for e in errors:
        print(f"  - {e}")
else:
    print("AUCUNE ERREUR")