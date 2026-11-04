---
name: zotero-manager
description: Manage a personal Zotero Desktop library using Zotero 10 local APIs. Create and edit references, organize collections, manage tags, attach and relink local PDFs, search, export, and cite. Use for Zotero library changes; excludes PDF content editing and highlighting.
---

# Zotero Manager — starter 0.2.0

Run `python3 <skill-dir>/scripts/zotero_manager.py ...`. Self-contained, Python standard library only. This is a separately maintained extension of OpenAI's Zotero helper 0.1.2, maintained in https://github.com/hi-ashutosh/zotero-manager-plugins on branch `feat/zotero-manager`. It does not modify the installed bundled plugin cache. Source attribution: https://github.com/openai/plugins/tree/main/plugins/zotero (MIT).

For setup, natural-language examples, the complete command guide and troubleshooting, read [the user guide](README.md). Agent-specific operating rules follow here.

## Operation

- Respect the user's task authorization. Read-only discussion is not permission to modify the library. Once a particular task is authorized, complete its routine steps without asking repeatedly.
- Start with `status --json`. If the local API is disabled, explain and enable only within the user's authorization. A sandbox connection error is not evidence that Zotero is closed.
- Read complete records using `get items ITEMKEY` and collections using `get collections COLLKEY`. Confirm identity by metadata and key; never choose an ambiguous search match for a write.
- New management commands preview by default. Add `--apply` to execute an authorized operation. A preview performs reads, not a Zotero authorization request or library write.
- Run `authorize` only when library writes are authorized. This opens Zotero's own dialog; let the user choose single-use or remembered access. Credentials are stored privately in `~/.local/state/zotero-manager/auth.json`. Never print or commit keys or inspect Zotero's internal credential files.
- `--state-dir PATH` before the command overrides credential/journal location. Legacy commands do not accept this option.
- Writes require the current server ID and version preconditions. Edits save the previous complete metadata, and creates journal their intended keys before sending. Recovery journals are in the state directory's `backups/` directory. No automatic rollback or retry: after a timeout or verification mismatch, inspect the intended key and journal before proceeding. On 401, authorize again only within the user's existing task authorization. On 412, re-read and assess rather than blindly retrying.
- JSON arrays replace entire arrays. Preserve existing creators/tags/relations unless the requested task replaces them. Use `membership` to preserve unrelated collection memberships automatically, and `edit-tags` to preserve unrelated tags and their types.
- Use supported HTTP APIs only; no SQLite writes or Zotero profile edits for management operations.

## Commands

```bash
# Read or preview
python3 <skill-dir>/scripts/zotero_manager.py get items ABCD2345
python3 <skill-dir>/scripts/zotero_manager.py template journalArticle
python3 <skill-dir>/scripts/zotero_manager.py edit-item ABCD2345 --json '{"title":"Corrected title","date":"2011"}'

# Actual writes: use --apply only for an authorized task
python3 <skill-dir>/scripts/zotero_manager.py authorize
python3 <skill-dir>/scripts/zotero_manager.py create-item --json '{"itemType":"manuscript","title":"Example","creators":[{"creatorType":"author","firstName":"Jane","lastName":"Doe"}]}' --apply
python3 <skill-dir>/scripts/zotero_manager.py edit-item ABCD2345 --json '{"DOI":"10.1234/example"}' --apply
python3 <skill-dir>/scripts/zotero_manager.py create-collection --name Bandits --apply
python3 <skill-dir>/scripts/zotero_manager.py create-collection --name Theory --parent ABCD2345 --apply
python3 <skill-dir>/scripts/zotero_manager.py edit-collection ABCD2345 --name 'Bandit theory' --apply
python3 <skill-dir>/scripts/zotero_manager.py edit-collection ABCD2345 --parent none --apply
python3 <skill-dir>/scripts/zotero_manager.py membership ABCD2345 --add EFGH6789 --remove JKLM2345 --apply
python3 <skill-dir>/scripts/zotero_manager.py link-file ABCD2345 '/absolute/path/Paper.pdf' --apply
python3 <skill-dir>/scripts/zotero_manager.py edit-tags ABCD2345 --add 'To read' --remove 'Read' --apply
python3 <skill-dir>/scripts/zotero_manager.py relink-file EFGH6789 '/absolute/path/Replacement.pdf' --apply
```

`membership` accepts repeated `--add`/`--remove`. A move updates both memberships in one version-checked write; it does not delete the entry. Linked PDFs remain at their supplied path, with a child attachment referencing them. Files must already exist. The helper checks for an existing link to the same resolved path, then verifies the resulting file URL. Double-click the PDF attachment in Zotero to open it. Moving/renaming the physical file afterward requires updating the link. Linked PDFs are not synced by Zotero and cannot be used in group libraries. This starter does not move, rename, copy, or edit PDF files.

`edit-tags` accepts repeated `--add` and `--remove`, matches tag names case-sensitively after trimming input whitespace, and preserves unrelated tags and existing manual/automatic tag types. New tags are manual. Adding an existing tag or removing an absent tag is a no-op. Blank names and adding/removing the same tag in one request are rejected.

`relink-file` takes the **attachment key**, not the parent reference key. Use `children` and `get items` to identify it. It updates an existing linked PDF attachment to an existing replacement PDF, keeping its key, parent and title. The original PDF may be missing. Stored-copy attachments are rejected; converting storage modes is outside this command. Preview is the default; `--apply` saves a recovery snapshot and verifies the resolved file URL. Neither PDF is moved or edited.

Preserved commands from the bundled helper: `status`, `inventory`, `search`, `collections`, `tags`, `groups`, `children`, `fulltext`, `file-url`, `export-bibtex`, `sync-bib`, `citations`, `cite`, `selected-target`, `import-bibtex`, `import-ris`, `enable`, `disable`, `restart`, `probe`. Use `<command> --help` for syntax. Imports require `--yes`; citation/export commands may write local files. `children` gives summaries, so use `get items CHILDKEY` for full note/attachment data. Only fetch full text or attachment paths when relevant to the user request. Legacy `cite --query` selects the first search match: resolve the intended record first and use `--item-key`.

## Limits and validation

The management commands target the personal library `/users/0/`; listing groups does not mean group writes are implemented. Notes use generic `edit-item` JSON and lack dedicated commands. Tags have the dedicated incremental `edit-tags` command. New-item templates are available for valid fields. Duplicate merging, saved-search management, stored-file uploads, automatic path discovery and file-moving repair, trash/restore, bulk editing, account management, and application-settings management are deferred. Item-type changes may discard incompatible fields; review the preview and saved snapshot carefully.

Read [references/validation.md](references/validation.md) for what was actually tested and any outstanding limitations. Run focused offline tests with `python3 -B -m unittest discover -s <skill-dir>/tests -v`. Live tests must use disposable records and files, never existing papers unless the user explicitly authorizes those changes.

API references: [local API](https://www.zotero.org/support/dev/web_api/v3/local_api), [write requests](https://www.zotero.org/support/dev/web_api/v3/write_requests), [linked files](https://www.zotero.org/support/attaching_files#linked_files).
