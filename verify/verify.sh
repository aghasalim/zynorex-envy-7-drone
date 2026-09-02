#!/usr/bin/env bash
# Recompute the published claim counts and comparison figures from
# docs/claims.csv in eight independent implementations.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

pass=0 fail=0 skip=0

run () {
    local name="$1" tool="$2"; shift 2
    printf '\n=== %s ===\n' "$name"
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'skipped: %s is not installed\n' "$tool"
        skip=$((skip + 1)); return
    fi
    if "$@"; then pass=$((pass + 1)); else fail=$((fail + 1)); fi
}

check_sql () {
    local out
    out=$(sqlite3 -init verify/claims.sql :memory: "" < /dev/null 2>&1 | tr -d '\r')
    echo "$out"
}

check_c () {
    cc -std=c99 -O2 -Wall -Wextra -Wpedantic -Werror -o /tmp/derived \
        verify/derived.c -lm &&
    /tmp/derived "$root"
}

check_go () { ( cd verify/gocheck && go run . -root "$root" ); }
check_js () { node verify/wiring.mjs "$root"; }
check_py () { python3 verify/claims.py "$root"; }
check_r  () { Rscript verify/claims.R "$root"; }
check_rb () { ruby verify/claims.rb "$root"; }

run "SQL, counts and comparisons"       sqlite3 check_sql
run "C, comparisons in README"          cc      check_c
run "Go, structure and comparisons"     go      check_go
run "JavaScript, wiring diagram"        node    check_js
run "Python, counts and comparisons"    python3 check_py
run "R, counts and comparisons"         Rscript check_r
run "Ruby, counts and comparisons"      ruby    check_rb

printf '\n%s\n' "----------------------------------------"
printf '%d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ] || exit 1
[ "$pass" -gt 0 ] || { echo "nothing ran"; exit 1; }
