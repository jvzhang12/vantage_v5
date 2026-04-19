import test from "node:test";
import assert from "node:assert/strict";

import {
  deriveWhiteboardDecisionPresentation,
  isWhiteboardFocused,
  shouldHideChatWorkspaceUpdate,
} from "../src/vantage_v5/webapp/whiteboard_decisions.mjs";

test("isWhiteboardFocused only when whiteboard is visible and Vantage is closed", () => {
  assert.equal(isWhiteboardFocused({ current: "whiteboard", returnSurface: "chat" }), true);
  assert.equal(isWhiteboardFocused({ current: "vantage", returnSurface: "whiteboard" }), false);
  assert.equal(isWhiteboardFocused({ current: "chat", returnSurface: "chat" }), false);
});

test("local pending decision exposes replace-or-keep actions for destructive whiteboard opens", () => {
  const presentation = deriveWhiteboardDecisionPresentation({
    view: { current: "whiteboard", returnSurface: "chat" },
    localDecision: {
      kind: "open_record",
      targetLabel: "Rules of Hangman (game)",
    },
  });

  assert.equal(presentation.visible, true);
  assert.equal(presentation.label, "Replace Current Whiteboard?");
  assert.deepEqual(
    presentation.actions.map((action) => action.id),
    ["replace_current", "cancel_decision"],
  );
});

test("pending draft replacement keeps replace, append, and keep-current choices non-destructive", () => {
  const presentation = deriveWhiteboardDecisionPresentation({
    view: { current: "whiteboard", returnSurface: "chat" },
    localDecision: {
      kind: "pending_draft_replace",
      targetLabel: "Draft Plan",
    },
  });

  assert.equal(presentation.visible, true);
  assert.equal(presentation.label, "Replace Current Whiteboard?");
  assert.deepEqual(
    presentation.actions.map((action) => action.id),
    ["replace_current", "append_instead", "cancel_decision"],
  );
});

test("whiteboard offers become open-or-keep decisions when the whiteboard is focused", () => {
  const presentation = deriveWhiteboardDecisionPresentation({
    view: { current: "whiteboard", returnSurface: "chat" },
    workspaceUpdate: {
      status: "offered",
      summary: "Vantage suggested continuing this work in the whiteboard.",
      content: "",
    },
  });

  assert.equal(presentation.visible, true);
  assert.equal(presentation.label, "Whiteboard Offer");
  assert.deepEqual(
    presentation.actions.map((action) => action.id),
    ["open_offer", "keep_in_chat"],
  );
});

test("draft-ready updates expose replace, append, and keep-current actions in the whiteboard", () => {
  const presentation = deriveWhiteboardDecisionPresentation({
    view: { current: "whiteboard", returnSurface: "chat" },
    workspaceUpdate: {
      status: "draft_ready",
      summary: "A new whiteboard draft is ready.",
      content: "# Draft",
      decision: null,
    },
  });

  assert.equal(presentation.visible, true);
  assert.equal(presentation.label, "Whiteboard Draft Ready");
  assert.deepEqual(
    presentation.actions.map((action) => action.id),
    ["apply_draft", "append_draft", "keep_current"],
  );
});

test("unknown local decisions fall back to the server draft decision instead of hiding it", () => {
  const presentation = deriveWhiteboardDecisionPresentation({
    view: { current: "whiteboard", returnSurface: "chat" },
    localDecision: {
      kind: "unexpected_local_state",
    },
    workspaceUpdate: {
      status: "draft_ready",
      summary: "A new whiteboard draft is ready.",
      content: "# Draft",
      decision: null,
    },
  });

  assert.equal(presentation.visible, true);
  assert.equal(presentation.label, "Whiteboard Draft Ready");
});

test("chat-side workspace updates stay hidden while the whiteboard owns the decision surface", () => {
  const hidden = shouldHideChatWorkspaceUpdate({
    view: { current: "whiteboard", returnSurface: "chat" },
    workspaceUpdate: {
      status: "draft_ready",
      content: "# Draft",
      decision: null,
    },
  });

  assert.equal(hidden, true);
});

test("resolved workspace decisions stay hidden in chat once the user already chose a path", () => {
  const hidden = shouldHideChatWorkspaceUpdate({
    view: { current: "chat", returnSurface: "chat" },
    workspaceUpdate: {
      status: "draft_ready",
      content: "# Draft",
      decision: "applied",
    },
  });

  assert.equal(hidden, true);
});
