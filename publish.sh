#!/bin/bash
# Aggiorna la parola del giorno e pubblica il sito su GitHub Pages.
set -e
cd "$(dirname "$0")"
python3 update.py >/dev/null
python3 render.py
git add -A
git -c user.name=Jordan -c user.email=minemistico@gmail.com commit -qm "parola del giorno: $(python3 -c "import json;print(json.load(open('word.json'))['lemma'])")" || true
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
