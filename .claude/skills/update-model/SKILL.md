---
name: update-model
description: Add a new model version to pidgin/data/models.json. Use when the user mentions a newly released model from Anthropic (Claude/Opus/Sonnet/Haiku), OpenAI (GPT/o-series), Google (Gemini/Gemma), or xAI (Grok) and wants it registered. Dispatches to the per-provider sub-skill.
---

# Update Model (meta)

Pidgin tracks every supported model in `pidgin/data/models.json`. Adding a new version follows a uniform recipe with small per-provider differences.

## Dispatch

Identify the provider from the model name and follow the matching sub-skill:

| Family | Provider | Sub-skill |
|---|---|---|
| `claude-*`, opus, sonnet, haiku | anthropic | `update-claude-model` |
| `gpt-*`, `o<N>` (o1/o3/o4/o5...) | openai | `update-openai-model` |
| `gemini-*`, `gemma-*` | google | `update-google-model` |
| `grok-*` | xai | `update-xai-model` |

If multiple providers shipped at once, run each sub-skill in turn.

## Universal recipe (shared by every sub-skill)

1. **Find the previous latest entry** for the same family in `pidgin/data/models.json` (e.g. `claude-opus-4.7` when adding 4.8). Use it as the template.
2. **Insert a new entry** directly after it, cloned from its body, with:
   - new key (version bumped)
   - bumped `display_name`
   - new `api.model_id` (provider's actual id — see sub-skill)
   - `cost.last_updated` set to today's date
3. **Move the family alias** (`opus`/`sonnet`/`haiku`/`gemini`/`flash`/`grok`/etc.) from the old entry's `aliases` array to the new entry's. Leave the old entry's metadata otherwise intact.
4. **Do not modify** sibling entries, capability flags, or pricing unless the sub-skill says to.
5. **Validate**:
   ```bash
   uv run python -c "
   import json; json.load(open('pidgin/data/models.json'))
   from pidgin.config.models import resolve_model_id
   for name in ['<family-alias>', '<new-key>', '<previous-key>']:
       mid, cfg = resolve_model_id(name)
       print(f'{name} -> {mid} (api_id: {cfg.api.model_id if cfg else None})')
   "
   ```
   The family alias must resolve to the new key. The old key must still resolve to itself.
6. **Commit & push** on the active development branch:
   ```bash
   git add pidgin/data/models.json
   git commit -m "chore: add <new-key> and move <family> alias"
   git push -u origin <branch>
   ```

## Notes

- `scripts/model_overrides.yaml` is only consulted when `scripts/generate_models.py` is re-run. Hand edits to `models.json` are the supported quick path; the overrides file does not need an entry per release.
- No PR unless the user asks for one.
