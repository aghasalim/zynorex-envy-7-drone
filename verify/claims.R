# Recompute the README's comparison arithmetic from docs/claims.csv in R.
#
# Same checks as the SQL, C and Go versions. No external packages.
#
# Run: Rscript verify/claims.R <repo root>

args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) > 0) args[1] else "."

readme <- paste(readLines(file.path(root, "README.md"), warn = FALSE), collapse = "\n")
claims <- read.csv(file.path(root, "docs", "claims.csv"), stringsAsFactors = FALSE)

bad <- 0
fail <- function(msg) { cat("  FAIL:", msg, "\n"); bad <<- bad + 1 }

require_in_readme <- function(needle, what) {
  if (!grepl(needle, readme, fixed = TRUE))
    fail(paste0("README does not contain '", needle, "' (", what, ")"))
}

require_in_readme(as.character(nrow(claims)), "total claim rows")

spec <- claims[!is.na(claims$build_value) & claims$build_value != "" &
               !is.na(claims$reference_value) & claims$reference_value != "", ]

for (i in seq_len(nrow(spec))) {
  r  <- spec[i, ]
  bv <- as.numeric(r$build_value)
  rv <- as.numeric(r$reference_value)
  if (r$id == "endurance") {
    pct <- 100.0 * (bv - rv) / rv
    require_in_readme(paste0(sprintf("%.0f", pct), "%"), "endurance gain")
  } else if (r$id == "weight") {
    diff <- as.integer(rv - bv)
    require_in_readme(as.character(diff), "weight saved")
  } else if (r$id == "range") {
    mult <- bv / rv
    require_in_readme(paste0(mult, "x"), "range multiple")
  }
}

if (bad > 0) {
  cat("R:", bad, "problem(s)\n")
  quit(status = 1)
}
cat("R:", nrow(claims), "claims, counts and comparisons reproduced\n")
