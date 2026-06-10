---
name: update-xai-model
description: Add a new xAI Grok model version to pidgin/data/models.json. Use when the user mentions a newly released grok-* model.
---

# Update xAI (Grok) model

Follow the universal recipe in `update-model`, with these xAI-specific details.

## Conventions

- **Key**: the canonical xAI model id — e.g. `grok-5`, `grok-4-mini`.
- **display_name**: match existing entries (bare id is fine).
- **api.model_id**: equal to the key.

## Family aliases

| Model | Alias |
|---|---|
| Latest non-mini `grok-N` | `grok` |
| Previous-major non-mini  | `grok<N>` (e.g. `grok3` for `grok-3`) |
| `*-mini` variants        | typically no alias |

When bumping the latest, move the `grok` alias to the new entry and clear the previous owner's `aliases` to `[]`. Optionally give the demoted previous-latest a `grok<N>` alias if there isn't already one.

## Pricing & limits

xAI doesn't publish via OpenRouter as cleanly as others — these entries were added manually. Copy pricing and limits from the closest sibling and flag in the summary so the user can confirm.

## Capabilities

Copy from the closest sibling.

## Recipe

1. Locate the closest sibling (e.g. `grok-4` when adding `grok-5`).
2. Clear `["grok"]` from the previous owner's `aliases`.
3. Insert the new entry cloned from the sibling, with new key, `display_name`, `api.model_id`, `aliases: ["grok"]`, and today's `cost.last_updated`.
4. Validate and commit per `update-model`.

Commit message format: `chore: add <new-key> and move grok alias`.
