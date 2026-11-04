# Zotero Manager: desired features and implementation priorities

Planning baseline: 2026-11-04. Companion: [existing-skill assessment](01-existing-zotero-skill-assessment.md).

## Goal and working scope

Build a separately maintained `zotero-manager` skill for ordinary library management, reusing the bundled helper's useful functionality. Extend executable code, not only instructions. Exclude PDF-content editing and highlighting. Start with the personal library; investigate additional library types separately.

The initial target is approximately **30 minutes of focused work**, with usage efficiency prioritized. This is a scope budget, not a guarantee that every feature will be live-verified in that period. Prefer a small usable core over broad feature claims.

Fork setup and focused offline development are authorized. Live Zotero write testing was subsequently authorized and completed on disposable fixtures; see the results below.

## First priority: a usable core

The following are the first implementation priorities. Code for several already exists in the starter; completing a priority includes validating its actual behavior, not rewriting code that is already present.

| Order | Feature | Minimum acceptance criterion | Current evidence |
|---|---|---|---|
| 1 | Reliable reads and controlled writes | Resolve exact item/collection identity; preview changes; use local authorization, server ID, and object versions; preserve previous metadata; read back results; report failures without blind retries. | Implemented infrastructure. Several failure/preservation cases have offline tests. Live reads and the disposable-fixture write sequence verified on Zotero 10.0.7. |
| 2 | Edit existing reference metadata | Change selected fields, including title, authors, date, DOI and publication details, while preserving unrelated data. Treat item-type changes carefully because fields may become incompatible. | `edit-item` exists. Live-tested title, author, date and DOI edits with unrelated membership preserved. Other field types and item-type conversion remain unverified. |
| 3 | Create and rename collections | Create a collection, optionally under a parent; rename an existing collection without changing membership. Reparenting is useful if the same supported workflow permits it. | `create-collection` and `edit-collection` live-tested for root/nested creation and rename with parent preservation. |
| 4 | Add/remove/move collection membership | Add destination and remove source in one update when moving; preserve every unrelated membership; never delete the library entry. | `membership` exists; preservation and contradictory-input cases tested offline. Live-tested on disposable records. |
| 5 | Create new references | Add a structured metadata record to the intended collection and return its key; retain BibTeX/RIS imports. Check for likely existing records before creating a duplicate. | `create-item` and inherited imports exist. Structured journal-article creation and preview live-tested. Duplicate-reference screening remains unimplemented. No dedicated duplicate-screening command. |
| 6 | Link a chosen local PDF to an entry | Create a child linked-file attachment to an existing PDF, avoid another link to the same resolved path, and verify Zotero resolves it to the supplied file. Confirm opening behavior during live testing. | `link-file` exists with path checks, duplicate-link checks and file-URL verification code. Focused offline tests now cover linked-file paths, duplicates, missing files, parent validation and file-URL verification. Linked attachment creation, path resolution, unchanged file contents and duplicate prevention live-tested. |
| 7 | Preserve existing useful workflows | Keep search, inventory, BibTeX export, citations, indexed text, and attachment-location lookup available. | Bundled helper copied as `zotero_legacy.py`; commands delegated. Not all inherited commands re-tested. |

When time is tight, complete and verify items 1–4 first. New-reference imports already exist as a fallback for item 5. Linked PDFs remain a core user request, but must be labeled unverified if time or authorization prevents testing.

## Later features

