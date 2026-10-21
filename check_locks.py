# -*- coding: utf-8 -*-
"""Check if files are locked by running processes."""
import subprocess, os

# Check for any process using Playwright browsers or Temp files
r = subprocess.run(
    ["wmic", "process", "get", "processid,commandline"],
    capture_output=True, text=True, timeout=15
)
out = r.stdout.lower()
print("=== Processus actifs ===")
for line in out.splitlines():
    if any(k in line for k in ["playwright", "chrom", "scraper", "python"]):
        print(" ", line[:200])

# Check if Temp files are locked
print()
print("=== Vérification verrous sur Temp ===")
temp_dir = r"C:\Users\pc lenovo\AppData\Local\Temp"
for f in os.listdir(temp_dir):
    p = os.path.join(temp_dir, f)
    if os.path.isfile(p):
        print(f"  {f} : {os.path.getsize(p)/1024/1024:.2f} MB")

# Check NuGet cache
print()
print("=== NuGet cache ===")
nuget = r"C:\Users\pc lenovo\AppData\Local\NuGet"
if os.path.exists(nuget):
    total = 0
    for root, dirs, files in os.walk(nuget):
        for fn in files:
            total += os.path.getsize(os.path.join(root, fn))
    print(f"  Taille: {total/1024/1024:.2f} MB")