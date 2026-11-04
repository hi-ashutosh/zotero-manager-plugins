# Zotero Manager — personal fork

This fork extends OpenAI's Zotero skill with executable library-management commands for **metadata, collections, tags, linked PDFs and PDF relinking**.

**The new features live on branch `feat/zotero-manager`.** The fork's `main` branch still contains the upstream baseline.

- **[Start here: installation, features and usage guide](plugins/zotero/skills/zotero-manager/README.md)**
- [Skill instructions](plugins/zotero/skills/zotero-manager/SKILL.md)
- [Tested behavior and limitations](plugins/zotero/skills/zotero-manager/references/validation.md)
- [Feature plan](plugins/zotero/docs/02-new-skill-features-and-priorities.md)

In Codex, use `$zotero-manager` to select the extended skill. It talks to Zotero Desktop's local API; no screenshot or computer-control permission is needed. Writes require your task authorization and Zotero's own API authorization.

Current validation: **29 offline tests and 21 live assertions**, tested on macOS with Zotero 10.0.7. PDF editing/highlighting, duplicate merging, stored-file uploads and bulk management are outside the implemented scope. See the guide for exact feature coverage.

This repository is a fork of [openai/plugins](https://github.com/openai/plugins), which contains many unrelated plugin examples. Our changes are focused on `plugins/zotero`; installing Zotero Manager does not require installing those other plugins. No stable release or upstream pull request has been published.

## Upstream repository context

### Plugins

This repository contains a curated collection of Codex plugin examples.

Each plugin lives under `plugins/<name>/` with a required
`.codex-plugin/plugin.json` manifest and optional companion surfaces such as
`skills/`, `.app.json`, `.mcp.json`, plugin-level `agents/`, `commands/`,
`hooks.json`, `assets/`, and other supporting files.

The default marketplace lives at `.agents/plugins/marketplace.json` and points
at the standard `plugins/` directory. API key login users have a separate
marketplace at `.agents/plugins/api_marketplace.json`.

Highlighted richer examples in this repo include:

- `plugins/figma` for `use_figma`, Code to Canvas, Code Connect, and design system rules
- `plugins/notion` for planning, research, meetings, and knowledge capture
- `plugins/build-ios-apps` for SwiftUI implementation, refactors, performance, and debugging
- `plugins/build-macos-apps` for macOS SwiftUI/AppKit workflows, build/run/debug loops, and packaging guidance
- `plugins/build-web-apps` for deployment, UI, payments, and database workflows
- `plugins/expo` for Expo and React Native apps, SDK upgrades, EAS workflows, and Codex Run actions
- `plugins/netlify`, `plugins/remotion`, and `plugins/google-slides` for additional public skill- and MCP-backed plugin bundles
