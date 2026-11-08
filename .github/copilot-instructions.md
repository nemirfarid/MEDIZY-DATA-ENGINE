# MEDIZY contributor instructions

- Preserve the healthcare directory and all user data. Never delete, reset, replace, or deduplicate production data as part of UI/code fixes.
- Keep changes minimal and scoped. Prefer a feature branch and pull request.
- Do not commit credentials, tokens, API keys, patient data, private exports, or local build artifacts.
- Before proposing a data change, create and verify a backup and explain the migration/rollback plan.
- For Flutter changes, run `flutter pub get`, `flutter analyze`, and `flutter test` in `mobile/`; inspect the diff before committing.
- A green CI build does not establish that the app starts correctly on a physical Android device. Request device verification for launch, navigation, and directory loading.
- Never claim the national directory count or 58-wilaya coverage without running a data audit against the actual dataset.
- MEDIZY UI must not use cross-shaped symbols. Respect existing branding and accessibility.
