#!/usr/bin/env bash
# List all unit-test files under each module's src/test/java
# Output: relative path from repo root, one per line, sorted.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/Users/zeeshanarif/Documents/GitHub/newandroid/wego-android-n}"
cd "$REPO_ROOT"

find . -type d -name "build" -prune -o \
       -type d -name ".gradle" -prune -o \
       -type f \( -name "*.kt" -o -name "*.java" \) \
       -path "*/src/test/java/*" \
       -print \
| sed 's|^\./||' \
| sort
