# MEDIZY — export national des structures de santé (2026-11-03)

Fichier : `medizy_algeria_health_directory_2026-11-03.csv`

## Contenu réellement obtenu
- 1 915 structures de soins de proximité / cliniques (OpenStreetMap).
- 3 811 pharmacies (OpenStreetMap).
- 640 établissements publics de santé après dédoublonnage conservateur (registre du ministère republié par GeoAlgeria).
- **Total exporté : 6 366 enregistrements distincts selon les clés disponibles.**

## Limites importantes
- Ce fichier n'atteint pas 45 000 lignes.
- Il s'agit d'un répertoire de structures, pas d'un annuaire exhaustif de médecins/personnes physiques. Aucun praticien individuel n'a été inventé ni ajouté sans source nominative vérifiable.
- Téléphones, adresses et spécialités restent vides lorsqu'ils ne sont pas publiés dans la source.
- La présence dans OpenStreetMap ne garantit pas à elle seule que l'établissement est encore ouvert.
- Aucun enregistrement de la base MEDIZY de production n'a été lu, modifié ou remplacé.

## Dédoublonnage
- Identifiants OSM / MSP lorsqu'ils sont disponibles.
- Sinon, rapprochement prudent par nom normalisé, wilaya et coordonnées arrondies.
- Les doublons ambigus ne sont pas supprimés automatiquement dans la base de production.

## Sources et licences
- `@geoalgeria/cliniques` — OpenStreetMap, ODbL.
- `@geoalgeria/pharmacies` — OpenStreetMap, ODbL.
- `@geoalgeria/sante` — registre public du ministère republié par GeoAlgeria ; consulter la licence et les conditions de réutilisation du paquet source.

Sources : https://geoalgeria.com/data ; https://geoalgeria.com/fr/data/docs/cliniques
Date de récupération de l'export : 2026-11-03.
