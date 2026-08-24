import fs from "node:fs";
import { JSDOM } from "jsdom";

// mermaid.parse() needs a DOM even though it renders nothing.
const dom = new JSDOM("<!doctype html><html><body></body></html>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
globalThis.Element = dom.window.Element;
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.SVGElement = dom.window.SVGElement;
globalThis.DOMPurify = undefined;

const mermaid = (await import("mermaid")).default;

const file = process.argv[2];
const src = fs.readFileSync(file, "utf8");
const blocks = [...src.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(m => m[1]);
if (blocks.length === 0) { console.log("no mermaid blocks found"); process.exit(0); }

mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });
let bad = 0;
for (const [i, code] of blocks.entries()) {
  try {
    await mermaid.parse(code);
    console.log(`mermaid block ${i + 1}: OK (${code.split("\n").length} lines)`);
  } catch (e) {
    bad++;
    console.error(`mermaid block ${i + 1}: FAILED\n  ${String(e.message).split("\n")[0]}`);
  }
}
process.exit(bad ? 1 : 0);
