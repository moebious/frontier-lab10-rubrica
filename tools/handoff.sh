#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo "🚀 FRONTIER LAB10 — DESIGN DOCS HANDOFF"
echo "=========================================="

# 1. Regenerate PDF if export script exists
if [ -f "tools/pdf/export.sh" ]; then
  echo "📄 Ensuring docs/DESIGN.pdf is up to date..."
  sh tools/pdf/export.sh || echo "⚠️ PDF re-export failed, using existing PDF if present."
fi

# 2. Check files
if [ ! -f "docs/DESIGN.pdf" ]; then
  echo "❌ Error: docs/DESIGN.pdf not found!"
  exit 1
fi

if [ ! -f "site/diagram.png" ]; then
  echo "❌ Error: site/diagram.png not found!"
  exit 1
fi

echo "✅ Verified docs/DESIGN.pdf ($(du -h docs/DESIGN.pdf | cut -f1))"
echo "✅ Verified site/diagram.png ($(du -h site/diagram.png | cut -f1))"

# 3. Stage ONLY the design docs & diagram (keep all code/tools/traces untracked)
git add -f docs/DESIGN.pdf site/diagram.png
if [ -f "docs/DESIGN.md" ]; then git add -f docs/DESIGN.md; fi
if [ -f "site/diagram.svg" ]; then git add -f site/diagram.svg; fi

# Commit if there are changes
if git diff --cached --quiet; then
  echo "ℹ️ No changes in design doc or diagram since last commit."
else
  git commit -m "docs(submission): 01 SYSTEMS DESIGN (doc + architecture diagram)"
  echo "✅ Committed design documents."
fi

# 4. Check if git remote origin exists, otherwise create via gh
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "📦 Creating public repository on GitHub via gh..."
  gh repo create frontier-lab10-rubrica --public --source=. --remote=origin
fi

# Ensure branch is main
git branch -M main

# 5. Push to GitHub
echo "⬆️ Pushing to GitHub..."
git push -u origin main

REMOTE_URL=$(git remote get-url origin | sed -E 's/git@github.com:/https:\/\/github.com\//' | sed 's/\.git$//')

echo ""
echo "=========================================="
echo "🎯 ENTREGA LISTA — COPIA ESTOS DATOS"
echo "=========================================="
echo ""
echo "Opción 1: ENLACES PÚBLICOS (Garantizados 100% online)"
echo "----------------------------------------------------"
echo "1. DOC DE DISEÑO:"
echo "   ${REMOTE_URL}/blob/main/docs/DESIGN.pdf"
echo ""
echo "2. DIAGRAMA DE ARQUITECTURA:"
echo "   ${REMOTE_URL}/blob/main/site/diagram.png"
echo ""
echo "----------------------------------------------------"
echo "Opción 2: SUBIDA DIRECTA DE ARCHIVOS (Botón ARCHIVO)"
echo "----------------------------------------------------"
echo "1. DOC DE DISEÑO:"
echo "   $ROOT_DIR/docs/DESIGN.pdf"
echo ""
echo "2. DIAGRAMA DE ARQUITECTURA:"
echo "   $ROOT_DIR/site/diagram.png"
echo ""
echo "👉 Portal de entregas: https://frontier.lab10.ai/evento/reto/entregas"
echo "=========================================="
