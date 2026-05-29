# 06. Surfaces And Whiteboard

> Status: Current source of truth
> Note: Product language should say Whiteboard. Current implementation may still use `workspace_*` names for compatibility.

## Surface Roles

```text
Chat:
    default conversation surface

Whiteboard:
    live collaborative Markdown draft
    opened intentionally
    pending drafts/offers remain non-durable until accepted or saved

Vantage:
    guided inspection surface for Working Memory, Recall, Reasoning Path, Learned, Library previews, and receipts

Library:
    durable saved material: concepts, memories, artifacts, reference notes
    inspectable but not automatically in scope

Scenario Lab:
    explicit multi-branch reasoning mode
    not ordinary formatted chat
```

## Surface State Distinctions

```text
visible:
    user can see the surface or item

open:
    UI has opened the surface or item for inspection/work

selected:
    UI selection or inspection focus

pinned:
    explicit carry-forward context for future turns

in_scope:
    allowed to influence the current answer

editing:
    user and assistant are actively drafting or revising the item
```

Visible, open, and selected do not automatically mean pinned or in scope.

## Whiteboard Entry

```text
if user explicitly asks to open or draft in Whiteboard:
    open Whiteboard or draft there without redundant invitation

elif user asks for substantial work product and Whiteboard would help:
    offer Whiteboard draft or pending draft flow

else:
    stay in chat
```

The Whiteboard should feel like a drafting mode, not an unavoidable side panel.

## Whiteboard Scope

```text
function whiteboard_in_scope(turn):
    if user explicitly references current draft:
        return true
    if Whiteboard is active and user is continuing the draft:
        return true
    if Whiteboard is pinned:
        return true
    if user asks unrelated chat and Whiteboard is only visible:
        return false
```

Do not silently ground normal chat in stale Whiteboard content.

## Inspect-Only Library Behavior

```text
if user opens Library item:
    show item for inspection
    do not pin automatically
    do not include in future Working Memory unless pinned or explicitly referenced
```

For artifacts:

```text
if user wants to continue editing saved artifact:
    require explicit "reopen in Whiteboard" or equivalent continuation action
```

## Close And Preserve

```text
if user asks to close/hide surface:
    close visible surface
    do not delete saved data
    block unrelated writes for that turn unless separately explicit and safe

if user asks to keep/leave open:
    preserve current surface
    do not reopen another item just because recall found one
```

Surface commands are UI state commands first, not storage mutations.

## Scenario Lab

```text
if Navigator routes to Scenario Lab:
    create branch outputs and comparison artifact according to Scenario Lab contract
elif user asks follow-up about an existing comparison:
    prefer chat continuity with pinned/selected context unless user asks to rerun
```

Scenario Lab is current, but it should stay explicit and distinct from ordinary chat and Whiteboard drafting.
