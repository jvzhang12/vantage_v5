# `src/vantage_v5/services/vector_index.py`

Persistent local vector index for Vantage Attention retrieval.

## Purpose

- Provide a pluggable `VectorIndex` interface for semantic retrieval.
- Persist per-scope resource embeddings in SQLite so each user profile can keep an isolated local vector store.
- Keep the first backend dependency-free by storing sparse token-vector embeddings as JSON.

## Core Data Flow

- `VectorDocument` captures the compact resource text and metadata that should be embedded.
- `SQLiteVectorIndex.sync()` upserts changed resources into `state/vector_index.sqlite3`.
- `SQLiteVectorIndex.query()` embeds the user query, scans stored vectors, and returns ranked `VectorHit` records.
- `AttentionEngine` uses these hits as one hybrid ranking signal alongside deterministic keys, timestamps, visible-artifact priority, app policy, and recency.

## Important Boundaries

- This is a local persistent vector backend, not the final embedding provider.
- The embedding provider is replaceable, so remote or model-backed embeddings can be added without changing the Attention/Navigator contract.
- The vector index does not choose final context; Navigator still selects from the hybrid shortlist.

