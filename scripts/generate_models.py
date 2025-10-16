#!/usr/bin/env python3
"""
Generate models.json adhering to models_schema_v2.json by combining data
from OpenRouter, provider APIs, and local overrides.

Environment variables (optional):
- OPENROUTER_API_KEY
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GOOGLE_API_KEY  (for Google AI Studio models)
- XAI_API_KEY     (if/when Grok API lists models)

Usage:
  python generate_models.py [-o models.json] [--overrides model_overrides.yaml]

The script merges data from multiple sources:
1. Local models from overrides (local:test, ollama models, etc.)
2. OpenRouter API (pricing, context windows, capabilities)
3. Provider APIs (OpenAI, Anthropic, Google, XAI)
4. Model-specific overrides (curation, aliases, capability corrections)

Requires PyYAML for overrides support: pip install pyyaml
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


SCHEMA_VERSION = "2.0.0"


def http_get(
    url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30
) -> Optional[dict]:
    req = Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            ct = resp.headers.get("Content-Type", "")
            if (
                "application/json" in ct
                or data.strip().startswith(b"{")
                or data.strip().startswith(b"[")
            ):
                return json.loads(data)
            # Non-JSON; return None
            return None
    except HTTPError as e:
        print(f"HTTP error GET {url}: {e}", file=sys.stderr)
    except URLError as e:
        print(f"URL error GET {url}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error GET {url}: {e}", file=sys.stderr)
    return None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def provider_from_openrouter_id(or_id: str) -> Tuple[Optional[str], str]:
    """Split OpenRouter model id like 'openai/gpt-4o-mini' into (provider, model_id).
    If no slash, return (None, original).
    """
    parts = or_id.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, or_id


def normalize_provider_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name = name.lower()
    # Map common variants to schema enum values
    mapping = {
        "openai": "openai",
        "anthropic": "anthropic",
        "google": "google",
        "google-ai": "google",
        "googleai": "google",
        "xai": "xai",
        "grok": "xai",
        "x.ai": "xai",
        "ollama": "ollama",
        "local": "local",
        "silent": "silent",
    }
    return mapping.get(name, name)


def fetch_openrouter_models(api_key: Optional[str]) -> List[dict]:
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = http_get(url, headers=headers)
    if not data:
        return []
    # API returns { data: [ { id, name, pricing, context_length?, ... }, ... ] }
    models = data.get("data") or data.get("models") or []
    out = []
    for m in models:
        if not isinstance(m, dict):
            continue
        # Enforce required fields presence minimum
        mid = m.get("id") or m.get("slug") or m.get("model")
        name = m.get("name") or m.get("display_name") or mid
        pricing = m.get("pricing") or {}
        context_length = (
            m.get("context_length")
            or m.get("max_context_tokens")
            or m.get("context_length_tokens")
        )
        max_output = m.get("max_output_tokens")
        out.append(
            {
                "id": mid,
                "display_name": name,
                "pricing": pricing,
                "context_length": context_length,
                "max_output_tokens": max_output,
                "raw": m,
            }
        )
    return out


def fetch_openai_models(api_key: Optional[str]) -> List[str]:
    if not api_key:
        return []
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    data = http_get(url, headers=headers)
    if not data:
        return []
    ids = []
    for m in data.get("data", []):
        mid = m.get("id")
        if isinstance(mid, str):
            ids.append(mid)
    return ids


def fetch_anthropic_models(api_key: Optional[str]) -> List[str]:
    # As of mid-2025, Anthropic provides a models list endpoint
    if not api_key:
        return []
    url = "https://api.anthropic.com/v1/models"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Accept": "application/json",
    }
    data = http_get(url, headers=headers)
    if not data:
        return []
    ids = []
    for m in data.get("data", []):
        mid = m.get("id")
        if isinstance(mid, str):
            ids.append(mid)
    return ids


def fetch_google_models(api_key: Optional[str]) -> List[str]:
    # Google AI Studio generative-language models list
    if not api_key:
        return []
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    data = http_get(url)
    if not data:
        return []
    ids = []
    for m in data.get("models", []):
        mid = m.get("name") or m.get("baseModel")
        # Google returns names like "models/gemini-1.5-pro"; strip prefix
        if isinstance(mid, str) and "/" in mid:
            mid = mid.split("/", 1)[1]
        if isinstance(mid, str):
            ids.append(mid)
    return ids


def fetch_xai_models(api_key: Optional[str]) -> List[str]:
    # If X.ai exposes a models listing endpoint, use it; otherwise, skip.
    # Placeholder for future expansion.
    return []


def load_overrides(overrides_path: str) -> Dict[str, Any]:
    """Load YAML overrides file if it exists."""
    if not yaml:
        print("PyYAML not installed; skipping overrides", file=sys.stderr)
        return {}

    if not os.path.exists(overrides_path):
        print(f"Overrides file not found: {overrides_path}", file=sys.stderr)
        return {}

    try:
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides = yaml.safe_load(f) or {}
        print(f"Loaded overrides from {overrides_path}", file=sys.stderr)
        return overrides
    except Exception as e:
        print(f"Error loading overrides: {e}", file=sys.stderr)
        return {}


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override dict into base dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def build_parameters_support(provider: str) -> dict:
    # Conservative defaults; override where we are reasonably confident
    provider = provider.lower()
    if provider == "openai":
        return {
            "temperature": {"supported": True, "range": [0.0, 2.0], "default": 1.0},
            "top_p": {"supported": True, "range": [0.0, 1.0], "default": 1.0},
            "top_k": {"supported": False, "default": None},
        }
    if provider == "anthropic":
        return {
            "temperature": {"supported": True, "range": [0.0, 1.0], "default": 0.7},
            "top_p": {"supported": True, "range": [0.0, 1.0], "default": None},
            "top_k": {"supported": True, "range": [1, 100], "default": None},
        }
    if provider == "google":
        return {
            "temperature": {"supported": True, "range": [0.0, 2.0], "default": 1.0},
            "top_p": {"supported": True, "range": [0.0, 1.0], "default": 0.95},
            "top_k": {"supported": True, "range": [1, 100], "default": 64},
        }
    if provider == "xai":
        return {
            "temperature": {"supported": True, "range": [0.0, 2.0], "default": 0.7},
            "top_p": {"supported": True, "range": [0.0, 1.0], "default": None},
            "top_k": {"supported": False, "default": None},
        }
    # Fallback: supported=false
    return {
        "temperature": {"supported": False, "default": None},
        "top_p": {"supported": False, "default": None},
        "top_k": {"supported": False, "default": None},
    }


def default_capabilities() -> dict:
    return {
        "streaming": True,
        "vision": False,
        "tool_calling": True,
        "system_messages": True,
        "extended_thinking": False,
        "json_mode": True,
        "prompt_caching": False,
    }


def derive_capabilities_from_openrouter(raw: dict, defaults: dict) -> dict:
    caps = dict(defaults)
    # Heuristics based on tags/fields if present
    tags = raw.get("tags") or []
    if isinstance(tags, list):
        tset = {str(t).lower() for t in tags}
        if any("vision" in t or "image" in t for t in tset):
            caps["vision"] = True
        if any("tool" in t or "function" in t for t in tset):
            caps["tool_calling"] = True
        if any("json" in t for t in tset):
            caps["json_mode"] = True
        if any("reason" in t or "thinking" in t for t in tset):
            caps["extended_thinking"] = True
        if any("cache" in t for t in tset):
            caps["prompt_caching"] = True
    # Some OpenRouter fields may directly encode capabilities
    for k in ["vision", "tools", "json_mode", "reasoning", "prompt_caching"]:
        if k in raw and isinstance(raw[k], bool):
            if k == "tools":
                caps["tool_calling"] = raw[k]
            elif k == "reasoning":
                caps["extended_thinking"] = raw[k]
            else:
                caps[k if k != "tools" else "tool_calling"] = raw[k]
    return caps


def build_cost_from_openrouter(pricing: dict) -> Optional[dict]:
    if not isinstance(pricing, dict):
        return None

    # Pricing can come as strings per 1M tokens (e.g., { prompt: "3.00", completion: "10.00" })
    # or nested. Normalize and parse floats. Assume USD.
    def parse_amount(val: Any) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip().replace("$", "")
        try:
            return float(s)
        except Exception:
            return None

    prompt = (
        pricing.get("prompt")
        or pricing.get("input")
        or pricing.get("input_per_1m_tokens")
    )
    completion = (
        pricing.get("completion")
        or pricing.get("output")
        or pricing.get("output_per_1m_tokens")
    )
    cache_read = pricing.get("cache_read") or pricing.get("cache_read_per_1m_tokens")
    cache_write = pricing.get("cache_write") or pricing.get("cache_write_per_1m_tokens")

    in_cost = parse_amount(prompt)
    out_cost = parse_amount(completion)
    cr = parse_amount(cache_read)
    cw = parse_amount(cache_write)

    if in_cost is None and out_cost is None:
        return None
    return {
        "input_per_1m_tokens": in_cost or 0.0,
        "output_per_1m_tokens": out_cost or 0.0,
        "cache_read_per_1m_tokens": cr if cr is not None else None,
        "cache_write_per_1m_tokens": cw if cw is not None else None,
        "currency": "USD",
        "last_updated": today_date(),
    }


def model_metadata_defaults() -> dict:
    return {
        "status": "available",
        "release_date": None,
        "deprecation_date": None,
        "curated": False,
        "stable": True,
        "description": "",
        "notes": "",
        "size": "",
    }


def build_model_entry(
    provider: str,
    model_id: str,
    display_name: Optional[str] = None,
    or_raw: Optional[dict] = None,
    or_cost: Optional[dict] = None,
    context_len: Optional[int] = None,
    max_output: Optional[int] = None,
    custom_key: Optional[str] = None,
) -> Tuple[str, dict]:
    provider_norm = normalize_provider_name(provider) or provider
    display = display_name or model_id
    caps = (
        derive_capabilities_from_openrouter(or_raw or {}, default_capabilities())
        if or_raw
        else default_capabilities()
    )
    params = build_parameters_support(provider_norm)

    limits = {
        "max_context_tokens": int(context_len)
        if isinstance(context_len, int)
        else None,
        "max_output_tokens": int(max_output) if isinstance(max_output, int) else None,
        "max_thinking_tokens": None,
    }

    # Aliases: generate simple alias candidates
    aliases: List[str] = []
    short = model_id.replace(provider_norm + "-", "").replace(provider_norm + "/", "")
    if short and short != model_id:
        aliases.append(short)

    entry = {
        "provider": provider_norm,
        "display_name": display,
        "aliases": aliases,
        "api": {
            "model_id": model_id,
        },
        "capabilities": caps,
        "limits": limits,
        "parameters": params,
        "cost": or_cost if or_cost else None,
        "metadata": model_metadata_defaults(),
        "rate_limits": None,
    }
    # Key for models map: use custom_key if provided, otherwise use simple model_id
    # (for pidgin, we prefer simple keys like "claude-sonnet-4-5" over "anthropic:claude-sonnet-4-5")
    if custom_key:
        key = custom_key
    elif provider_norm in {"local", "ollama", "silent"}:
        # For local providers, keep the prefix
        key = f"{provider_norm}:{model_id}"
    else:
        # For API providers, use simple model_id
        key = model_id
    return key, entry


def merge_models(
    openrouter_models: List[dict],
    provider_lists: Dict[str, List[str]],
    overrides: Dict[str, Any],
) -> Dict[str, dict]:
    models: Dict[str, dict] = {}

    # First, add local models from overrides
    local_models = overrides.get("local_models", [])
    for local_model in local_models:
        if not isinstance(local_model, dict):
            continue
        key = local_model.get("key")
        if not key:
            continue
        # Deep copy to avoid mutation
        models[key] = dict(local_model)
        # Remove the key field from the model entry itself
        models[key].pop("key", None)

    # Second, from OpenRouter (rich info)
    for m in openrouter_models:
        or_id = m.get("id") or ""
        provider, mid = provider_from_openrouter_id(or_id)
        provider = normalize_provider_name(provider)
        if provider not in {"openai", "anthropic", "google", "xai"}:
            # Skip providers outside schema enum (unless local/ollama/silent, which OpenRouter won't list)
            continue
        cost = build_cost_from_openrouter(m.get("pricing") or {})
        context_len = m.get("context_length")
        max_output = m.get("max_output_tokens")
        key, entry = build_model_entry(
            provider,
            mid,
            m.get("display_name") or m.get("name"),
            m.get("raw") or m,
            cost,
            context_len,
            max_output,
        )
        models[key] = entry

    # Third, from provider APIs: add anything not present
    for provider, ids in provider_lists.items():
        for mid in ids:
            # Build with default key format
            pk, entry = build_model_entry(provider, mid)
            if pk in models:
                continue
            models[pk] = entry

    # Finally, apply model-specific overrides
    model_overrides = overrides.get("model_overrides", {})
    for override_key, override_data in model_overrides.items():
        if not isinstance(override_data, dict):
            continue
        # The override might specify a custom key
        custom_key = override_data.get("key", override_key)
        # Find the model to override (try both the override_key and custom_key)
        target_key = None
        if custom_key in models:
            target_key = custom_key
        elif override_key in models:
            target_key = override_key
        else:
            # Try to find by model_id match
            for k, v in models.items():
                if v.get("api", {}).get("model_id") == override_key:
                    target_key = k
                    break

        if target_key:
            # Apply deep merge
            models[target_key] = deep_merge(models[target_key], override_data)
            # Remove the key field if present
            models[target_key].pop("key", None)

    return models


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate models.json per models_schema_v2.json"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="models.json",
        help="Output file path (default: models.json)",
    )
    parser.add_argument(
        "--overrides",
        default="model_overrides.yaml",
        help="Path to YAML overrides file (default: model_overrides.yaml)",
    )
    parser.add_argument(
        "--include-providers",
        nargs="*",
        default=["openai", "anthropic", "google", "xai"],
        help="Providers to include from their APIs (default: openai anthropic google xai)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate output against local models_schema_v2.json if jsonschema is available",
    )
    args = parser.parse_args()

    # Load overrides
    overrides_path = args.overrides
    if not os.path.isabs(overrides_path):
        # Make relative to script directory
        overrides_path = os.path.join(os.path.dirname(__file__), overrides_path)
    overrides = load_overrides(overrides_path)

    or_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anth_key = os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    xai_key = os.getenv("XAI_API_KEY")

    print("Fetching OpenRouter models ...", file=sys.stderr)
    or_models = fetch_openrouter_models(or_key)
    print(f"OpenRouter models: {len(or_models)}", file=sys.stderr)

    provider_lists: Dict[str, List[str]] = {}
    if "openai" in args.include_providers:
        print("Fetching OpenAI models ...", file=sys.stderr)
        provider_lists["openai"] = fetch_openai_models(openai_key)
        print(f"OpenAI models: {len(provider_lists['openai'])}", file=sys.stderr)
    if "anthropic" in args.include_providers:
        print("Fetching Anthropic models ...", file=sys.stderr)
        provider_lists["anthropic"] = fetch_anthropic_models(anth_key)
        print(f"Anthropic models: {len(provider_lists['anthropic'])}", file=sys.stderr)
    if "google" in args.include_providers:
        print("Fetching Google models ...", file=sys.stderr)
        provider_lists["google"] = fetch_google_models(google_key)
        print(f"Google models: {len(provider_lists['google'])}", file=sys.stderr)
    if "xai" in args.include_providers:
        print("Fetching X.ai models ...", file=sys.stderr)
        provider_lists["xai"] = fetch_xai_models(xai_key)
        print(f"X.ai models: {len(provider_lists['xai'])}", file=sys.stderr)

    models_map = merge_models(or_models, provider_lists, overrides)

    output_obj = {
        "schema_version": SCHEMA_VERSION,
        "last_updated": now_iso(),
        "generator": "generate_models.py",
        "models": models_map,
    }

    # Write output
    out_path = args.output
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_obj, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_path} with {len(models_map)} models", file=sys.stderr)

    if args.validate:
        try:
            import jsonschema  # type: ignore
        except Exception:
            print("jsonschema not installed; skipping validation", file=sys.stderr)
        else:
            # Load local schema file if present
            schema_path = os.path.join(
                os.path.dirname(__file__), "models_schema_v2.json"
            )
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as sf:
                    schema = json.load(sf)
                try:
                    jsonschema.validate(instance=output_obj, schema=schema)
                except Exception as e:
                    print(f"Validation failed: {e}", file=sys.stderr)
                    return 2
                else:
                    print("Validation passed", file=sys.stderr)
            else:
                print(
                    "Schema file models_schema_v2.json not found; skipping validation",
                    file=sys.stderr,
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
