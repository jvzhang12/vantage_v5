# `src/vantage_v5/storage/vault.py`

This module reads vault notes directly from an external Obsidian-style vault rather than from the app’s own record directories. `VaultNoteStore` walks Markdown files under `vault_root`, filters them by include and exclude prefixes, and returns `VaultNoteRecord` objects with extracted metadata, summary card text, and file provenance.

Each note record captures the note ID, title, type, card, cleaned body text, relative path, folder, tags, modified timestamp, and absolute path. IDs are deterministic and derived from the relative path using a slug plus a SHA-1 digest, so the same file path always maps to the same vault-note ID. Titles come from frontmatter `title` or `name`, then a first Markdown heading, and finally the filename stem.

Persistence here is read-only from the store’s perspective. It never writes vault notes, only scans them, parses optional YAML frontmatter, and converts them into searchable card dictionaries. The important constraints are that only `.md` files are considered, frontmatter must be well-formed to be read as metadata, and include/exclude rules operate on relative path prefixes.
