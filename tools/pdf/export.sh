#!/bin/sh
# Export docs/DESIGN.md to docs/DESIGN.pdf (US Letter) via pandoc + headless Chrome.
set -eu
cd "$(dirname "$0")/../.."
TMP=$(mktemp -d)
pandoc docs/DESIGN.md -s --metadata title="Rubrica · Systems Design" -V title= \
  --css tools/pdf/print.css --embed-resources -o "$TMP/design.html" 2>/dev/null
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --no-pdf-header-footer --print-to-pdf="$PWD/docs/DESIGN.pdf" "file://$TMP/design.html" 2>/dev/null
rm -rf "$TMP"
echo "wrote docs/DESIGN.pdf"
