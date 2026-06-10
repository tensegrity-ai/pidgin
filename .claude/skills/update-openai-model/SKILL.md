---
name: update-openai-model
description: Add a new OpenAI model version (GPT or o-series) to pidgin/data/models.json. Use when the user mentions a newly released gpt-* (gpt-5, gpt-4.2, etc.) or o-series (o3, o4, o5, mini variants) model.
---

# Update OpenAI model

Follow the universal recipe in `update-model`, with these OpenAI-specific details.

## Conventions

- **Key**: the canonical OpenAI model id, no prefix — e.g. `gpt-5`, `gpt-4.2`, `o5`, `o4-mini`.
- **display_name**: same as the key, or whatever OpenAI's display string is (existing entries use the bare id, e.g. `"gpt-4.1"`).
- **api.model_id**: equal to the key. OpenAI rarely uses dated suffixes for the canonical id; if a dated snapshot is the only available id, use it verbatim.

## Family aliases

These are the short aliases users type:

| Family / model | Alias |
|---|---|
| Latest non-mini `gpt-N` | `gpt<N>` (e.g. `gpt5` for `gpt-5`) |
| Latest `gpt-N-mini`     | `gpt<N>-mini` |
| Latest `gpt-N-nano`     | `gpt<N>-nano` |
| Latest non-mini `o<N>`  | `o<N>` |
| Latest `o<N>-mini`      | `o<N>-mini` |
| `gpt-4o`                | `4o` |
| `gpt-4o-mini`           | `4o-mini` |

When bumping a major version, move the alias to the new entry and clear the previous owner's `aliases` to `[]`.

## Pricing & limits

OpenAI pricing varies per model — **do not assume**. If the user provides pricing, use it. Otherwise copy from the closest existing sibling and flag this in the commit/summary so the user can confirm.

`max_context_tokens` and `max_output_tokens`: copy from the closest sibling entry.

## Capabilities

Copy from the closest sibling. Notable defaults seen in the current data:

- o-series: `extended_thinking: true`, `tool_calling: false` (o1 specifically; check the sibling).
- GPT-4o family: `vision: true`.
- Other GPTs: `vision: false` unless announced.

## Recipe

1. Locate the closest sibling (same family/tier) in `pidgin/data/models.json`.
2. If the new model takes over a short alias, clear that alias from the previous owner.
3. Insert the new entry cloned from the sibling, with new key, `display_name`, `api.model_id`, appropriate alias(es), and today's `cost.last_updated`.
4. Validate and commit per `update-model`.

Commit message format: `chore: add <new-key>` (add `and move <alias> alias` if an alias was moved).
