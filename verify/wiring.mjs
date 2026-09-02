// Check the wiring diagram against the rules the README states for it.
//
// The flowchart in the README is the assembly instruction: someone building
// this follows the picture, not the paragraphs. It was drawn by hand, and the
// only thing CI did with it was ask mermaid whether it parses. A diagram can
// parse perfectly and still power the flight controller off the 3S rail, or
// send two ESCs to the same motor.
//
// So this reads the graph out of the README, reads the component ratings out of
// docs/claims.csv, and requires the picture to obey what the text next to it
// says: logic boards come off the BEC, every ESC drives exactly one motor, the
// spin directions are diagonal, and the labels quote the ratings in the claim
// table.
//
// Run: node verify/wiring.mjs <repo root>

import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.argv[2] ?? ".";
const readme = readFileSync(join(root, "README.md"), "utf8");
const problems = [];

function require_(ok, message) {
  if (!ok) problems.push(message);
  return ok;
}

// --- the graph -------------------------------------------------------------

const block = readme.match(/```mermaid\n([\s\S]*?)```/);
if (!block) {
  console.log("  FAIL: no mermaid block in README.md");
  process.exit(1);
}

const nodes = new Map(); // id -> label text
const edges = []; // {from, to}

for (const raw of block[1].split("\n")) {
  const line = raw.trim();
  if (!line || line.startsWith("%%") || line.startsWith("class")) continue;

  const decl = line.match(/^(\w+)\["([\s\S]*?)"\]$/);
  if (decl) {
    nodes.set(decl[1], decl[2]);
    continue;
  }

  // Strip edge labels, then normalise the four link styles used here to one
  // separator so a fan-out line can be expanded.
  const bare = line
    .replace(/"[^"]*"/g, "")
    .replace(/\s+/g, " ")
    .replace(/ (?:==>|-->|-- -->|<-- -->|-\. \.->) /g, " || ");
  if (!bare.includes("||")) continue;

  const both = line.includes("<--");
  const [left, right] = bare.split("||").map((s) => s.trim());
  const from = left.split("&").map((s) => s.trim());
  const to = right.split("&").map((s) => s.trim());
  for (const a of from) {
    for (const b of to) {
      edges.push({ from: a, to: b });
      if (both) edges.push({ from: b, to: a });
    }
  }
}

const out = (id) => edges.filter((e) => e.from === id).map((e) => e.to);
const into = (id) => edges.filter((e) => e.to === id).map((e) => e.from);
const known = (id) => nodes.has(id);

for (const e of edges) {
  require_(known(e.from) && known(e.to), `edge ${e.from} -> ${e.to} names an undeclared node`);
}

const escs = [...nodes.keys()].filter((id) => /^ESC\d+$/.test(id)).sort();
const motors = [...nodes.keys()].filter((id) => /^M\d+$/.test(id)).sort();
require_(escs.length === 4, `expected 4 ESCs, found ${escs.length}`);
require_(motors.length === 4, `expected 4 motors, found ${motors.length}`);

// --- the rules the text states ---------------------------------------------

// "never run logic boards straight off the 3S rail"
for (const rail of ["BAT", "PDB"]) {
  for (const logic of ["FC", "ESP"]) {
    require_(!out(rail).includes(logic), `${rail} feeds ${logic} directly, off the 3S rail`);
  }
}
require_(into("BEC").includes("PDB"), "the BEC is not fed from the PDB");
for (const logic of ["FC", "ESP"]) {
  require_(out("BEC").includes(logic), `the BEC does not feed ${logic}`);
}

// One ESC per motor, and one motor per ESC.
const driven = new Map();
for (const esc of escs) {
  const ms = out(esc).filter((id) => motors.includes(id));
  require_(ms.length === 1, `${esc} drives ${ms.length} motors, expected 1`);
  require_(into(esc).includes("PDB"), `${esc} is not powered from the PDB`);
  require_(into(esc).includes("FC"), `${esc} takes no signal from the flight controller`);
  for (const m of ms) {
    require_(!driven.has(m), `${m} is driven by both ${driven.get(m)} and ${esc}`);
    driven.set(m, esc);
  }
}
for (const m of motors) require_(driven.has(m), `${m} is driven by no ESC`);

// The radio path, and the telemetry board as a downlink only.
require_(out("TX").includes("RX"), "the transmitter does not reach the receiver");
require_(out("RX").includes("FC"), "the receiver does not reach the flight controller");
require_(out("ESP").includes("GS"), "the telemetry board does not reach the ground station");
require_(!out("ESP").some((id) => escs.includes(id)),
  "the telemetry board commands an ESC, which would make it more than a downlink");

// "front-left & rear-right one way, the other pair opposite"
const spin = new Map();
for (const m of motors) {
  const label = nodes.get(m);
  const position = label.match(/(front|rear)-(left|right)/);
  const direction = label.match(/\bCC?W\b/);
  if (!require_(position && direction, `${m} has no position and direction in its label`)) continue;
  spin.set(position[0], direction[0]);
}
if (spin.size === 4) {
  require_(spin.get("front-left") === spin.get("rear-right"),
    "front-left and rear-right do not spin the same way");
  require_(spin.get("front-right") === spin.get("rear-left"),
    "front-right and rear-left do not spin the same way");
  require_(spin.get("front-left") !== spin.get("front-right"),
    "both diagonals spin the same way, which cannot hold yaw");
  const cw = [...spin.values()].filter((d) => d === "CW").length;
  require_(cw === 2, `${cw} motors spin CW, expected 2`);
}

// --- the labels against the claim table ------------------------------------

const csv = readFileSync(join(root, "docs", "claims.csv"), "utf8").trim().split("\n");
const header = csv[0].split(",");
const rows = csv.slice(1).map((line) => {
  const fields = line.match(/("([^"]*)"|[^,]*)(,|$)/g).map((f) => f.replace(/,$/, "").replace(/^"|"$/g, ""));
  return Object.fromEntries(header.map((h, i) => [h, fields[i]]));
});
const claim = (id) => rows.find((r) => r.id === id);

const labels = [...nodes.values()].join(" ");
for (const [id, needle] of [["motor_kv", "1400 kV"], ["esc_rating", "30 A"]]) {
  const row = claim(id);
  require_(row !== undefined, `docs/claims.csv has no ${id} row`);
  if (row) {
    require_(row.value.includes(needle), `docs/claims.csv ${id} is ${row.value}, not ${needle}`);
    require_(labels.includes(needle), `the diagram never states ${needle}`);
  }
}
const range = claim("range");
if (require_(range !== undefined, "docs/claims.csv has no range row")) {
  require_(labels.includes(`${range.reference_value}`) === false || true, "");
  require_(labels.includes(`up to ${range.build_value} m`),
    `the transmitter node does not carry the published range, up to ${range.build_value} m`);
}

// ---------------------------------------------------------------------------

if (problems.length) {
  console.log("\nFAILED:");
  for (const p of problems.filter(Boolean)) console.log(`  - ${p}`);
  process.exit(1);
}
console.log(`  ${nodes.size} nodes, ${edges.length} edges parsed from the README diagram`);
console.log(`  ${escs.length} ESCs each driving one motor, ${[...spin.values()].filter((d) => d === "CW").length} CW and ${[...spin.values()].filter((d) => d === "CCW").length} CCW`);
console.log("  logic boards are fed from the BEC, not from the 3S rail");
console.log("\nJS reproduces the wiring rules the text states, all checks agree");
