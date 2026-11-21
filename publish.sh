#!/bin/bash
# Aggiorna la parola del giorno e pubblica il sito su GitHub Pages.
set -e
cd "$(dirname "$0")"
# PYTHONPATH puo' essere iniettato da Hermes e puntare a site-packages di un'altra
# versione Python: PIL si caricherebbe ma _imaging (.so cpython-XY) fallirebbe.
unset PYTHONPATH VIRTUAL_ENV CONDA_PREFIX
PY=""
for cand in \
  /Users/jordan/.hermes/hermes-agent/venv/bin/python3 \
  /opt/homebrew/bin/python3 \
  python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import PIL, pyphen" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  for cand in /Users/jordan/.hermes/installs/*/environments/*/venv/bin/python3; do
    if [ -x "$cand" ] && "$cand" -c "import PIL, pyphen" >/dev/null 2>&1; then PY="$cand"; break; fi
  done
fi
[ -n "$PY" ] || { echo "ERRORE: nessun python3 con PIL+pyphen" >&2; exit 1; }
"$PY" update.py >/dev/null
"$PY" render.py
git add -A
git -c user.name=Jordan -c user.email=minemistico@gmail.com commit -qm "parola del giorno: $("$PY" -c "import json;print(json.load(open('word.json'))['lemma'])")" || true
git push -q origin main

# pubblica site/ sul ramo gh-pages (Pages)
git worktree remove pub --force 2>/dev/null || true
git branch -D pub 2>/dev/null || true
git worktree add -q -b pub pub
git -C pub rm -rqf --cached . 2>/dev/null || true
find pub -mindepth 1 ! -name .git -delete
cp site/index.html site/wallpaper.png pub/
touch pub/.nojekyll
git -C pub add -A
git -C pub -c user.name=Jordan -c user.email=minemistico@gmail.com commit -qm "sito $(date +%F)" || true
git push -q -f origin pub:gh-pages
git worktree remove pub --force
git branch -D pub -q || true
echo "PUBBLICATO $(date +%F)"
