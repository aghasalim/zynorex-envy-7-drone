// Structural validation of the repository's claim table, plus an independent
// recomputation of the summary the README publishes from it.
//
// docs/claims.csv is now the evidence for every claim in this repository: the
// figure is drawn from it and the README quotes counts derived from it. Nothing
// checked that the file is well formed. A ragged row, a column name that got
// duplicated in an edit, a value left blank, or an evidence class spelled a new
// way would all pass unnoticed through the Python that reads it and would just
// change the figure. This rejects all of those, then recomputes the eight
// published numbers and requires the README to state each one.
package main

import (
	"encoding/csv"
	"flag"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

var classes = map[string]bool{
	"spec": true, "component": true, "documented": true, "missing": true,
}

type row map[string]string

// readTable rejects a ragged file outright, which is the point, and returns the
// header separately so duplicate and empty column names can be reported.
func readTable(path string) ([]string, []row, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = 0
	records, err := r.ReadAll()
	if err != nil {
		return nil, nil, err
	}
	if len(records) < 2 {
		return nil, nil, fmt.Errorf("only %d rows", len(records))
	}
	header := records[0]
	var rows []row
	for _, rec := range records[1:] {
		m := row{}
		for i, h := range header {
			m[h] = rec[i]
		}
		rows = append(rows, m)
	}
	return header, rows, nil
}

func validate(header []string, rows []row) []string {
	var problems []string

	seen := map[string]bool{}
	for _, h := range header {
		if strings.TrimSpace(h) == "" {
			problems = append(problems, "a column has an empty name")
		}
		if seen[h] {
			problems = append(problems, fmt.Sprintf("column %q appears twice", h))
		}
		seen[h] = true
	}
	for _, want := range []string{"id", "claim", "value", "evidence",
		"build_value", "reference_value", "unit"} {
		if !seen[want] {
			problems = append(problems, fmt.Sprintf("no column named %q", want))
		}
	}
	if len(problems) > 0 {
		return problems
	}

	ids := map[string]bool{}
	for i, r := range rows {
		where := fmt.Sprintf("row %d (%s)", i+2, r["id"])
		if strings.TrimSpace(r["id"]) == "" {
			problems = append(problems, fmt.Sprintf("row %d has a blank id", i+2))
		}
		if ids[r["id"]] {
			problems = append(problems, fmt.Sprintf("%s: duplicate id", where))
		}
		ids[r["id"]] = true

		for _, f := range []string{"claim", "value", "evidence"} {
			if strings.TrimSpace(r[f]) == "" {
				problems = append(problems, fmt.Sprintf("%s: %s is blank", where, f))
			}
		}
		if !classes[r["evidence"]] {
			problems = append(problems,
				fmt.Sprintf("%s: unknown evidence class %q", where, r["evidence"]))
		}

		// Only the three headline comparisons carry numbers, and both sides
		// have to be there: half a comparison is worse than none.
		hasBuild := r["build_value"] != ""
		hasRef := r["reference_value"] != ""
		if hasBuild != hasRef {
			problems = append(problems, fmt.Sprintf("%s: one side of the comparison is missing", where))
		}
		if hasBuild && r["evidence"] != "spec" {
			problems = append(problems,
				fmt.Sprintf("%s: carries numbers but is not a design target", where))
		}
		if r["evidence"] == "spec" && !hasBuild {
			problems = append(problems,
				fmt.Sprintf("%s: is a design target with no numbers to check", where))
		}
		for _, f := range []string{"build_value", "reference_value"} {
			if r[f] == "" {
				continue
			}
			v, err := strconv.ParseFloat(r[f], 64)
			if err != nil {
				problems = append(problems, fmt.Sprintf("%s: %s is not a number: %q", where, f, r[f]))
				continue
			}
			if math.IsNaN(v) || math.IsInf(v, 0) {
				problems = append(problems, fmt.Sprintf("%s: %s is %v", where, f, v))
			}
			if v <= 0 {
				problems = append(problems, fmt.Sprintf("%s: %s is not positive: %v", where, f, v))
			}
		}
		if hasBuild && r["unit"] == "" {
			problems = append(problems, fmt.Sprintf("%s: comparison has no unit", where))
		}
	}
	return problems
}

// published recomputes, from the claim table alone, every row of the README's
// recomputed-values table.
func published(rows []row) [][2]string {
	count := func(class string) int {
		n := 0
		for _, r := range rows {
			if r["evidence"] == class {
				n++
			}
		}
		return n
	}
	num := func(id, field string) float64 {
		for _, r := range rows {
			if r["id"] == id {
				v, _ := strconv.ParseFloat(r[field], 64)
				return v
			}
		}
		return math.NaN()
	}

	gain := 100 * (num("endurance", "build_value") - num("endurance", "reference_value")) /
		num("endurance", "reference_value")
	saved := num("weight", "reference_value") - num("weight", "build_value")
	ratio := num("range", "build_value") / num("range", "reference_value")

	return [][2]string{
		{"claim rows in docs/claims.csv", strconv.Itoa(len(rows))},
		{"design-target claims", strconv.Itoa(count("spec"))},
		{"component-rating claims", strconv.Itoa(count("component"))},
		{"documented claims", strconv.Itoa(count("documented"))},
		{"open items", strconv.Itoa(count("missing"))},
		{"endurance gain over the reference", fmt.Sprintf("%.2f%%", gain)},
		{"weight saved against the reference", fmt.Sprintf("%g g", saved)},
		{"control-range multiple", fmt.Sprintf("%gx", ratio)},
	}
}

func main() {
	root := flag.String("root", ".", "repository root")
	flag.Parse()

	table := filepath.Join(*root, "docs", "claims.csv")
	header, rows, err := readTable(table)
	if err != nil {
		fmt.Printf("  FAIL: docs/claims.csv is unreadable: %v\n", err)
		os.Exit(1)
	}

	problems := validate(header, rows)
	if len(problems) == 0 {
		fmt.Printf("  docs/claims.csv: %d columns, %d rows, structurally clean\n",
			len(header), len(rows))
	}

	readmeBytes, err := os.ReadFile(filepath.Join(*root, "README.md"))
	if err != nil {
		fmt.Printf("  FAIL: README.md is unreadable: %v\n", err)
		os.Exit(1)
	}
	readme := string(readmeBytes)

	for _, kv := range published(rows) {
		want := fmt.Sprintf("| %s | %s |", kv[0], kv[1])
		if strings.Contains(readme, want) {
			fmt.Printf("  README publishes %s as %s\n", kv[0], kv[1])
		} else {
			problems = append(problems,
				fmt.Sprintf("README does not publish %q as %q", kv[0], kv[1]))
		}
	}

	// The claim column is what the figure prints, so it has to be the same text
	// the README uses for the three headline rows.
	for _, r := range rows {
		if r["evidence"] != "spec" {
			continue
		}
		if !strings.Contains(readme, r["claim"]) {
			problems = append(problems,
				fmt.Sprintf("README never mentions the claim %q", r["claim"]))
		}
	}

	if len(problems) > 0 {
		fmt.Println("\nFAILED:")
		for _, p := range problems {
			fmt.Printf("  - %s\n", p)
		}
		os.Exit(1)
	}
	fmt.Println("\nGo validates the claim table and reproduces all 8 published numbers, exact")
}
