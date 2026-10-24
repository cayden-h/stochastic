#!/bin/zsh
# Usage: ./render.sh 01-big-picture   (renders HTML to PDF, and PNG previews into ./preview)
cd "$(dirname "$0")"
mkdir -p preview
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=15000 --print-to-pdf="$1.pdf" "file://$PWD/$1.html" >/dev/null 2>&1
pdftoppm -png -r 60 "$1.pdf" "preview/$1"
ls preview | grep "$1"
