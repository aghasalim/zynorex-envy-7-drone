-- Recompute the summary the README publishes about its own claim table.
--
-- docs/claims.csv is the machine readable source for the evidence figure drawn
-- by ci/make_figures.py, and the README quotes counts and comparison figures
-- derived from it. Those all came out of one Python script, so nothing checked
-- them. This derives the same eight numbers in SQLite and verify/verify.sh
-- requires every one of them to appear in the README, spelled the same way.
--
-- Run: sqlite3 -init verify/claims.sql :memory: "" < /dev/null

.mode csv
.headers off
.import --csv docs/claims.csv claims

CREATE TEMP VIEW spec AS
    SELECT id,
           CAST(build_value AS REAL)     AS build,
           CAST(reference_value AS REAL) AS reference
    FROM claims
    WHERE build_value <> '' AND reference_value <> '';

.mode list
.separator |

SELECT 'claim rows in docs/claims.csv', COUNT(*) FROM claims;

SELECT 'design-target claims',    COUNT(*) FROM claims WHERE evidence = 'spec';
SELECT 'component-rating claims', COUNT(*) FROM claims WHERE evidence = 'component';
SELECT 'documented claims',       COUNT(*) FROM claims WHERE evidence = 'documented';
SELECT 'open items',              COUNT(*) FROM claims WHERE evidence = 'missing';

-- The README's headline is 70% more flight time. That is a ratio of two other
-- numbers in the same table, so it can be checked rather than trusted.
SELECT 'endurance gain over the reference',
       printf('%.2f%%', 100.0 * (build - reference) / reference)
FROM spec WHERE id = 'endurance';

SELECT 'weight saved against the reference',
       printf('%d g', CAST(reference - build AS INT))
FROM spec WHERE id = 'weight';

SELECT 'control-range multiple',
       printf('%gx', build / reference)
FROM spec WHERE id = 'range';
