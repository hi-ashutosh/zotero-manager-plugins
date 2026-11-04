# Zotero Manager

A Codex skill for managing a **personal Zotero Desktop library** through Zotero's local API. Describe the task in ordinary language, or run the Python helper directly. No screenshot access or computer control is required.

This is a community-maintained extension of [OpenAI's Zotero plugin](https://github.com/openai/plugins/tree/main/plugins/zotero), developed in [hi-ashutosh/zotero-manager-plugins](https://github.com/hi-ashutosh/zotero-manager-plugins). **Use branch `feat/zotero-manager`: the fork's `main` branch does not yet contain these additions.** No upstream pull request or stable release has been published.

**Current skill:** starter 0.2.0. **Validation:** 29 offline tests and 21 live assertions on macOS with Zotero 10.0.7. Other operating systems and untested workflows are not covered by that claim. [Detailed test coverage](references/validation.md).

## Contents

- [Features and limits](#features-and-limits)
- [Install and first use](#install-and-first-use)
- [Permissions and previews](#permissions-and-previews)
- [Use it in Codex](#use-it-in-codex)
- [Command-line guide](#command-line-guide)
- [PDF linking and relinking](#pdf-linking-and-relinking)
- [Troubleshooting and recovery](#troubleshooting-and-recovery)
- [Updates, tests and project files](#updates-tests-and-project-files)

## Features and limits

| Task | How to use it | Coverage |
|---|---|---|
| Create references | `create-item` with structured item JSON; inherited BibTeX/RIS imports also available | Direct journal-article creation live-tested; imports inherited |
| Edit metadata | `edit-item`: title, creators, dates, DOI and other valid item fields | Title, author, date and DOI live-tested; not every field/type combination |
| Create and organize collections | `create-collection`, `edit-collection` | Root/nested creation and rename live-tested; reparenting implemented, not separately live-tested |
| Add/remove/move collection membership | `membership` | Live-tested; preserves unrelated memberships |
| Add/remove tags on one item | `edit-tags` | Live-tested; preserves unrelated tags and automatic/manual types |
| Attach a local PDF by reference | `link-file` | Live-tested; verifies path and avoids duplicate links to that path |
| Repair an existing linked PDF's path | `relink-file` with an attachment key and replacement PDF | Live-tested with the original file missing; retains attachment identity |
| Search/list entries, collections and tags | `search`, `inventory`, `collections`, `tags` | Inherited helper; search/list output is summarized |
| Inspect complete records | `get items`, `get collections` | Used by the live-tested workflows |
| Read indexed text and attachment locations | `children`, `fulltext`, `file-url` | Inherited; `children` gives summaries, not full note text |
| Export and cite | `export-bibtex`, `sync-bib`, `citations`, `cite` | Inherited; not all commands re-tested here |
| List visible groups | `groups` | Listing only; the management commands target the personal library |

**Not implemented as dedicated workflows:** duplicate detection/merging, automatic metadata completion, bulk edits, library-wide tag renaming, saved-search management, stored-file uploads, automatic missing-file discovery, physical PDF renaming/moving, trash/restore, account administration and group permissions. Notes and relationships can be expressed through generic item JSON, but lack dedicated validated workflows. PDF-content editing and highlighting are excluded.

Item-type changes may discard fields that are invalid for the new type. They are not part of the live-verified metadata edits. Review the preview and recovery snapshot before attempting them.

## Install and first use

### Requirements

- Codex for natural-language use, or a terminal for direct helper use.
- Python **3.10 or newer**. The helper uses only the Python standard library; no `pip install` is needed.
- Zotero Desktop **10 or newer**, running on the same computer as the helper.
- Zotero's local API enabled in **Settings → Advanced → Allow other applications on this computer to communicate with Zotero**. [Zotero setup and authorization reference](https://www.zotero.org/support/dev/web_api/v3/local_api).

A remote/cloud helper cannot reach the Zotero instance on your computer through its own `127.0.0.1`. Run this skill locally alongside Zotero.

### Install in Codex

Ask Codex:

> Use $skill-installer to install only the zotero-manager skill from repository hi-ashutosh/zotero-manager-plugins, ref feat/zotero-manager, path plugins/zotero/skills/zotero-manager. Preserve any existing installation until you have checked it.

The explicit ref matters because the branch name contains a slash. Install the **whole skill folder**, including its scripts and references; copying only `SKILL.md` is insufficient. This local-skill route does not require installing every plugin in the repository. OpenAI documents installation from other repositories through the skill installer; if the skill does not appear after installation, restart Codex. [Official OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills).

Invoke it explicitly as `$zotero-manager` to distinguish it from the original `$Zotero` skill. Each friend needs their own local Zotero setup and authorization; no credentials are distributed in this repository.

### Optional: clone for terminal use or development

```bash
git clone --filter=blob:none --sparse --single-branch --branch feat/zotero-manager https://github.com/hi-ashutosh/zotero-manager-plugins.git
cd zotero-manager-plugins
git sparse-checkout set plugins/zotero
```

Cloning alone does not register a Codex skill. Use the installer above for Codex discovery, or register the whole skill folder using a local skill location supported by your Codex installation. For terminal use, no Codex registration is needed.

From the repository root, define this convenience function in a macOS/Linux shell:

```bash
zm() { python3 plugins/zotero/skills/zotero-manager/scripts/zotero_manager.py "$@"; }
zm status --json
```

Every `zm` example below calls that Python script. On a different shell, run `python3` followed by the script's full path and the same arguments. The helpers have been live-tested on macOS; Windows/Linux behavior has not been validated.

## Permissions and previews

Two separate decisions apply: **you authorize a task**, and **Zotero grants the helper an API key**. A remembered key does not authorize unrelated tasks by itself.

For the new management commands, omitting `--apply` previews the operation. A preview reads necessary data but does not request authorization, change the library or save a write journal. `changed: false` means the requested state was already present. Use `--apply` to execute an authorized change.

```bash
zm edit-tags ABCD2345 --add 'To read'
zm authorize
zm edit-tags ABCD2345 --add 'To read' --apply
```

`authorize` opens Zotero's own dialog, which you click yourself. **Allow** grants one write; **Always Allow** grants reusable access; **Deny** grants none. The key can technically write to libraries the user can edit; it is not restricted to a particular test record. The helper's task scope is governed separately by your instructions. Remembered access can be revoked with **Settings → Advanced → Clear Write Authorizations**. [Zotero local write authorization](https://www.zotero.org/support/dev/web_api/v3/local_api#authorizing_writes).

Credentials are kept privately in `~/.local/state/zotero-manager/auth.json`; writes save recovery journals in the sibling `backups/` folder. Do not share either with friends or commit them. Override both locations with `--state-dir PATH` **before a new management subcommand**, and use the same location for authorization and subsequent operations. Inherited commands do not accept that option.

**Inherited-command exceptions:** imports use `--yes`, not `--apply`. Exports, `sync-bib`, `cite` and `fulltext --out` can write local files. `enable`, `disable` and `restart` change settings or application state. These commands do not gain preview mode through this wrapper.

## Use it in Codex

Supply enough information to identify the intended paper/collection. Codex should resolve ambiguous matches before writing. You can use requests such as:

> Use $zotero-manager to find my paper titled “Example paper” and show its metadata. Do not change anything.

> Use $zotero-manager to add the tag “To read” to the paper with item key ABCD2345. Keep its other tags.

> Use $zotero-manager to create a collection called Bandit theory under my Machine Learning collection.

> Use $zotero-manager to move item ABCD2345 from collection EFGH6789 to JKLM2345, retaining its other collection memberships.

> Use $zotero-manager to attach /absolute/path/Paper.pdf as a linked PDF to item ABCD2345. Check for an existing link first.

> Use $zotero-manager to relink attachment NPQR6789 to /absolute/path/Replacement.pdf. Keep the existing attachment record.

Keys in this guide are fictitious placeholders. Replace them with keys returned by your library. A Zotero item key is not the same as an exported BibTeX citation key.

## Command-line guide

### Find records and identify keys

```bash
zm search 'Example paper' --json
zm inventory --json
zm collections --json
zm tags --json
zm get items ABCD2345
zm get collections EFGH6789
zm children ABCD2345 --json
zm get items NPQR6789
```

`search` searches top-level personal-library items. Search and inventory summarize records; `get items` returns complete JSON. `children` identifies attachment/note keys; use the **child attachment key** for `file-url` and `relink-file`. `inventory --include-children` includes child summaries.

### Create or edit a reference

```bash
zm template journalArticle
zm create-item --json '{"itemType":"journalArticle","title":"Example paper","creators":[{"creatorType":"author","firstName":"Jane","lastName":"Doe"}],"date":"2011","collections":["EFGH6789"]}'
zm edit-item ABCD2345 --json '{"title":"Corrected title","date":"2011","DOI":"10.1234/example"}'
```

These commands preview. After reviewing an authorized change, repeat the relevant command with `--apply`.

`template` returns a `template` object plus `allowedCreatorTypes`. Send the inner item object to `create-item`, not the whole wrapper. `--json` accepts a JSON object string, not a filename. Valid fields depend on the item type. Creators use Zotero's `creators` array; organization/single-field names use `name` instead of first/last names.

`edit-item` patches supplied fields and leaves other fields unchanged, but supplied arrays replace complete arrays. To edit authors, provide the complete intended `creators` list. Use `edit-tags` and `membership` for incremental changes. Clearing a scalar generally uses `""`; clearing a list uses `[]`. Keys, versions and managed date fields cannot be edited through this command. New-reference duplicate detection is not automatic: search before creating.

### Create, rename and nest collections

```bash
zm create-collection --name 'Bandit theory' --apply
zm create-collection --name 'Exploration' --parent EFGH6789 --apply
zm edit-collection EFGH6789 --name 'Bandit theory and applications' --apply
zm edit-collection EFGH6789 --parent JKLM2345 --apply
zm edit-collection EFGH6789 --parent none --apply
```

`--parent none` places a collection at the library root. Omit `--apply` to preview. Renaming preserves the existing parent; moving a collection uses the supported reparenting command but was not separately live-tested.

### Add, remove or move collection membership

```bash
zm membership ABCD2345 --add EFGH6789 --apply
zm membership ABCD2345 --remove EFGH6789 --apply
zm membership ABCD2345 --remove EFGH6789 --add JKLM2345 --apply
```

A record can belong to multiple collections. “Move” removes the specified source membership and adds the destination in one version-checked update, preserving all other memberships. Removal from a collection does not delete the library item. Repeat `--add` or `--remove` for multiple collection keys. Child attachments use their parent's collection membership.

### Add or remove tags

```bash
zm edit-tags ABCD2345 --add 'To read' --add 'Bandits' --remove 'Finished' --apply
```

This affects one item. Names are case-sensitive and input whitespace is trimmed. Existing unrelated tags and their manual/automatic types are preserved; new tags are manual. Adding an existing tag or removing an absent tag is a no-op. Blank names and adding/removing the same name in one request are rejected. This does not rename a tag across the entire library.

### Export, cite and import

```bash
zm export-bibtex --item-key ABCD2345 --out one-reference.bib
zm sync-bib --out references.bib
zm citations --style apa --json
zm cite --item-key ABCD2345 --markdown notes.md --bib references.bib --marker '<cite>'
zm cite --item-key ABCD2345 --tex paper.tex --bib references.bib --marker '<cite>'
zm selected-target --json
zm import-bibtex --file new-references.bib --yes
zm import-ris --file new-references.ris --yes
```

These inherited commands are available, but not all were re-tested here. Imports use the library/collection currently selected in Zotero; inspect `selected-target` first. They do not use the manager's local-API key workflow. An import is not an update-in-place operation for an existing entry.

`sync-bib` writes a fresh personal-library export; it is not bidirectional synchronization. `cite` edits the draft and appends a missing BibTeX entry. It does not refresh an existing entry with the same BibTeX key. Prefer an explicit item key because `cite --query` warns and selects the first result if a query is ambiguous. A supplied marker must exist in the draft; without a marker the citation is appended.

For other inherited commands, use `zm COMMAND --help`. `fulltext ATTACHMENTKEY` reads text already indexed by Zotero; it does not OCR unindexed files.

## PDF linking and relinking

```bash
zm link-file ABCD2345 '/absolute/path/Paper.pdf' --title 'Paper PDF' --apply
zm file-url NPQR6789
zm relink-file NPQR6789 '/absolute/path/Replacement.pdf'
zm relink-file NPQR6789 '/absolute/path/Replacement.pdf' --apply
```

`link-file` takes a **parent reference key**, then creates a linked child attachment if the same resolved path is not already attached. `relink-file` takes an **existing attachment key**, then changes that attachment's path. It retains the key, title and parent, including when the old file is missing. It rejects parent records, stored-copy attachments and non-PDF replacement paths. It does not search your disk for replacements; supply an existing PDF explicitly.

The PDF stays in your chosen folder. Neither command copies, moves, renames or edits its contents. If you move the file yourself later, use `relink-file`. Both write workflows verify that Zotero's file URL resolves to the requested path. An existing `.pdf` file is required; the helper does not validate its entire PDF structure. A snapshot of old attachment metadata is saved before relinking.

Zotero supports opening a linked attachment by double-clicking it. Our tests verified the resolved path and unchanged bytes, not viewer UI behavior. Zotero does not sync linked-file contents, and linked files cannot be used in group libraries. For multiple computers, arrange file availability yourself and review Zotero's linked attachment base-directory behavior. [Official linked-file documentation](https://www.zotero.org/support/attaching_files#linked_files).

## Troubleshooting and recovery

| Symptom | What to do |
|---|---|
| Zotero unavailable or connection refused | Open Zotero, check the local-API setting and run `status --json`. The manager connects to `127.0.0.1:23119` on the same computer. |
| “Operation not permitted” from Codex's sandbox | Request access to the local API through Codex's normal command permissions; this does not require screen control. It does not prove Zotero is closed. |
| No authorization / HTTP 401 | Run `authorize` again for the authorized task. A single-use key may already have been consumed. |
| HTTP 403 | Check the local API setting, the authorization decision and library access. |
| HTTP 412 | The object or Zotero database changed. Re-read it and review a fresh preview before attempting the change again. |
| HTTP 429 during authorization | Wait before requesting another dialog; avoid repeatedly requesting permission. |
| HTTP 400 or a per-object failure | Inspect invalid fields/type/JSON and the returned error. An HTTP 200 response alone is not proof every object was saved; the manager checks per-object results. |
| Timeout or read-back mismatch after a write | Inspect the object and recovery journal before retrying. The write may already have succeeded. |
| “Expected an eight-character … key” | Use the actual Zotero key from a search/child/collection result, not a DOI, title or BibTeX key. |
| A linked PDF no longer opens | Find the PDF at its new location, identify its existing attachment key, preview `relink-file`, then apply the authorized repair. |

New management creates journal the intended key before sending. Edits save complete previous metadata plus proposed changes before writing. The result reports its `journal` or `backup` path. These files help diagnose failures and reconstruct selected fields; **there is no automatic undo/restore command**. Ask Codex to compare the saved metadata with the current record and preview a corrective edit. Do not blindly re-upload a snapshot's old key/version or assume it can restore lost PDF contents. Journals contain library metadata and have no automatic retention limit.

## Updates, tests and project files

For a Git checkout, review local changes, then update the development branch:

```bash
git status
git pull --ff-only origin feat/zotero-manager
```

A skill installed as a copied folder does not follow later GitHub pushes automatically: ask `$skill-installer` to update that source/ref after inspecting the existing installation. A skill registered as a symlink uses its checkout's files; keep the checkout at that location. Avoid installing duplicate copies under the same skill name.

Offline checks, from the repository root:

```bash
python3 -B -m unittest discover -s plugins/zotero/skills/zotero-manager/tests -v
```

The live harness creates and deletes marked temporary records/collections, generates temporary PDFs and uses the normal write key. Run it only when that test scope is authorized:

```bash
python3 -B plugins/zotero/skills/zotero-manager/tests/live_smoke.py --apply
```

Without `--apply`, the live harness exits without connecting or writing. It checks fixture markers before deletion and retains a report with any cleanup failures. The ordinary helper has no general delete command; test cleanup is narrowly implemented in this harness.

- [Agent instructions](SKILL.md)
- [Verified behavior and limitations](references/validation.md)
- [Bundled-skill assessment](https://github.com/hi-ashutosh/zotero-manager-plugins/blob/feat/zotero-manager/plugins/zotero/docs/01-existing-zotero-skill-assessment.md)
- [Feature plan and priorities](https://github.com/hi-ashutosh/zotero-manager-plugins/blob/feat/zotero-manager/plugins/zotero/docs/02-new-skill-features-and-priorities.md)
- [Manager implementation](scripts/zotero_manager.py)
- [Inherited helper](scripts/zotero_legacy.py)

The original `skills/zotero` remains alongside the extended `skills/zotero-manager`. The manager reuses the upstream helper and adds supported local-API operations; it does not write SQLite directly. See the [license and attribution](LICENSE).
