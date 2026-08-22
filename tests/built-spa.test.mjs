import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import test from "node:test";

const staticDir = fileURLToPath(new URL("../backend/static/", import.meta.url));

async function bundle() {
  const assets = await readdir(`${staticDir}assets`);
  const script = assets.find((name) => name.endsWith(".js"));
  assert.ok(script, "expected a built JavaScript bundle");
  return readFile(`${staticDir}assets/${script}`, "utf8");
}

test("builds an SPA shell with product metadata", async () => {
  const html = await readFile(`${staticDir}index.html`, "utf8");

  assert.match(html, /<title>RepoLens — Codebase Intelligence<\/title>/i);
  assert.match(html, /<div id="root">/);
  assert.match(html, /property="og:image" content="\/og-repolens\.png"/);
  assert.match(html, /<script type="module" [^>]*src="\/assets\/[^"]+\.js"/);
});

test("ships the landing page copy in the client bundle", async () => {
  const code = await bundle();

  assert.match(code, /Understand any codebase/);
  assert.match(code, /Analyze repository/);
  assert.match(code, /https:\/\/github\.com\/Shreyakb301\/RepoLens/);
});

test("calls the API on the same origin", async () => {
  const code = await bundle();

  // The SPA is served by FastAPI, so requests are same-origin `/api/*` paths
  // and no proxy or CORS allowlist is involved.
  assert.match(code, /\/api\/analyze/);
  assert.doesNotMatch(code, /onrender\.com/);
});
