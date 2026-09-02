/* Recompute the README's comparison arithmetic from docs/claims.csv.
 *
 * The headline table says this build is lighter, ranges further and flies 70%
 * longer than the reference. Those are the only numbers in the repository that
 * are derived rather than copied off a spec sheet, and they were derived once,
 * by hand, in prose. This reads the claim table, resolves every column BY NAME
 * so a reordered file cannot silently shift the arithmetic, recomputes the
 * three comparisons, and requires the README to say what they come to.
 *
 * Build: cc -std=c99 -O2 -Wall -Wextra -Wpedantic -Werror -o derived
 *            verify/derived.c -lm
 * Run:   ./derived <repo root>
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_COLS 16
#define MAX_LINE 1024

static int problems = 0;

static void fail(const char *fmt, const char *a, const char *b) {
    printf("  FAIL: ");
    printf(fmt, a, b);
    printf("\n");
    problems++;
}

/* Split one CSV line in place, honouring double quoted fields. Returns the
 * field count. The claim table contains "30 A, SimonK", so a naive split on
 * commas would read a five column file as six columns. */
static int split_csv(char *line, char *fields[], int max) {
    int n = 0;
    char *out = line;
    const char *in = line;

    while (*in && n < max) {
        int quoted = 0;
        fields[n++] = out;
        for (;;) {
            char c = *in;
            if (c == '\0' || c == '\n' || c == '\r') break;
            if (c == '"') { quoted = !quoted; in++; continue; }
            if (c == ',' && !quoted) { in++; break; }
            *out++ = c;
            in++;
        }
        *out++ = '\0';
        if (*in == '\0' || *in == '\n' || *in == '\r') break;
    }
    return n;
}

static int column_of(char *header[], int ncols, const char *name) {
    for (int i = 0; i < ncols; i++)
        if (strcmp(header[i], name) == 0) return i;
    return -1;
}

/* The whole README, so claims can be looked for as plain substrings. */
static char *slurp(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    rewind(f);
    char *buf = malloc((size_t)size + 1);
    if (!buf) { fclose(f); return NULL; }
    size_t got = fread(buf, 1, (size_t)size, f);
    buf[got] = '\0';
    fclose(f);
    return buf;
}

static void require_in_readme(const char *readme, const char *needle,
                              const char *what) {
    if (strstr(readme, needle)) {
        printf("  README states %s as %s\n", what, needle);
    } else {
        fail("README does not state %s as %s", what, needle);
    }
}

int main(int argc, char **argv) {
    const char *root = argc > 1 ? argv[1] : ".";
    char csv_path[512], readme_path[512];
    snprintf(csv_path, sizeof csv_path, "%s/docs/claims.csv", root);
    snprintf(readme_path, sizeof readme_path, "%s/README.md", root);

    char *readme = slurp(readme_path);
    if (!readme) { printf("  FAIL: cannot read %s\n", readme_path); return 1; }

    FILE *f = fopen(csv_path, "r");
    if (!f) { printf("  FAIL: cannot read %s\n", csv_path); return 1; }

    char line[MAX_LINE];
    char *header[MAX_COLS];
    if (!fgets(line, sizeof line, f)) { printf("  FAIL: empty claim table\n"); return 1; }
    int ncols = split_csv(line, header, MAX_COLS);

    const char *needed[] = {"id", "value", "evidence", "build_value",
                            "reference_value", "unit"};
    int idx[6];
    for (int i = 0; i < 6; i++) {
        idx[i] = column_of(header, ncols, needed[i]);
        if (idx[i] < 0) {
            printf("  FAIL: no column named %s\n", needed[i]);
            return 1;
        }
    }
    const int c_id = idx[0], c_value = idx[1], c_evidence = idx[2];
    const int c_build = idx[3], c_reference = idx[4], c_unit = idx[5];

    double endurance_build = 0.0, endurance_reference = 0.0;
    int spec_rows = 0;

    while (fgets(line, sizeof line, f)) {
        char *field[MAX_COLS];
        int n = split_csv(line, field, MAX_COLS);
        if (n < ncols) continue;
        if (strcmp(field[c_evidence], "spec") != 0) continue;
        spec_rows++;

        const char *id = field[c_id];
        char *end = NULL;
        double build = strtod(field[c_build], &end);
        if (end == field[c_build] || !isfinite(build)) {
            fail("%s has no usable build value (%s)", id, field[c_build]);
            continue;
        }
        double reference = strtod(field[c_reference], &end);
        if (end == field[c_reference] || !isfinite(reference)) {
            fail("%s has no usable reference value (%s)", id, field[c_reference]);
            continue;
        }

        /* Both sides of the comparison must be quoted in the README, with the
         * unit, so a value edited in one place and not the other is caught. */
        char want[128];
        snprintf(want, sizeof want, "%.0f %s", build, field[c_unit]);
        require_in_readme(readme, want, id);
        snprintf(want, sizeof want, "%.0f %s", reference, field[c_unit]);
        require_in_readme(readme, want, id);

        /* The claim table's own value string has to agree with the number. */
        snprintf(want, sizeof want, "%.0f", build);
        if (!strstr(field[c_value], want))
            fail("%s value column %s does not contain its own build number", id,
                 field[c_value]);

        if (strcmp(id, "weight") == 0 && !(build < reference))
            fail("%s: this build is not lighter than the reference%s", id, "");
        if (strcmp(id, "range") == 0 && !(build > reference))
            fail("%s: this build does not range further%s", id, "");
        if (strcmp(id, "endurance") == 0) {
            if (!(build > reference))
                fail("%s: this build does not fly longer%s", id, "");
            endurance_build = build;
            endurance_reference = reference;
        }
    }
    fclose(f);

    if (spec_rows != 3) {
        printf("  FAIL: expected 3 design-target rows, found %d\n", spec_rows);
        problems++;
    }
    if (endurance_reference <= 0.0) {
        printf("  FAIL: no endurance row to derive the gain from\n");
        free(readme);
        return 1;
    }

    double gain = 100.0 * (endurance_build - endurance_reference) / endurance_reference;
    long rounded = lround(gain);
    printf("  endurance gain %.2f%% from %.0f min against %.0f min, rounds to %ld%%\n",
           gain, endurance_build, endurance_reference, rounded);

    char claim[64];
    snprintf(claim, sizeof claim, "%ld%% more flight time", rounded);
    require_in_readme(readme, claim, "the headline gain");

    char stated[64];
    snprintf(stated, sizeof stated, "%.2f%%", gain);
    require_in_readme(readme, stated, "the unrounded gain");

    require_in_readme(readme, "Lighter, longer range", "the direction of all three");

    free(readme);
    if (problems) {
        printf("\n%d disagreement(s) between docs/claims.csv and README.md\n", problems);
        return 1;
    }
    printf("\nC reproduces all three comparisons and the headline gain, exact\n");
    return 0;
}
