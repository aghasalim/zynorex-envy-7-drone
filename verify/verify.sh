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

# The SQL prints one "label|value" line per figure it recomputed. Every value
# has to appear in README.md spelled exactly that way, which is the check the
# claims.sql header has always claimed this function performs. It did not: the
# body ended in an echo, so the function returned 0 no matter what SQLite said,
# including when SQLite failed outright.
check_sql () {
    local out rc missing=0 n=0 label value
    out=$(sqlite3 -init verify/claims.sql :memory: "" < /dev/null 2>&1 | tr -d '\r')
    rc=$?
    if [ "$rc" -ne 0 ]; then
        printf 'sqlite3 exited %d\n%s\n' "$rc" "$out"
        return 1
    fi
    if [ -z "$out" ] || printf '%s' "$out" | grep -qi '^Error'; then
        printf 'sqlite3 produced no usable output:\n%s\n' "$out"
        return 1
    fi
    while IFS='|' read -r label value; do
        [ -n "$label" ] || continue
        n=$((n + 1))
        if [ -z "$value" ]; then
            printf '  FAIL %-38s recomputed nothing\n' "$label"
            missing=$((missing + 1))
        elif grep -qF -- "$value" README.md; then
            printf '  ok   %-38s %s\n' "$label" "$value"
        else
            printf '  FAIL %-38s %s is not in README.md\n' "$label" "$value"
            missing=$((missing + 1))
        fi
    done <<< "$out"
    if [ "$n" -eq 0 ]; then
        echo "no figures came back from the SQL"
        return 1
    fi
    if [ "$missing" -gt 0 ]; then
        printf '%d of %d figures are not in README.md as the SQL spells them\n' \
               "$missing" "$n"
        return 1
    fi
    printf 'SQL reproduces %d figures, each one present in README.md\n' "$n"
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
