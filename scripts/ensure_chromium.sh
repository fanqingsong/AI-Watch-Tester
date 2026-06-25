#!/usr/bin/env bash
# Ensure a Playwright chromium browser is usable.
#
# Why this exists: Playwright >= 1.60 downloads Chrome for Testing (CFT) from a
# path that the common `PLAYWRIGHT_DOWNLOAD_HOST` mirrors (npmmirror etc.) do NOT
# mirror, so `playwright install chromium` 404s. Worse, `playwright install`
# wipes any manually-placed browser dir before re-downloading, then hangs.
#
# Strategy: if chromium already launches locally (e.g. restored from a mirror
# via scripts/restore_chromium.sh), skip the network install entirely. Only fall
# back to `playwright install` when it's genuinely missing — which still works
# unchanged on machines with direct access to the official CDN.
set -euo pipefail

if python - <<'PY'
import sys
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        b.close()
except Exception:
    sys.exit(1)
PY
then
    echo "ensure_chromium: chromium already usable, skipping 'playwright install'."
    exit 0
fi

echo "ensure_chromium: chromium missing, running 'playwright install chromium'..."
exec playwright install chromium
