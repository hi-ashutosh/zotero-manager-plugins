# Zotero Manager

Manage Zotero metadata, collections, tags and linked PDFs from Codex or the Python CLI. This fork retains the original Zotero helper and adds the separate `zotero-manager` skill.

## Start here

**[Complete user guide: setup, features, examples, permissions and troubleshooting](skills/zotero-manager/README.md)**

The guide is included inside the skill folder, so it remains available when the skill is installed separately.

## Current features

- Create references and edit selected metadata.
- Create/nest/rename collections and change collection memberships.
- Add/remove item tags while preserving other tags and their types.
- Link an existing local PDF to a reference.
- Relink an existing PDF attachment when its file location changes.
- Reuse search, inventory, exports, citations, imports and indexed-text lookup.

New management writes support previews, recovery journals, version checks and read-back verification. See the guide for inherited-command exceptions and exact limits.

## Status and source

- Development branch: **`feat/zotero-manager`**, not `main`.
- Skill: starter 0.2.0; **29 offline tests and 21 live assertions** on macOS/Zotero 10.0.7.
- [Test coverage](skills/zotero-manager/references/validation.md)
- [Agent instructions](skills/zotero-manager/SKILL.md)
- [Feature plan](docs/02-new-skill-features-and-priorities.md)
- [Assessment of the original helper](docs/01-existing-zotero-skill-assessment.md)

No screenshots or computer control are required. Local Zotero write authorization is required for management changes. This is a maintained fork, not an official OpenAI release; no stable release or upstream pull request has been published.