| Priority | Desired feature | Scope and current gap |
|---|---|---|
| Next | Notes | Create/edit child and standalone notes. Generic item JSON may express these already; dedicated workflows and tests are still needed. |
| Next | Tags | Add/remove/rename tags while preserving unrelated tags. Generic JSON array replacement exists; dedicated incremental tag management is missing. |
| Next | Related items | Manage relationships while preserving existing links; verify relationship semantics and any reciprocal updates required. |
| Next | Missing-metadata checks | Report missing/implausible fields with proposed corrections and sources; apply only authorized changes. |
| Next | Bulk edits | Preview affected items, define partial-failure behavior, and journal originals. Not implemented as a bulk workflow. |
| Next | Trash and restore | Distinguish reversible trash from permanent deletion and collection removal. No dedicated workflow yet. |
| Later / investigate | Saved searches | Create/edit/delete searches and read results using supported routes. Not implemented. |
| Later / investigate | Stored-file attachments | Add managed file copies using a supported upload/import workflow; distinguish from linked files. Not implemented. |
| Later / investigate | Attachment-path repair | Detect missing paths and relink to an identified replacement; verify before/after locations. No dedicated repair workflow. |
| Later / investigate | Filename and filesystem coordination | Rename/move PDFs and update Zotero references without editing PDF contents; plan recovery for partial failure. Not implemented. |
| Later / investigate | Duplicate detection and merging | Detection and actual Zotero merge semantics are separate features. Investigate supported merge methods and effects on notes, files, relations, and citation references before promising support. |
| Later / investigate | Group-library item management | Generalize from the personal-library prefix and respect permissions. Group listing alone is insufficient; linked files cannot be used in groups. |
| Deferred | GitHub fork, branch and releases | Maintain our source independently of the bundled cache; eventually publish/tag tested releases or contribute upstream. Fork created at https://github.com/hi-ashutosh/zotero-manager-plugins; development branch `feat/zotero-manager`. Changes are maintained there; no upstream pull request or release yet. |

Account administration, group permissions, and broad application-settings changes are outside the initial scope; some may remain outside the eventual skill's scope. PDF editing and highlighting are excluded, not pending features.

## Required behavior across features

- Use supported Zotero APIs; no direct SQLite writes.
- User authorization is task-specific. Discussion and planning do not authorize writes. Once a concrete task is authorized, avoid repeated confirmation for routine steps.
- Zotero's own key-granting dialog remains necessary for local API writes. Do not treat a remembered key as permission for an unrelated task.
- Preserve unrelated metadata and collection memberships; remember that JSON arrays can replace entire lists.
- Save previous metadata where useful for recovery. A snapshot is not a promise of automatic rollback, particularly after an item-type change or file operation.
- Verify each actual write and expose mismatches or partial failures. After a timeout, inspect the intended key before retrying a create.
- Keep credentials private and outside source control.
- Test new operations using disposable records, collections, and files before modifying existing papers. Clean up only the fixtures created for that test.
- For linked PDFs, use an existing file at the selected path. Moving it later requires relinking. Opening by double-click is Zotero behavior that the workflow should preserve. [Zotero file documentation](https://www.zotero.org/support/attaching_files)
- Label features separately as planned, code present, offline-tested, and live-verified. Do not use “tested” to imply that all four states are equivalent.

## Current starter: location and validation boundary

- Source: [zotero-manager](../skills/zotero-manager/SKILL.md).
- Bundled plugin remains unchanged.
- **20 offline tests pass in the fork.** They cover selected safety/preservation/error cases and local schema-template construction. This does not individually validate every new command.
- Earlier live read-only checks confirmed Zotero 10.0.7, create previews and the schema-based manuscript template. The standard `/api/items/new` template endpoint returned 404; the starter instead uses local field-schema routes.
- **Core management writes were live-tested on 2026-11-04 using Zotero 10.0.7.** The final run passed 12 assertions; all disposable records/collections and the generated PDF were cleaned up. The earlier authorization timeout was followed by successful user-granted authorization. Validation covers these specific operations, not every item type or future feature.

## Next work after the user authorizes resuming

Review the already-written implementation against the first-priority acceptance criteria. If live tests are authorized, obtain a local key through Zotero's dialog, then run a short create/edit/collection/membership/linked-PDF sequence on disposable fixtures and clean them up. Fix observed failures, update the validation record, and stop at the agreed time/usage budget rather than expanding into later features.

## Completed live test (2026-11-04)

The authorized CLI/API test used no computer control. It verified the core metadata, collection, membership and linked-PDF operations, then removed its own fixtures. A missing `version: 0` create precondition was found and fixed. Reusable live harness: `tests/live_smoke.py` in the manager skill. Existing papers were untouched. Viewer opening, duplicate-reference detection, item-type conversion, notes/tags and later features remain unverified by this test.
