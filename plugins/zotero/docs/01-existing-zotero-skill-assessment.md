# Existing Zotero skill: verified capabilities and limits

Assessment date: 2026-11-04. Target: **OpenAI's installed Zotero plugin 0.1.2**, not the separate `zotero-manager` starter created in this chat.

## How this was verified

Inspected the installed manifest, skill instructions, route reference, the Python command parser, and the implementations behind its commands. Checked current official Zotero documentation for local API writes and linked attachments. This assessment did not execute imports, request authorization, change settings, or modify Zotero records. “Implemented” below means present in inspected code; it does not mean every operation was tested against the live library.

Installed sources:

- [Skill instructions](../skills/zotero/SKILL.md)
- [Python helper](../skills/zotero/scripts/zotero.py)
- [Route reference](../skills/zotero/references/local-api-routes.md)
- [Plugin manifest](../.codex-plugin/plugin.json)

## What its commands can do

| Capability | Commands | Exact scope and limits |
|---|---|---|
| Check readiness | `status`, `probe` | Check local API/connector responses, preferences, version information, and route availability. `probe` reports response summaries, not a full library report. |
| Enable/disable the local API and restart Zotero | `enable`, `disable`, `restart` | Preference commands modify `prefs.js` after backing it up; optional restart. These are settings/app changes, not read-only commands. |
| List library entries | `inventory` | Lists top-level items by default; `--include-children` includes child items. Returns summaries. |
| Search entries | `search` | Searches `/users/0/items/top`. Output includes item key, type, title, creators, and year; optional exported BibTeX keys. Not a dedicated full-text search or advanced saved-search interface. |
| List collections and nesting | `collections` | Returns names, keys, parent collection, and version. Does not create or edit collections or list a selected collection's contents through a dedicated command. |
| List tags | `tags` | Tag names and item counts. No tag editing. |
| List visible group libraries | `groups` | Group identifiers, names, and types. The other commands are hardcoded to the personal-library prefix; group listing is not general group-library management. |
| List child notes and attachments | `children` | Returns the same item summaries as inventory. Does not output full note HTML or complete attachment metadata. |
| Read indexed attachment text | `fulltext` | Prints or saves text already indexed by Zotero. It does not itself OCR PDFs, extract unindexed text, or edit PDFs. |
| Locate an attachment | `file-url` | Returns Zotero's file-view URL for an existing attachment key. Does not create, relink, move, or open the file itself. |
| Export BibTeX | `export-bibtex`, `sync-bib` | Exports one item or the personal library. Supports optional child inclusion and local output files. `sync-bib` writes an export; it is not bidirectional synchronization. |
| Format citations | `citations` | Requests style-based citation rendering for personal-library top-level entries. |
| Insert draft citations | `cite` | Inserts a citation into LaTeX/Markdown and appends a missing BibTeX entry. An existing entry with the same BibTeX key is not refreshed. With an ambiguous query it warns and uses the first match; resolve identity and use an item key for precision. |
| Identify import destination | `selected-target` | Queries the currently selected library/collection through the connector. Uses HTTP POST but does not add or edit library records. |
| Add new references through import | `import-bibtex`, `import-ris` | Sends supplied text or a file to `/connector/import`, requiring `--yes`. Destination is the currently selected Zotero library/collection. No destination-key option, general item editor, or post-import read-back verification is implemented. |

Inspected helper SHA-256: `b914a88b9fdac185eff58bb8912c7c8f0ea5394a98282cbe1c3c42ab9617483a`.

All 20 command names are accounted for above. Source anchors: `build_parser`, `cmd_*`, `summarize_item`, `find_item`, `append_bib_entry`, and `export_bibtex` in the helper.

## What it does not implement as ready-to-use commands

| Task | Status in the bundled helper |
|---|---|
| Edit an existing record's title, creators, date, DOI, item type, or publication fields | No management command. Importing a corrected citation is not a supported update-in-place workflow. |
| Create a new reference directly from structured item JSON | No dedicated command; BibTeX/RIS import is available instead. |
| Create, rename, reparent, or delete collections | No commands. |
| Add/remove existing collection memberships or move entries between collections | No commands. |
| Create/edit notes, tags, and related-item links | No dedicated management commands. Imported records may carry some such data according to the translator/source; that does not provide general editing. |
| Add a linked local PDF or stored-file attachment | No attachment-creation command. |
| Repair attachment links, rename/move files, or coordinate paths | No workflow. |
| Detect and merge duplicates | No duplicate-management workflow. An agent could analyze retrieved data separately, but that is not an implemented merge command. |
| Audit missing metadata, perform bulk edits, or manage trash/restore | No dedicated workflows. |
| Create/edit/delete saved searches | No commands. `probe` merely checks the searches route. |
| Manage group permissions, accounts, or general app settings | No workflow; the local-API preference/restart commands above are the limited settings exception. |
| Edit PDF contents or highlighting | No commands; these are also excluded from the proposed new skill. |

Important precision: the script has general Python `request()` and `api_get()` functions. Custom code can use these to fetch full item JSON or send other requests. That is different from a documented, validated management command. Absence from the helper is not proof that Zotero cannot perform a task.

## Correction: Zotero 10 local API writes are supported

The installed route reference says: “The local API is read-only; write requests are not supported there.” That statement is outdated for Zotero 10. The installed application reported **10.0.7** during an earlier read-only check in this chat.

Official documentation confirms reads need no key when the local API is enabled. Writes need a user-granted local key obtained through `POST /api/local/authorize`, the instance's `Zotero-Server-ID`, and appropriate local-version preconditions. Access may be single-use or remembered. The bundled helper implements none of this authorization/version-management workflow. [Official local API documentation](https://www.zotero.org/support/dev/web_api/v3/local_api)

## The linked-PDF workflow the user wants

Zotero supports a child attachment pointing to a PDF at a user-chosen filesystem path. It references the original file rather than storing another copy; double-clicking the attachment opens it. The file must exist at the linked path. If moved or renamed later, its link needs updating. Zotero does not sync the linked file itself, and linked files are unavailable in group libraries. [Official attachment documentation](https://www.zotero.org/support/attaching_files)

**Conclusion:** Zotero supports this workflow; the bundled helper has no linked-file command. The new manager is separate from this bundled helper. Its linked-PDF creation workflow was successfully live-tested on disposable records on 2026-11-04.
