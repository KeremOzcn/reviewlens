#!/usr/bin/env bash
# Builds a Chrome Web Store upload zip containing only extension runtime
# files. Running `zip -r` on extension/ directly would also bundle
# extension/e2e/ (Playwright, node_modules, test fixtures) and
# extension/mock_server.py, which don't belong in a store submission.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION_DIR="$REPO_ROOT/extension"
DIST_DIR="$REPO_ROOT/dist"
OUT_ZIP="$DIST_DIR/reviewlens-extension.zip"

RUNTIME_FILES=(
  manifest.json
  background.js
  content.js
  popup.html
  popup.js
  popup.css
  sidepanel.html
  sidepanel.js
  sidepanel.css
  icons
)

mkdir -p "$DIST_DIR"
rm -f "$OUT_ZIP"

STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT

for item in "${RUNTIME_FILES[@]}"; do
  cp -R "$EXTENSION_DIR/$item" "$STAGE_DIR/"
done

(cd "$STAGE_DIR" && zip -r -q "$OUT_ZIP" .)

echo "Wrote $OUT_ZIP"
unzip -l "$OUT_ZIP"
