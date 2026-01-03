# Models Schema v2.0 - Perfect Schema Design

**Created:** 2025-10-01
**Status:** Design Phase

## Executive Summary

The current `models.json` schema has hardcoded assumptions scattered throughout the codebase. This document proposes a comprehensive v2.0 schema where **every field is explicit** and **zero assumptions exist in code**.

## Current Problems

### 1. Split Responsibilities - Provider vs Model Capabilities

**Problem:** `provider_capabilities.py` defines capabilities per provider, but these vary per model.

```python
# pidgin/config/provider_capabilities.py
PROVIDER_CAPABILITIES = {
    "openai": ProviderCapabilities(
        supports_vision=True,  # WRONG - not all OpenAI models have vision
    ),
}
```

**Reality:** GPT-4o has vision, GPT-3.5 doesn't. Capabilities are **model-specific**, not provider-specific.

### 2. Hardcoded Defaults Scattered Everywhere

```python
# pidgin/cli/constants.py
DEFAULT_TEMPERATURE = 0.7

# pidgin/config/model_loader.py
context_window=config.get("context_window", 4096)  # Fallback

# pidgin/providers/builder.py:46
model_map = {"qwen": "qwen2.5:0.5b", "phi": "phi3", "mistral": "mistral"}
```

### 3. Missing Critical Capabilities in models.json

**Currently has:**
- `context_window`, `pricing`, `aliases`, `curated`, `stable`

**Missing:**
- Streaming support (per model)
- Vision/multimodal support
- Tool/function calling
- Max output tokens (separate from context)
- Temperature ranges
- Provider-specific API fields

### 4. Special-Cased Providers

```python
# Ollama models have special "ollama_model" field
# Local/silent get special fallback handling
# Model name mappings hardcoded in builder.py
```

### 5. No Explicit Parameter Constraints

- No per-model temperature support/ranges
- No way to know if `temperature=0` is valid
- No `max_output_tokens` (separate from `context_window`)

## The Perfect Schema v2.0

### Design Principles

1. **Every field is explicit** - No defaults in code, ever
2. **Model-level capabilities** - Not provider-level inheritance
3. **Structured parameters** - Ranges and defaults included
4. **No special cases** - All providers use same structure
5. **Self-validating** - JSON Schema validation on load

