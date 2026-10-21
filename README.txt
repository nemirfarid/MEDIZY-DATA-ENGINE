SANTE DZ — SCRAPER NATIONAL

1) Ouvrir CMD :
   cd /d C:\SANTE_DZ_SCRAPER

2) Activer l'environnement :
   .venv\Scripts\activate

3) Installer :
   python -m pip install -r requirements.txt
   python -m playwright install chromium

4) TEST MOSTAGANEM :
   python scraper.py --wilaya Mostaganem --max-results 80 --visible

5) NATIONAL :
   python scraper.py --all --max-results 80 --visible

Les fichiers sont dans :
   C:\SANTE_DZ_SCRAPER\exports\

Le fichier principal :
   SANTE_DZ_GOOGLE_MAPS_NATIONAL.xlsx

Le scraper sauvegarde progressivement :
   exports\checkpoint.csv

Si la fenêtre Google Maps s'arrête ou si tu interromps avec CTRL+C,
relance la même commande : les données déjà présentes dans checkpoint.csv
sont conservées et fusionnées.
