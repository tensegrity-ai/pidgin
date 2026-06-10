---
name: update-google-model
description: Add a new Google model version (Gemini or Gemma) to pidgin/data/models.json. Use when the user mentions a newly released gemini-* (gemini-3.0-pro, gemini-2.5-flash, etc.) or gemma-* model.
---

# Update Google model

Follow the universal recipe in `update-model`, with these Google-specific details.

## Conventions

- **Key**: the canonical Google model id — e.g. `gemini-3.0-pro`, `gemini-2.5-flash`, `gemma-3-27b-it`.
- **display_name**: existing entries use the bare id (`"gemini-2.5-pro"`). Match that style.
- **api.model_id**: equal to the key.

## Family aliases

| Family / tier | Alias |
|---|---|
| Latest Gemini Pro     | `gemini` |
| Latest Gemini Flash   | `flash` |
| Previous-major Flash  | `flash<MAJOR>` (e.g. `flash2` for `gemini-2.0-flash`) |

When bumping a major Pro or Flash release, move the alias to the new entry and clear the previous owner's `aliases` to `[]`. Gemma models typically have no alias.

## Pricing & limits

Gemini pricing varies (Pro vs Flash). Copy from the closest sibling and flag in the summary so the user can confirm. `max_context_tokens` for current Gemini 2.x sits in the 1M range — copy from the sibling rather than guessing.

## Capabilities

Copy from the closest sibling. Gemini 2.5 Pro and Flash have `vision: true` in the current data.

## Recipe

1. Locate the closest sibling (same tier — Pro/Flash/Gemma variant).
2. If the new model takes over `gemini` or `flash`, clear that alias from the previous owner.
3. Insert the new entry cloned from the sibling, with new key, `display_name`, `api.model_id`, appropriate alias(es), and today's `cost.last_updated`.
4. Validate and commit per `update-model`.

Commit message format: `chore: add <new-key>` (add `and move <alias> alias` if an alias was moved).
