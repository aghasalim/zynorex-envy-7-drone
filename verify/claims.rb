# Recompute the README's comparison arithmetic from docs/claims.csv in Ruby.
#
# Same checks as the SQL, C and Go versions.
#
# Run: ruby verify/claims.rb <repo root>

require "csv"

root = ARGV[0] || "."
readme = File.read(File.join(root, "README.md"), encoding: "UTF-8")
claims = CSV.read(File.join(root, "docs", "claims.csv"), headers: true)

bad = 0
fail_msg = ->(m) { puts "  FAIL: #{m}"; bad += 1 }

require_in_readme = ->(needle, what) {
  fail_msg.("README does not contain '#{needle}' (#{what})") unless readme.include?(needle)
}

require_in_readme.(claims.size.to_s, "total claim rows")

spec = claims.select { |r| r["build_value"].to_s != "" && r["reference_value"].to_s != "" }

spec.each do |r|
  bv = r["build_value"].to_f
  rv = r["reference_value"].to_f
  case r["id"]
  when "endurance"
    pct = 100.0 * (bv - rv) / rv
    require_in_readme.("#{pct.round(0).to_i}%", "endurance gain")
  when "weight"
    diff = (rv - bv).to_i
    require_in_readme.(diff.to_s, "weight saved")
  when "range"
    mult = bv / rv
    require_in_readme.("#{mult}x", "range multiple")
  end
end

if bad > 0
  puts "Ruby: #{bad} problem(s)"
  exit 1
end
puts "Ruby: #{claims.size} claims, counts and comparisons reproduced"
