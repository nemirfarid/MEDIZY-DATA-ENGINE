#!/usr/bin/env bash
set -euo pipefail

FLUTTER_DIR="$HOME/.local/flutter"
mkdir -p "$HOME/.local"
if [ ! -d "$FLUTTER_DIR/.git" ]; then
  git clone --depth 1 --branch stable https://github.com/flutter/flutter.git "$FLUTTER_DIR"
fi
echo 'export PATH="$HOME/.local/flutter/bin:$PATH"' >> "$HOME/.bashrc"
export PATH="$FLUTTER_DIR/bin:$PATH"
flutter --version
if [ -f mobile/pubspec.yaml ]; then
  (cd mobile && flutter pub get)
fi
