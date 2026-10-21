# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from taxonomie_specialites import SPECIALITES
from scraper import CATEGORIES

print('Categories dans scraper.py:', len(CATEGORIES))
for i, c in enumerate(CATEGORIES, 1):
    print('  %2d. %s' % (i, c))

print()
print('Specialites dans taxonomie:', len(SPECIALITES))
for i, s in enumerate(SPECIALITES, 1):
    print('  %2d. %-10s -> %s' % (i, s['code'], s['specialite']))
