# `src/vantage_v5/services/draft_artifact_lifecycle.py`

Backend lifecycle boundary for whiteboard save, snapshot, publish, promotion, saved-item reopen, and artifact lifecycle card enrichment.

## Purpose

- Hide the multi-step storage/executor sequences for whiteboard lifecycle operations behind one service.
- Keep `server.py` and local semantic actions from manually coordinating workspace saves, active-workspace state, artifact snapshots, artifact promotion, artifact fetches, saved-item reopen state, and artifact lifecycle presentation fields.
- Preserve existing response contracts by returning lifecycle result objects that the HTTP layer can serialize with the existing card serializers.

## Key Classes

- `artifact_lifecycle_card_fields()`: presentation helper that adds `artifact_origin` and `artifact_lifecycle` only for artifact records, centralizing card enrichment for server, Chat, and Scenario Lab serializers.
- `artifact_lifecycle_kind()`: convenience helper for learned-item rationale copy that needs the normalized lifecycle value.
- `DraftArtifactRuntime`: typed runtime wrapper for the workspace store, artifact store, state store, graph-action executor, and active scope.
- `DraftArtifactLifecycleResult`: result object containing the relevant workspace, executed action, artifact record, scope, and optional assistant message.
- `DraftArtifactLifecycle`: service with methods for reopening saved items into the whiteboard, saving visible whiteboard snapshots, publishing visible whiteboards, saving workspace updates, and promoting saved or unsaved whiteboard buffers into artifacts.

## Notable Behavior

- `open_saved_item_into_whiteboard()` delegates saved-item resolution to the graph executor, writes the reopened whiteboard into the active runtime scope, reloads the workspace document, and returns the same graph action shape as the older route-level implementation.
- `artifact_lifecycle_card_fields()` keeps card serializers from importing storage-level lifecycle parsing directly. The storage parser still recovers metadata from Markdown/frontmatter, but lifecycle owns which recovered fields are exposed on product cards.
- `save_visible_whiteboard_snapshot()` persists the whiteboard, makes it active, and creates a `whiteboard_snapshot` artifact.
- `publish_visible_whiteboard()` promotes the current visible whiteboard content into a `promoted_artifact` without first forcing a workspace save, matching the prior `/api/chat` local publish behavior.
- `promote_whiteboard_to_artifact()` can promote an unsaved browser buffer without creating a workspace file, preserving the user-visible promotion semantics.
