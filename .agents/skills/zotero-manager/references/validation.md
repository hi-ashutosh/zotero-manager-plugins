# Validation status

Starter 0.2.0. Live-tested on 2026-11-04 with Zotero Desktop 10.0.7 using its local API. No screenshots or computer control were used.

## Live-verified core behavior

A final disposable-fixture run passed all 21 assertions:

1. Create root and nested collections.
2. Rename a collection while preserving its parent.
3. Create a structured journal-article reference.
4. Preview an edit without changing the reference.
5. Edit title, date, DOI and author.
6. Preserve collection membership during metadata edits.
7. Move between collections while retaining unrelated membership.
8. Remove collection membership without deleting the library item.
9. Add collection membership.
10. Create a linked child PDF and verify its resolved file path.
11. Avoid creating a second attachment for the same resolved PDF path.
12. Leave the PDF bytes unchanged.
13. Preview tag changes without changing tags.
14. Add/remove tags while preserving an unrelated automatic tag.
15. Preserve metadata and collection memberships during tag changes.
16. Avoid writes when asked to add an existing tag or remove an absent one.
17. Preview a replacement path without changing the attachment.
18. Repair a broken PDF link using an existing replacement PDF.
19. Preserve attachment key, parent, title and child count when relinking.
20. Recognize the relinked path as the existing attachment.
21. Preserve the bytes of both PDFs during relinking.

All three temporary collections, the temporary reference and linked attachment were deleted, and each deletion was verified by a 404 read. The original generated PDF (including its moved test path) and the replacement PDF were removed. Prior failed runs were also cleaned up. Existing library records were not test targets.

The first live attempt exposed a real create bug: client-generated keys also require `version: 0`. The helper now includes that precondition, and an offline regression test covers it. A separate test assertion was corrected to compare resolved paths because macOS can represent the same location through `/var` and `/private/var`.

## Offline and inherited coverage

29 offline tests pass. These cover previews, metadata/membership preservation, collection PUT/version behavior, private server-bound credentials, stale-write handling, per-object failures, recovery-key journaling, keyed-create preconditions, local schema templates, linked-PDF path/duplicate/error cases, incremental tag preservation and no-ops, and relinking validation/previews/identity preservation.

The original search/export/import/citation helper is reused unchanged; not every inherited command was re-tested. Note workflows, bulk/library-wide tag renaming, other item types, item-type conversion, group writes, actual viewer opening and all deferred features remain outside this live test's coverage. Resolving a linked file through the API does not verify double-click UI behavior.

## Running the tests

Offline: `python3 -B -m unittest discover -s <skill-dir>/tests -v`.

Live: `python3 -B <skill-dir>/tests/live_smoke.py --apply`, only when the user authorizes disposable-record tests. Without `--apply` the harness exits without connecting or writing. It generates unique fixture markers, saves intended keys before writes, checks those markers before cleanup, and retains its local report for recovery. It uses the normal private credential state; it never prints authorization keys. Single-use access may require further user-clicked Zotero dialogs. If cleanup fails, the report lists remaining keys and retains the test PDF.

## Fork provenance

- Upstream: `openai/plugins`, commit `b767f8f` (the fork's initial base).
- Working fork: https://github.com/hi-ashutosh/zotero-manager-plugins, branch `feat/zotero-manager`.
- `scripts/zotero_legacy.py` is an unchanged copy of the upstream Zotero helper at that base.
- The new manager is separate; the original Zotero skill remains available.

## Added commands (2026-11-04)

`edit-tags` and `relink-file` were live-tested on Zotero 10.0.7 through the local API. Relinking was tested with the old file deliberately absent, using only generated test files. No screenshots, UI control or existing-paper modifications were involved. Commands still default to preview and require `--apply` to write.
