import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const webappRoot = path.join(repoRoot, "src", "vantage_v5", "webapp");

function readWebappFile(filename) {
  return readFileSync(path.join(webappRoot, filename), "utf8");
}

function tagWithId(markup, id) {
  return [...markup.matchAll(/<[^>]+>/g)]
    .map((match) => match[0])
    .find((tag) => tag.includes(`id="${id}"`)) || "";
}

test("draft operation feedback uses a dedicated polite status node", () => {
  const html = readWebappFile("index.html");
  const statusTag = tagWithId(html, "draftOperationStatus");
  const workspaceMetaTag = tagWithId(html, "workspaceMeta");

  assert.ok(statusTag, "expected draftOperationStatus node");
  assert.match(statusTag, /\brole="status"/);
  assert.match(statusTag, /\baria-live="polite"/);
  assert.match(statusTag, /\baria-atomic="true"/);
  assert.doesNotMatch(workspaceMetaTag, /\baria-live=/);
});

test("draft-local success feedback is inline instead of global toast", () => {
  const app = readWebappFile("app.js");
  const applyDraftBody = app.slice(
    app.indexOf("async function applyPendingWorkspaceUpdate"),
    app.indexOf("function appendWorkspaceDraft"),
  );

  assert.doesNotMatch(app, /pushNotice\("Draft saved"/);
  assert.doesNotMatch(app, /pushNotice\("Draft opened"/);
  assert.doesNotMatch(app, /pushNotice\("Draft ready"/);
  assert.match(app, /setDraftOperationStatus\("Draft saved"/);
  assert.match(app, /setDraftOperationStatus\("Draft opened"/);
  assert.match(app, /setDraftOperationStatus\("Draft ready"/);
  assert.match(applyDraftBody, /setDraftOperationStatus\(/);
  assert.doesNotMatch(applyDraftBody, /tone:\s*"success"/);
});

test("edited top-level assets have bumped cache keys", () => {
  const html = readWebappFile("index.html");

  assert.match(html, /\/static\/styles\.css\?v=20260513-visible-artifacts/);
  assert.match(html, /\/static\/app\.js\?v=20260513-visible-artifacts/);
});
