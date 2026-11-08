# MEDIZY — Développement gratuit depuis Android

Ce guide organise les trois voies de travail : Codespaces (édition), GitHub Actions (tests/APK) et assistance IA.

## 1. Codespaces depuis Chrome Android
1. Ouvrir https://github.com/codespaces
2. Se connecter au compte GitHub propriétaire du dépôt.
3. Choisir **New codespace** puis le dépôt `nemirfarid/MEDIZY-DATA-ENGINE`, branche `main`.
4. Ouvrir le terminal intégré et vérifier le contenu du dossier `mobile/`.
5. Modifier uniquement les fichiers nécessaires, puis créer une branche de travail avant les changements.
6. Commit/push sur cette branche. Ne jamais modifier ou remplacer l'annuaire CSV/GZ pour une correction UI.

Quota : le compte personnel GitHub Free inclut actuellement 120 core-hours et 15 GB-month de stockage Codespaces (soit environ 60 heures sur une machine 2 cœurs). Le codespace doit être arrêté quand on quitte. L'usage au-delà du quota peut être bloqué sans moyen de paiement.

## 2. Automatisation de tests et APK
Le dépôt possède déjà `.github/workflows/android-apk.yml`. Il déclenche le workflow manuellement et lors de changements dans `mobile/**` ou ce workflow. Il fait checkout, installe Java/Flutter, restaure le projet Flutter, copie l'annuaire compressé, exécute `flutter pub get`, `flutter analyze`, `flutter test`, puis `flutter build apk --release` et publie l'APK comme artifact 14 jours.

Depuis Android :
1. Ouvrir https://github.com/nemirfarid/MEDIZY-DATA-ENGINE/actions
2. Sélectionner **Android APK**.
3. Appuyer **Run workflow** sur la branche `main` (ou branche de travail).
4. Ouvrir l'exécution et attendre la fin.
5. Télécharger l'artifact `medizy-android-apk` seulement si le job Build est vert.

Ne pas lancer d'import de données ni d'écrasement DB dans le workflow de build. Un build réussi ne prouve pas à lui seul que l'application démarre ou que toutes les structures sont visibles : vérifier l'installation et les écrans sur le téléphone.

## 3. Assistance IA gratuite
- GitHub Copilot Free : https://github.com/features/copilot — quota gratuit limité, notamment jusqu'à 2 000 complétions/mois selon l'offre affichée par GitHub.
- ChatGPT : demander une analyse ciblée en fournissant le fichier concerné, le message d'erreur complet et les étapes de reproduction. Ne partager aucune clé, token, mot de passe, donnée patient ni fichier de production sensible.
- Demander à l'IA un patch minimal, les tests à exécuter et les risques; appliquer les modifications dans une branche, puis examiner le diff avant fusion.

## Règles de protection MEDIZY
- Pas de suppression, réinitialisation, remplacement ou déduplication destructive de la base de données sans sauvegarde vérifiée et accord explicite.
- Pas de commit de clés API, secrets, données personnelles ou exports sensibles.
- Garder les changements applicatifs séparés des changements de données.
- Préférer une branche de travail et une Pull Request; ne fusionner que si analyse, tests et revue sont satisfaisants.
- La disponibilité gratuite de Codespaces/Actions dépend des quotas GitHub. Aucun outil ne garantit un développement gratuit et continu 24 h/24.
