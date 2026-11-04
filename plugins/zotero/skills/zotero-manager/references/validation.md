# Validation status

Starter 0.1.0, developed 2026-11-03.

- Nineteen offline tests pass: previews perform no writes, edits preserve unrelated fields and journal previous metadata, collection moves preserve unrelated memberships, contradictory membership is rejected, verification mismatches fail, managed version edits are rejected, credentials are private and server-bound, membership comparison tolerates order changes, stale writes are not retried, single-use credentials are discarded after failed attempts, per-object create failures are detected with recovery keys journaled, and templates use local schema routes.
- Installed Zotero 10.0.7 local API confirmed available. Read-only live checks verified create previews and the schema-based manuscript template. The first authorization dialog timed out without returning a key; no live write tests were run and no library records were changed. Creating/editing records, collections, and linked attachments are implemented and offline-tested but NOT yet validated through actual Zotero writes.
- Opening attachments by double-click is documented Zotero behavior; automated UI opening is not tested.
- Legacy search/export/import/citation commands are vendored from OpenAI's installed 0.1.2 helper; not all are re-tested here.
- Specialized features listed as deferred in SKILL.md are not implemented.

## Fork provenance

- Upstream: `openai/plugins`, commit `b767f8fa3be1a22b093127dd59956c91ecffca9d`.
- Working fork: https://github.com/hi-ashutosh/zotero-manager-plugins, branch `feat/zotero-manager`.
- `scripts/zotero_legacy.py` is an unchanged copy of the upstream Zotero helper at that commit.
- New management code is separate, leaving the original Zotero skill available.

## Fork development checks (2026-11-04)

19 offline tests pass. Added focused coverage for collection rename preservation/versioning, linked-PDF preview without file copies, duplicate links, invalid attachment parents, missing PDFs, attachment-base-directory normalization, and mismatched resolved file URLs. The PDF fixtures only exercise paths; they do not validate PDF rendering. No Zotero API calls or library writes were made by this test run. Live write verification remains pending.