### Schema Structure

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "schema_version": "2.0.0",
  "last_updated": "2025-10-01T00:00:00Z",
  "generator": "pidgin-tools",

  "models": {
    "model_id": {
      "provider": "...",
      "display_name": "...",
      "aliases": [...],
      "api": {...},
      "capabilities": {...},
      "limits": {...},
      "parameters": {...},
      "cost": {...},
      "metadata": {...},
      "rate_limits": {...}
    }
  }
}
```

### Complete Example: Claude Sonnet 4.5

```json
{
  "claude-sonnet-4-5": {
    // === Identity ===
    "provider": "anthropic",
    "display_name": "Claude Sonnet 4.5",
    "aliases": ["sonnet"],

    // === API Configuration ===
    "api": {
      "model_id": "claude-sonnet-4-5",
      "api_version": "2023-06-01"
    },

    // === Capabilities (explicit, no inheritance) ===
    "capabilities": {
      "streaming": true,
      "vision": true,
      "tool_calling": true,
      "system_messages": true,
      "extended_thinking": true,
      "json_mode": false,
      "prompt_caching": true
    },

    // === Token Limits (all explicit) ===
    "limits": {
      "max_context_tokens": 1000000,
      "max_output_tokens": 8192,
      "max_thinking_tokens": null  // null = unlimited/N/A
    },

    // === Parameter Support ===
    "parameters": {
      "temperature": {
        "supported": true,
        "range": [0.0, 1.0],
        "default": 1.0
      },
      "top_p": {
        "supported": true,
        "range": [0.0, 1.0],
        "default": null
      },
      "top_k": {
        "supported": false
      }
    },

    // === Cost Structure ===
    "cost": {
      "input_per_1m_tokens": 3.00,
      "output_per_1m_tokens": 15.00,
      "cache_read_per_1m_tokens": 0.30,
      "cache_write_per_1m_tokens": 3.75,
      "currency": "USD",
      "last_updated": "2025-09-29"
    },

    // === Metadata ===
    "metadata": {
      "status": "available",  // available, preview, deprecated
      "release_date": "2025-09-29",
      "deprecation_date": null,
      "curated": true,
      "stable": true,
      "description": "Most intelligent Claude model"
    },

    // === Rate Limits (optional) ===
    "rate_limits": {
      "requests_per_minute": 50,
      "tokens_per_minute": 40000
    }
  }
}
```

### Example: Ollama Model (local:mistral)

```json
{
  "local:mistral": {
    "provider": "ollama",
    "display_name": "Mistral 7B",
    "aliases": ["mistral"],

    "api": {
      "model_id": "local:mistral",
      "ollama_model": "mistral:7b"  // Explicit Ollama API name
    },

    "capabilities": {
      "streaming": true,
      "vision": false,
      "tool_calling": false,
      "system_messages": true,
      "extended_thinking": false,
      "json_mode": false,
      "prompt_caching": false
    },

    "limits": {
      "max_context_tokens": 32768,
      "max_output_tokens": 32768,
      "max_thinking_tokens": null
    },

    "parameters": {
      "temperature": {
        "supported": true,
        "range": [0.0, 2.0],
        "default": 0.8
      },
      "top_p": {
        "supported": true,
        "range": [0.0, 1.0],
        "default": null
      },
      "top_k": {
        "supported": true,
        "range": [1, 100],
        "default": null
      }
    },

    "cost": null,  // Free local model

    "metadata": {
      "status": "available",
      "release_date": "2023-09-01",
      "curated": true,
      "stable": true,
      "notes": "Requires 8GB+ RAM",
      "size": "4.1GB"
    },

    "rate_limits": null  // No limits for local
  }
}
```

### Example: Test Model (local:test)

```json
{
  "local:test": {
    "provider": "local",
    "display_name": "Local Test",
    "aliases": ["test"],

    "api": {
      "model_id": "local:test"
    },

    "capabilities": {
      "streaming": true,
      "vision": false,
      "tool_calling": false,
      "system_messages": true,
      "extended_thinking": false,
      "json_mode": false,
      "prompt_caching": false
    },

    "limits": {
      "max_context_tokens": null,  // Unlimited for test
      "max_output_tokens": null,
      "max_thinking_tokens": null
    },

    "parameters": {
      "temperature": {
        "supported": false
      },
      "top_p": {
        "supported": false
      },
      "top_k": {
        "supported": false
      }
    },

    "cost": null,

    "metadata": {
      "status": "available",
      "curated": false,
      "stable": true,
      "description": "Test model for development"
    },

    "rate_limits": null
  }
}
```

## Benefits of v2.0 Schema

### 1. Model-Level Capabilities (Not Provider-Level)

```python
# OLD (bad):
if provider == "anthropic":
    supports_vision = True  # Wrong - not all Claude models have vision

# NEW (good):
if model_config.capabilities.vision:
    process_images()
```

### 2. API Configuration Separate

Provider-specific fields live in the `api` section:

```json
"api": {
  "model_id": "claude-sonnet-4-5",     // What to send to API
  "ollama_model": "mistral:7b",        // Ollama-specific
  "api_version": "2023-06-01",         // Anthropic-specific
  "deployment_id": "my-deployment"     // Azure-specific (future)
}
```

### 3. Structured Parameters with Validation

Not just boolean flags - know the valid ranges:

```json
"parameters": {
  "temperature": {
    "supported": true,
    "range": [0.0, 1.0],
    "default": 1.0
  }
}
```

### 4. No Special Cases in Code

```python
# Before: Special handling for Ollama
if model_id.startswith("local:"):
    model_map = {"qwen": "qwen2.5:0.5b", ...}
    ollama_model = model_map.get(name, name)

