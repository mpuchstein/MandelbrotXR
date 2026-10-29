#!/bin/bash
# Setup script for the `mandelbrotxr-site` Claude Code cloud environment
# (paste into claude.ai/code → environment → Setup script). Runs as root on Ubuntu 24.04.
# Needs Custom network access: default list + cdn.playwright.dev,
# playwright.download.prss.microsoft.com, playwright.azureedge.net,
# cdnjs.cloudflare.com, cdn.tailwindcss.com (see site/BRIEF.md).
set -euo pipefail
python3 -m pip install --break-system-packages playwright
python3 -m playwright install --with-deps chromium
