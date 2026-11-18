#!/bin/bash
# Aggiorna la parola del giorno e pubblica il sito.
set -e
cd "$(dirname "$0")"
python3 update.py >/dev/null
python3 render.py
git add -A
git -c user.name=Jordan -c user.email=minemistico@gmail.com commit -qm "parola del giorno: $(python3 -c "import json;print(json.load(open('word.json'))['lemma'])")" || true
git push -q origin main
# pubblica site/ sul ramo gh-pages (Pages)
git worktree add -q --orphan pub-tmp pub
cd pub
cp ../site/index.html ../site/wallpaper.png .
touch .nojekyll
git add -A
git -c user.name=Jordan -c user.email=minemistico@gmail.com commit -qm "sito"
cd ..
git push -q -f origin pub-tmp:gh-pages
git worktree remove pub --force
git branch -D pub-tmp -q || true
echo "PUBBLICATO $(date +%F)"
