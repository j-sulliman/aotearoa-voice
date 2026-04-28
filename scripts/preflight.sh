#!/usr/bin/env bash
#
# Pre-publish preflight check.
#
# Run from the repo root before pushing the repo public for the first time.
# Each check is independently red/green; failures are summarised at the end.
# Exit code is the count of failed checks, so wrap in CI later if you want.
#
# Usage:
#   ./scripts/preflight.sh

set -uo pipefail

cd "$(dirname "$0")/.."

# --- ANSI helpers ---
red()    { printf "\033[0;31m%s\033[0m" "$1"; }
green()  { printf "\033[0;32m%s\033[0m" "$1"; }
yellow() { printf "\033[0;33m%s\033[0m" "$1"; }
bold()   { printf "\033[1m%s\033[0m" "$1"; }

PASS=0
FAIL=0
WARN=0
FAILED_CHECKS=()

check() {
    local label=$1
    shift
    printf "  %-58s " "$label"
    if "$@" >/tmp/preflight.out 2>&1; then
        echo "$(green ✓)"
        PASS=$((PASS + 1))
    else
        echo "$(red ✗)"
        FAIL=$((FAIL + 1))
        FAILED_CHECKS+=("$label")
        if [[ -s /tmp/preflight.out ]]; then
            sed 's/^/      /' /tmp/preflight.out
        fi
    fi
}

warn() {
    local label=$1
    shift
    printf "  %-58s " "$label"
    if "$@" >/tmp/preflight.out 2>&1; then
        echo "$(green ✓)"
        PASS=$((PASS + 1))
    else
        echo "$(yellow ⚠)"
        WARN=$((WARN + 1))
        if [[ -s /tmp/preflight.out ]]; then
            sed 's/^/      /' /tmp/preflight.out
        fi
    fi
}

# ====================================================================
# Section 1: Secrets hygiene
# ====================================================================
echo
echo "$(bold '🔒 Secrets hygiene')"

check ".env is in .gitignore" \
    bash -c 'grep -qE "^\.env(\$|\b|/)" .gitignore || grep -qE "^\.env\$" .gitignore'

check ".env is not tracked by git" \
    bash -c '! git ls-files --error-unmatch .env 2>/dev/null'

check ".env has never been committed (full history)" \
    bash -c 'test -z "$(git log --all --oneline -- .env 2>/dev/null)"'

check "No obvious secrets in tracked files" \
    bash -c '
        # Look for common API key prefixes outside .env/.env.example
        if git grep -nE "(sk-ant-api03-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|sk_[a-f0-9]{40,})" \
            -- ":!.env*" ":!*.example" ":!docs/" 2>/dev/null | grep -v "placeholder"; then
            echo "Found what look like real API keys in tracked files."
            exit 1
        fi
        exit 0
    '

# ====================================================================
# Section 2: Repo essentials
# ====================================================================
echo
echo "$(bold '📦 Repo essentials')"

check "LICENSE exists" \
    test -f LICENSE

check "README.md exists" \
    test -f README.md

check "ARCHITECTURE.md exists" \
    test -f ARCHITECTURE.md

check ".env.example exists" \
    test -f .env.example

check "docker-compose.yml exists and validates" \
    docker compose config --quiet

# ====================================================================
# Section 3: README polish
# ====================================================================
echo
echo "$(bold '✏️  README polish')"

check "Hero GIF present at docs/hero.gif" \
    test -f docs/hero.gif

check "README references docs/hero.gif" \
    grep -q "docs/hero.gif" README.md

warn "No 'example.com' placeholders left in README" \
    bash -c '! grep -q "aotearoa.example.com" README.md'

warn "No 'replace with' placeholders left in README" \
    bash -c '! grep -qi "replace with your" README.md'

check "Cloned-voice line present in README" \
    grep -q "cloned in ElevenLabs" README.md

check "MIT licence linked" \
    grep -q "MIT licence" README.md

# ====================================================================
# Section 4: Build sanity (fast — no network)
# ====================================================================
echo
echo "$(bold '🛠  Build sanity')"

check "All Python modules compile" \
    bash -c '
        python3 -m py_compile $(find backend mcp_server -name "*.py" -not -path "*/__pycache__/*")
    '

check "locations.json is valid JSON with all required fields" \
    python3 -c '
import json
with open("mcp_server/data/locations.json") as f:
    locs = json.load(f)
required = {"id","name","region","lat","lng","themes","description","things_to_do","best_season","transit_context","nearby"}
for loc in locs:
    missing = required - set(loc.keys())
    if missing:
        loc_id = loc.get("id")
        print(f"{loc_id} missing {missing}")
        raise SystemExit(1)
'

check "pronunciations.json is valid JSON" \
    python3 -c 'import json; json.load(open("mcp_server/data/pronunciations.json"))'

check "pronunciations.pls is valid XML" \
    python3 -c 'import xml.etree.ElementTree as ET; ET.parse("scripts/pronunciations.pls")'

check "Frontend typechecks" \
    bash -c 'cd frontend && test -d node_modules && npx tsc -b 2>&1'

# ====================================================================
# Summary
# ====================================================================
echo
TOTAL=$((PASS + FAIL + WARN))
echo "─────────────────────────────────────────────────────────────"
if [[ $FAIL -eq 0 && $WARN -eq 0 ]]; then
    echo "$(green "✓ All $TOTAL checks passed. Safe to publish.")"
    exit 0
elif [[ $FAIL -eq 0 ]]; then
    echo "$(yellow "⚠ $WARN warning(s) — review before publishing.")"
    echo "  ($PASS passed, $WARN warnings, 0 failures)"
    exit 0
else
    echo "$(red "✗ $FAIL check(s) failed. Do not publish yet.")"
    echo "  ($PASS passed, $WARN warnings, $FAIL failures)"
    echo
    echo "Failed:"
    for c in "${FAILED_CHECKS[@]}"; do
        echo "  • $c"
    done
    exit "$FAIL"
fi
