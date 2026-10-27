# MEDIZY — Dictionnaire & Guide Médical Algérie

Application mobile souveraine d'orientation sanitaire, annuaire national, pharmacopée DCI et géolocalisation d'urgence 100% hors-ligne.

## Kit de Déploiement & Distribution Terrain

* **Version livrée** : `v1.4.0-dci-whatsapp` (Tag officiel de production)
* **Volume de données** : **36 417 fiches** qualifiées réparties sur les **58 wilayas** d'Algérie + **Index FTS5 DCI & Médicaments algériens**.
* **Binaire autonome** : `dist/Medizy-v1.4.0-National-Release.apk` (26,24 Mo).
* **Empreinte de contrôle SHA-256** : `9b116721b6fae8b5f86943c60b4aa58d633f1d2aa2fa60f345e3d866481e9fec` (voir `dist/checksums.txt`).
* **Installation 1-clic sur smartphone** : Double-cliquer ou exécuter `Installer_Medizy_Mobile.bat` (détection automatique ADB et transfert USB).

---

### Fonctionnalités Clés Actives (v1.4.0)
- **Moteur DCI & Génériques Algériens (Pharmacie Express)** : Recherche instantanée de médicaments et substitution immédiate en cas de rupture de stock (princeps ➔ génériques locaux Saidal, Biopharm...) avec statut Chifa.
- **Contact Direct WhatsApp & Ordonnance** : Génération de lien `wa.me/213XXXXXXXXX` pré-formaté en Darija/Français pour commande et partage de photos d'ordonnances avec les officines.
- **Routage par catégorie** : Filtrage interactif direct depuis la grille de l'accueil vers la cartographie dynamique.
- **SOS Santé 24/7** : Accès instantané aux urgences et gardes dans un rayon de 10 km (tri Haversine) et numéros d'urgence nationaux (14 / 1548).
- **Filtre Convention Chifa (ضمان اجتماعي)** : Identification immédiate des professionnels et officines conventionnés.
- **Boussole & Guidage Hors-Ligne** : Calcul vectoriel d'azimut et cap cardinal (N, NE, E...) autonome en zone blanche.
- **Triage Bilingue & Carnet Local** : Triage intelligent Français/Darija et carnet de santé local sécurisé.
