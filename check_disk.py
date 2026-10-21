# -*- coding: utf-8 -*-
"""Check disk cleanup targets."""
import subprocess, os

targets = [
    r"C:\Users\pc lenovo\AppData\Local\Temp",
    r"C:\Windows\Temp",
    r"C:\Users\pc lenovo\AppData\Local\ms-playwright\chromium-1234",
    r"C:\Users\pc lenovo\AppData\Local\Package Cache",
    r"C:\Users\pc lenovo\AppData\Local\Microsoft\Windows\INetCache",
    r"C:\Users\pc lenovo\AppData\Roaming\npm-cache",
    r"C:\Users\pc lenovo\AppData\Local\Microsoft\VSCode\extensions",
    r"C:\Users\pc lenovo\AppData\Local\Programs\Microsoft VS Code",
    r"C:\Windows\SoftwareDistribution\DeliveryOptimization",
    r"C:\Users\pc lenovo\AppData\Local\NuGet",
    r"C:\Users\pc lenovo\AppData\Local\ms-playwright\winldd-1007",
    r"C:\Users\pc lenovo\AppData\Local\ms-playwright\chromium_headless_shell-1234",
    r"C:\Users\pc lenovo\AppData\Local\ms-playwright\ffmpeg-1011",
]

for t in targets:
    if os.path.exists(t):
        total = 0
        for root, dirs, files in os.walk(t):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
        print(f"{'YES':4s} {t:70s} {total/1024/1024:10.2f} MB")
    else:
        print(f"{'NO':4s} {t:70s} {'-':>10s}")