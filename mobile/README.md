# MEDIZY Mobile — isolated app scaffold

This folder is a new Flutter app foundation. It does not connect to or mutate the production MEDIZY database.

## Design commitments
- Original MEDIZY visual identity; no medical-cross glyphs/icons anywhere.
- Structure categories use distinct neutral pictograms (hospital, clinic, pharmacy, lab, doctor, maternity, dental, other).
- Map UI is provider-neutral. Use Google Maps only with a properly configured Google Maps key/terms; otherwise use an OpenStreetMap-compatible provider. Never scrape Google tiles or imply 99% exact duplication.
- Local data import is read-only and explicit. Do not bundle the premium dataset into Git or upload it.
- Arabic/French support and RTL/LTR layouts.

## Build locally
Install Flutter stable, then:
```sh
cd mobile
flutter pub get
flutter run
```

This initial scaffold is not yet a release APK; it needs Flutter SDK/build validation and integration of the user's premium workbook from a local, private path.
