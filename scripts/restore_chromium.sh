#!/usr/bin/env bash
# Restore Playwright chromium browsers from the npmmirror Chrome-for-Testing
# mirror. Use when `playwright install chromium` fails (404 / slow) because
# Playwright >= 1.60's CFT download path isn't mirrored by PLAYWRIGHT_DOWNLOAD_HOST.
#
# Reads the exact revision + browserVersion from the installed Playwright's
# browsers.json, so it stays correct across Playwright upgrades.
#
# Usage:
#   bash scripts/restore_chromium.sh            # download + extract
#   bash scripts/restore_chromium.sh --cache    # reuse zips already in ~/.aat-playwright-zips
set -euo pipefail

MIRROR_HOST="${PLAYWRIGHT_CFT_MIRROR:-https://cdn.npmmirror.com/binaries/chrome-for-testing}"
STORE_DIR="${STORE_DIR:-$HOME/.aat-playwright-zips}"
CACHE_DIR="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"

# Resolve revision + CFT version from the installed playwright's browsers.json.
read -r REV VER < <(python - <<'PY'
import json
from pathlib import Path
import playwright._impl._driver as d
drv = Path(d.compute_driver_executable()[0])
meta = json.load(open(drv.parent / "package" / "browsers.json"))
c = next(b for b in meta["browsers"] if b["name"] == "chromium")
print(c["revision"], c["browserVersion"])
PY
)
echo "playwright chromium: revision=$REV browserVersion=$VER"

mkdir -p "$STORE_DIR" "$CACHE_DIR/chromium-$REV" "$CACHE_DIR/chromium_headless_shell-$REV"

USE_CACHE=0
[[ "${1:-}" == "--cache" ]] && USE_CACHE=1

fetch() {  # fetch <url> <dest>
    local name; name="$(basename "$2")"
    if [[ $USE_CACHE -eq 1 && -f "$2" ]]; then
        echo "reuse cached $name"
    else
        echo "downloading $name ..."
        curl -L --fail --silent --show-error -o "$2" "$1"
    fi
}

URL_BASE="$MIRROR_HOST/$VER/linux64"
fetch "$URL_BASE/chrome-linux64.zip"                "$STORE_DIR/chrome-linux64.zip"
fetch "$URL_BASE/chrome-headless-shell-linux64.zip" "$STORE_DIR/chrome-headless-shell-linux64.zip"

rm -rf "$CACHE_DIR/chromium-$REV/chrome-linux64" \
       "$CACHE_DIR/chromium_headless_shell-$REV/chrome-headless-shell-linux64"
unzip -q "$STORE_DIR/chrome-linux64.zip"                -d "$CACHE_DIR/chromium-$REV"
unzip -q "$STORE_DIR/chrome-headless-shell-linux64.zip" -d "$CACHE_DIR/chromium_headless_shell-$REV"
chmod +x "$CACHE_DIR/chromium-$REV/chrome-linux64/chrome" \
         "$CACHE_DIR/chromium_headless_shell-$REV/chrome-headless-shell-linux64/chrome-headless-shell"

echo "restored chromium + headless-shell ($VER) to $CACHE_DIR"
echo "next: 'make dev' will detect chromium is usable and skip the network install."
