# Model Generation Scripts

This directory contains scripts for generating and maintaining `pidgin/data/models.json`.

## generate_models.py

Generates a v2-compliant `models.json` file by combining data from multiple sources:

1. **Local models** from `model_overrides.yaml` (local:test, ollama models, etc.)
2. **OpenRouter API** - pricing, context windows, basic capabilities
3. **Provider APIs** - OpenAI, Anthropic, Google, XAI (when available)
4. **Model-specific overrides** - curation flags, aliases, capability corrections

### Requirements

```bash
pip install pyyaml
# OR
uv pip install pyyaml
```

### Usage

Basic usage (generates models.json in current directory):
```bash
python3 generate_models.py
```

Specify output location:
```bash
python3 generate_models.py -o ../pidgin/data/models.json
```

Custom overrides file:
```bash
python3 generate_models.py --overrides custom_overrides.yaml
```

### Environment Variables

Optional API keys for fetching latest model data:
- `OPENROUTER_API_KEY` - OpenRouter (primary source)
- `OPENAI_API_KEY` - OpenAI models
- `ANTHROPIC_API_KEY` - Anthropic models
- `GOOGLE_API_KEY` - Google Generative AI models
- `XAI_API_KEY` - X.ai/Grok models

The script works without API keys but will have limited data.

## model_overrides.yaml

Configuration file containing pidgin-specific model metadata:

### Local Models

Complete definitions for models not available via APIs:
- `local:test` - Test model for development
- `local:qwen` - Ollama Qwen 0.5B
- `local:phi` - Ollama Phi-3
- `local:mistral` - Ollama Mistral 7B
- `silent:none` - Silent provider

### Model Overrides

Corrections and enhancements for API-sourced models:
- **Aliases** - Short names for CLI usage (e.g., `sonnet`, `opus`, `4o`)
- **Curation flags** - Which models to show in default lists
- **Capability corrections** - Vision, extended thinking, prompt caching support
- **Descriptions** - Human-readable model descriptions

### Format

```yaml
local_models:
  - key: "local:test"
    provider: "local"
    display_name: "Local Test"
    aliases: ["test"]
    # ... full model definition

model_overrides:
  "claude-sonnet-4.5":
    aliases: ["sonnet"]
    capabilities:
      vision: true
      extended_thinking: true
    metadata:
      curated: true
```

## Workflow

1. **Update overrides** - Edit `model_overrides.yaml` to add/modify models
2. **Generate** - Run `python3 generate_models.py -o ../pidgin/data/models.json`
3. **Test** - Verify with `pidgin models` command
4. **Commit** - Commit both the script changes and updated models.json

## Notes

- The script is resilient to API failures and missing keys
- Local models are always included from overrides
- Model-specific overrides are deep-merged with API data
- Key format: API models use simple IDs (`claude-sonnet-4.5`), local models use prefixes (`local:test`)