# After: Just read from config
ollama_model = model_config.api.get("ollama_model", model_config.api.model_id)
```

### 5. Complete Token Information

```json
"limits": {
  "max_context_tokens": 1000000,    // Total context
  "max_output_tokens": 8192,        // Output limit
  "max_thinking_tokens": null       // Thinking budget (if applicable)
}
```

## Implementation Plan

### Phase 1: Schema Design ✓

- [x] Design v2.0 structure
- [x] Write examples for all provider types
- [x] Document design principles

### Phase 2: Schema Implementation

1. Create `models_schema_v2.json` with complete JSON Schema
2. Update `ModelConfig` dataclass with new fields:
   ```python
   @dataclass
   class ModelConfig:
       model_id: str
       provider: str
       display_name: str
       aliases: List[str]
       api: ApiConfig
       capabilities: Capabilities
       limits: Limits
       parameters: Parameters
       cost: Optional[Cost]
       metadata: Metadata
       rate_limits: Optional[RateLimits]
   ```
3. Add nested dataclasses:
   - `ApiConfig` - Provider-specific API fields
   - `Capabilities` - Feature flags
   - `Limits` - Token limits
   - `Parameters` - Parameter support with ranges
   - `Cost` - Pricing information
   - `Metadata` - Descriptive info
   - `RateLimits` - API rate limits

### Phase 3: Data Migration

1. Convert existing `models.json` to new schema
2. Research and fill in missing capability data for each model:
   - Vision support
   - Tool calling support
   - Streaming availability
   - Parameter ranges
   - Output token limits
3. Validate all 58 models against schema

### Phase 4: Code Updates

**Remove hardcoded assumptions:**
1. Delete `pidgin/config/provider_capabilities.py`
2. Remove `DEFAULT_TEMPERATURE` from `pidgin/cli/constants.py`
3. Remove model mappings from `pidgin/providers/builder.py`
4. Remove fallback defaults from `pidgin/config/model_loader.py`

**Update code to use explicit config:**
1. Replace provider-level capability checks with model-level
2. Use `model_config.parameters.temperature.range` for validation
3. Use `model_config.api.ollama_model` instead of hardcoded map
4. Use `model_config.limits.max_output_tokens` for truncation

### Phase 5: Validation

1. Add JSON Schema validation on load (fail fast on invalid data)
2. Add runtime checks that all required fields are present
3. Add tests to ensure no code uses hardcoded defaults
4. Add tests for parameter range validation

## Migration Strategy

### Backward Compatibility

**Schema Version Check:**
```python
def load_models(path: Path) -> Dict[str, ModelConfig]:
    data = json.loads(path.read_text())
    schema_version = data.get("schema_version", "1.0.0")

    if schema_version == "2.0.0":
        return load_v2_models(data)
    elif schema_version in ["1.0.0", "1.1.0"]:
        return load_v1_models(data)
    else:
        raise ValueError(f"Unsupported schema version: {schema_version}")
```

**No Breaking Changes:**
- Old v1 schemas continue to work
- Loader auto-detects version
- Deprecation warnings for v1
- Migration tool provided

### User Override Support

Users can still override at `~/.local/share/pidgin/models.json`:

```bash
# Copy package models.json as starting point
cp ~/.local/pipx/venvs/pidgin/lib/python3.x/site-packages/pidgin/data/models.json \
   ~/.local/share/pidgin/models.json

# Edit to customize pricing, add models, etc.
```

## Testing Plan

### 1. Schema Validation Tests

```python
def test_schema_validates():
    """All models pass JSON Schema validation."""
    schema = load_schema("models_schema_v2.json")
    data = load_models_json()
    jsonschema.validate(data, schema)

def test_no_missing_fields():
    """No model has null for required fields."""
    for model in load_models().values():
        assert model.capabilities.streaming is not None
        assert model.limits.max_context_tokens is not None
```

### 2. Code Assumption Tests

```python
def test_no_hardcoded_defaults():
    """Code doesn't use hardcoded defaults."""
    # Grep for DEFAULT_TEMPERATURE should fail
    # Grep for context_window fallbacks should fail

def test_no_provider_capability_checks():
    """No code checks provider-level capabilities."""
    # Code should check model.capabilities, not provider caps
```

### 3. Integration Tests

```python
def test_temperature_validation():
    """Temperature validated against model's actual range."""
    config = get_model_config("claude-sonnet-4-5")
    assert validate_temperature(config, 0.5) == True
    assert validate_temperature(config, 2.0) == False

def test_ollama_model_resolution():
    """Ollama models resolve correctly without hardcoded map."""
    config = get_model_config("local:mistral")
    assert config.api.ollama_model == "mistral:7b"
```

## Success Criteria

- ✅ Zero hardcoded defaults in codebase
- ✅ All model capabilities explicit in JSON
- ✅ Parameter ranges validated against schema
- ✅ No provider-level capability assumptions
- ✅ Clean separation of API-specific fields
- ✅ Self-documenting schema with examples
- ✅ Backward compatible with v1 schemas
- ✅ Complete test coverage

## Future Enhancements

Once v2.0 is stable:

1. **Per-model rate limit overrides** - Users can customize in their override file
2. **Capability-based model selection** - "Give me models with vision support"
3. **Cost optimization** - Automatically suggest cheaper equivalent models
4. **Parameter validation** - Reject invalid temperature/top_p values at CLI
5. **Model comparison** - `pidgin models --compare sonnet,opus,gpt-4o`
6. **Auto-update pricing** - Monthly job to refresh cost data

## References

- Current schema: `pidgin/data/models_schema.json` (v1.0)
- Model loader: `pidgin/config/model_loader.py`
- Provider capabilities: `pidgin/config/provider_capabilities.py` (to be removed)
- Model types: `pidgin/config/model_types.py`
