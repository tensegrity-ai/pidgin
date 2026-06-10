---
name: update-claude-model
description: Add a new Claude (Anthropic) model version to pidgin/data/models.json. Use when the user mentions a newly released claude-fable, claude-opus, claude-sonnet, or claude-haiku version (e.g. "opus 4.8 just dropped", "add the new sonnet", "bump fable", "bump haiku").
---

# Update Claude model

Follow the universal recipe in `update-model`, with these Anthropic-specific details.

## Families

Current Anthropic families, top-tier first:

- **fable** — public-facing flagship from the mythos line. 1M context.
- **opus** — high-capability tier. 1M context (current 4.x).
- **sonnet** — mid-tier workhorse. 1M context (current 4.x).
- **haiku** — fast/cheap tier. 200K context (current 4.x).

Notes:

- **Mythos** is a related limited-availability internal line and is **not** registered in `models.json`. Fable is the publicly available mythos-class model. Do not add Mythos entries unless the user explicitly asks.

## Conventions

- **Key**: `claude-<family>-<MAJOR>.<MINOR>` — e.g. `claude-opus-4.8`, `claude-sonnet-4.7`, `claude-haiku-5.0`. Fable currently ships major-version-only (`claude-fable-5`); if a minor lands, follow the same pattern (`claude-fable-5.1`).
- **display_name**: `"Anthropic: Claude <Family> <MAJOR>.<MINOR>"` — e.g. `"Anthropic: Claude Opus 4.8"`, `"Anthropic: Claude Fable 5"`.
- **api.model_id**: matches Anthropic's API id. Two patterns occur:
  - Dateless: `claude-<family>-<MAJOR>-<MINOR>` (e.g. `claude-opus-4-8`, `claude-fable-5`).
  - Dated snapshot: `claude-<family>-<MAJOR>-<MINOR>-<YYYYMMDD>` (e.g. `claude-haiku-4-5-20251001`).
  - When the dateless id is available (which is usually the case for the current release), prefer it. Look at the Claude Code environment context block for the canonical id of the model you're running on; older Haiku-style entries may keep their dated snapshot.
- **Family alias** (`aliases` field): `fable`, `opus`, `sonnet`, or `haiku`. The newest version in the family owns it; clear the previous owner's `aliases` to `[]`.

## Pricing defaults (per 1M tokens, USD)

| Family | input | output |
|---|---|---|
| fable  | `1e-05` | `5e-05`  |
| opus   | `5e-06` | `2.5e-05` |
| sonnet | `3e-06` | `1.5e-05` |
| haiku  | `1e-06` | `5e-06`  |

Use these unless Anthropic has announced a change for the new release. Always confirm against Anthropic's pricing page if the user provides one.

## Capabilities & limits

Copy from the previous entry in the same family — do not invent values. As of late Claude 4.x / Fable 5:

- `max_context_tokens`: `1000000` for current Fable/Opus/Sonnet, `200000` for current Haiku.
- `streaming`, `tool_calling`, `system_messages`, `json_mode`: `true`.
- `vision`, `extended_thinking`, `prompt_caching`: vary by family; copy them verbatim from the previous entry rather than guessing.

If Anthropic has announced a new capability (e.g. vision newly enabled), update only that flag.

## Recipe

1. Locate the previous latest entry (e.g. `claude-opus-4.7`) in `pidgin/data/models.json`.
2. Edit its `aliases` array down to `[]`.
3. Insert the new entry directly after it, cloned from its body, with the bumped key, `display_name`, `api.model_id`, `aliases: ["<family>"]`, and today's `cost.last_updated`.
4. Validate and commit per the universal recipe in `update-model`.

Commit message format: `chore: add <new-key> and move <family> alias` (e.g. `chore: add claude-opus-4.8 and move opus alias`).
