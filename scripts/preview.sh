#!/usr/bin/env bash
# Local preview: renders README.md through GitHub's own Markdown API and
# wraps it in GitHub's CSS. Live cards are read from ./dist if present.
#   bash scripts/preview.sh && open http://localhost:8765/dist/preview.html
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist
body=$(gh api markdown -f mode=gfm -f context=mrxvision97/mrxvision97 -f text="$(cat README.md)")
body=${body//https:\/\/raw.githubusercontent.com\/mrxvision97\/mrxvision97\/output\//\/dist\/}
body=${body//src=\"assets\//src=\"\/assets\/}
body=${body//srcset=\"assets\//srcset=\"\/assets\/}
cat > dist/preview.html <<HTML
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Profile preview</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown.min.css">
<style>body{margin:0;background:#fff}@media (prefers-color-scheme:dark){body{background:#0d1117}}
.markdown-body{box-sizing:border-box;max-width:1012px;margin:0 auto;padding:32px 16px}</style>
</head><body><article class="markdown-body">$body</article></body></html>
HTML
echo "dist/preview.html written"
