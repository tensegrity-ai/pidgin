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
  python generate_models.py --curate   # interactive curation checklist

The script merges data from multiple sources:
1. Local models from overrides (local:test, ollama models, etc.)
2. OpenRouter API (pricing, context windows, capabilities)
3. Provider APIs (OpenAI, Anthropic, Google, XAI)
4. Model-specific overrides (curation, aliases, capability corrections)

Three-tier model system:
- Essential (curated=true): Hand-picked best-of-breed (~15 models)
- Stable (stable=true): Production-ready, no experiments (~50 models)
- Extended: Everything including previews and dated variants

Requires PyYAML for overrides support: pip install pyyaml
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

# Providers we include from OpenRouter
SUPPORTED_PROVIDERS = {"openai", "anthropic", "google", "xai"}


# ---------------------------------------------------------------------------
# Stability & alias logic (ported from pidgin-tools)
# ---------------------------------------------------------------------------


def is_stable_model(model_id: str) -> bool:
    """Determine if a model is a stable release.

    Stable models:
    - Don't have date suffixes (-2024-11-20, -20241022)
    - Aren't experimental (preview, exp, beta, experimental)
    - Aren't specialized variants (lite, live, robotics, learnlm)
    - Aren't moving targets (latest)
    """
    model_lower = model_id.lower()

    # Check for date suffixes (e.g., -2024-11-20, -20241022, -0613, -0125)
    if re.search(
        r"-20[0-9]{2}-|[0-9]{4}-[0-9]{2}-[0-9]{2}|-[0-9]{8}$|-[0-9]{4}$", model_id
    ):
        return False

    # Non-conversational model prefixes/patterns
    non_chat = ["aqa", "gpt-oss"]
    if any(model_lower.startswith(p) for p in non_chat):
        return False

    # Non-conversational types (anywhere in the name)
    if "codex" in model_lower or "image" in model_lower:
        return False

    # Non-conversational suffixes
    non_chat_suffixes = [
        "-chat",  # gpt-5-chat is a variant, not the main model
        "-high",  # o3-mini-high, o4-mini-high are variants
        "-001",  # dated snapshot variants
    ]
    if any(model_lower.endswith(m) for m in non_chat_suffixes):
        return False

    unstable_markers = [
        "preview",
        "exp",
        "beta",
        "experimental",
        "alpha",
        "latest",
        "lite",
        "live",
        "robotics",
        "learnlm",
        "embedding",
        "tts",
        "whisper",
        "dall-e",
        "moderation",
        "realtime",
        "transcribe",
        "imagen",
        "veo",
        ":thinking",
        ":free",
        ":extended",
        "sora",
        "gpt-image",
        "gpt-audio",
        "babbage",
        "davinci",
        "instruct",
        "-search-",
        "deep-research",
        "safeguard",
    ]

    return not any(marker in model_lower for marker in unstable_markers)


def generate_alias(model_id: str, display_name: str, provider: str) -> Optional[str]:
    """Generate a single best alias for a model."""
    if provider not in ["openai", "anthropic", "google", "xai", "ollama", "local"]:
        return None

    name_lower = display_name.lower()
    id_lower = model_id.lower()

    if provider == "openai":
        alias_map = {
            "gpt-4": "gpt4",
            "gpt-4-turbo": "gpt4-turbo",
            "gpt-4o-mini": "4o-mini",
            "gpt-4o": "4o",
            "gpt-4.1": "gpt41",
            "gpt-4.1-mini": "gpt41-mini",
            "gpt-4.1-nano": "gpt41-nano",
            "o1-mini": "o1-mini",
            "o1": "o1",
            "o3-mini": "o3-mini",
            "o3": "o3",
            "o4-mini": "o4-mini",
        }
        if model_id in alias_map:
            return alias_map[model_id]
        if "gpt-3.5" in id_lower:
            return "3.5"

    elif provider == "anthropic":
        if "opus" in name_lower:
            if "3" in name_lower and "3." not in name_lower:
                return "opus3"
            return "opus"
        elif "sonnet" in name_lower:
            if "3.5" in name_lower:
                return "sonnet35"
            if "3.7" in name_lower:
                return "sonnet37"
            return "sonnet"
        elif "haiku" in name_lower:
            if "3" in name_lower and "3." not in name_lower:
                return "haiku3"
            return "haiku"

    elif provider == "google":
        if "flash" in name_lower:
            if "2.5" in name_lower:
                return "flash"
            elif "2.0" in name_lower:
                return "flash2"
        elif "pro" in name_lower:
            if "2.5" in name_lower:
                return "gemini"

    elif provider == "xai":
        if model_id == "grok-4":
            return "grok"
        elif "grok-3" in id_lower and "mini" not in id_lower:
            return "grok3"

    elif provider in ["ollama", "local"]:
        if ":" in model_id:
            return model_id.split(":", 1)[1]

    return None


def assign_aliases(models: Dict[str, dict]) -> None:
    """Assign aliases to models, resolving conflicts by priority."""
    alias_claims: Dict[str, str] = {}

    # First pass: preserve aliases from overrides (highest priority)
    for key, entry in models.items():
        for alias in entry.get("aliases", []):
            alias_claims[alias] = key

    # Second pass: generate aliases for models that don't have any
    for key, entry in models.items():
        if entry.get("aliases"):
            continue
        provider = entry.get("provider", "")
        display = entry.get("display_name", key)
        alias = generate_alias(key, display, provider)
        if alias and alias not in alias_claims:
            alias_claims[alias] = key
            entry["aliases"] = [alias]
        else:
            entry["aliases"] = []


# ---------------------------------------------------------------------------
# HTTP & date helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Provider fetching
# ---------------------------------------------------------------------------


def provider_from_openrouter_id(or_id: str) -> Tuple[Optional[str], str]:
    """Split OpenRouter model id like 'openai/gpt-4o-mini' into (provider, model_id)."""
    parts = or_id.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, or_id


def normalize_provider_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name = name.lower()
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
    # z-ai, thudm, etc. are NOT xai - don't map them
    return mapping.get(name, name)


def fetch_openrouter_models(api_key: Optional[str]) -> List[dict]:
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = http_get(url, headers=headers)
    if not data:
        return []
    models = data.get("data") or data.get("models") or []
    out = []
    for m in models:
        if not isinstance(m, dict):
            continue
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
    return [m["id"] for m in data.get("data", []) if isinstance(m.get("id"), str)]


def fetch_anthropic_models(api_key: Optional[str]) -> List[str]:
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
    return [m["id"] for m in data.get("data", []) if isinstance(m.get("id"), str)]


def fetch_google_models(api_key: Optional[str]) -> List[str]:
    if not api_key:
        return []
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    data = http_get(url)
    if not data:
        return []
    ids = []
    for m in data.get("models", []):
        mid = m.get("name") or m.get("baseModel")
        if isinstance(mid, str) and "/" in mid:
            mid = mid.split("/", 1)[1]
        if isinstance(mid, str):
            ids.append(mid)
    return ids


def fetch_xai_models(api_key: Optional[str]) -> List[str]:
    if not api_key:
        return []
    url = "https://api.x.ai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    data = http_get(url, headers=headers)
    if not data:
        return []
    return [m["id"] for m in data.get("data", []) if isinstance(m.get("id"), str)]


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Model building
# ---------------------------------------------------------------------------


def build_parameters_support(provider: str) -> dict:
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
    for k in ["vision", "tools", "json_mode", "reasoning", "prompt_caching"]:
        if k in raw and isinstance(raw[k], bool):
            if k == "tools":
                caps["tool_calling"] = raw[k]
            elif k == "reasoning":
                caps["extended_thinking"] = raw[k]
            else:
                caps[k] = raw[k]
    return caps


def build_cost_from_openrouter(pricing: dict) -> Optional[dict]:
    if not isinstance(pricing, dict):
        return None

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

    entry = {
        "provider": provider_norm,
        "display_name": display,
        "aliases": [],
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

    if custom_key:
        key = custom_key
    elif provider_norm in {"local", "ollama", "silent"}:
        key = f"{provider_norm}:{model_id}"
    else:
        key = model_id
    return key, entry


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


def _normalize_model_name(model_id: str) -> str:
    """Normalize a model ID for fuzzy matching.

    Strips date suffixes and normalizes separators so that
    'claude-opus-4-1-20250805' matches 'claude-opus-4.1'.
    """
    # Strip date suffix (e.g., -20250805, -20241001)
    name = re.sub(r"-\d{8}$", "", model_id)
    # Replace dots with hyphens for comparison
    name = name.replace(".", "-")
    return name.lower()


def _match_provider_to_openrouter(
    provider_model_id: str,
    provider: str,
    existing_models: Dict[str, dict],
) -> Optional[str]:
    """Try to match a provider API model ID to an existing OpenRouter model key.

    Returns the matched key, or None.
    """
    norm_provider = _normalize_model_name(provider_model_id)
    for key, entry in existing_models.items():
        if entry.get("provider") != provider:
            continue
        norm_key = _normalize_model_name(key)
        if norm_key == norm_provider:
            return key
    return None


def merge_models(
    openrouter_models: List[dict],
    provider_lists: Dict[str, List[str]],
    overrides: Dict[str, Any],
) -> Dict[str, dict]:
    models: Dict[str, dict] = {}

    # 1. Local models from overrides
    for local_model in overrides.get("local_models", []):
        if not isinstance(local_model, dict):
            continue
        key = local_model.get("key")
        if not key:
            continue
        models[key] = dict(local_model)
        models[key].pop("key", None)

    # 2. OpenRouter (rich info)
    for m in openrouter_models:
        or_id = m.get("id") or ""
        provider, mid = provider_from_openrouter_id(or_id)
        provider = normalize_provider_name(provider)
        if provider not in SUPPORTED_PROVIDERS:
            continue
        cost = build_cost_from_openrouter(m.get("pricing") or {})
        key, entry = build_model_entry(
            provider,
            mid,
            m.get("display_name") or m.get("name"),
            m.get("raw") or m,
            cost,
            m.get("context_length"),
            m.get("max_output_tokens"),
        )
        models[key] = entry

    # 3. Provider APIs: add anything not already present, and fix api.model_id
    #    for models that came from OpenRouter with non-API IDs
    for provider, ids in provider_lists.items():
        for mid in ids:
            pk, entry = build_model_entry(provider, mid)
            if pk not in models:
                # Try to match to an existing OpenRouter model by normalizing
                # e.g., "claude-opus-4-1-20250805" should match "claude-opus-4.1"
                matched = _match_provider_to_openrouter(mid, provider, models)
                if matched:
                    # Update the api.model_id to use the real provider ID
                    models[matched]["api"]["model_id"] = mid
                else:
                    models[pk] = entry

    # 4. Apply model-specific overrides
    model_overrides = overrides.get("model_overrides", {})
    for override_key, override_data in model_overrides.items():
        if not isinstance(override_data, dict):
            continue
        custom_key = override_data.get("key", override_key)
        target_key = None
        if custom_key in models:
            target_key = custom_key
        elif override_key in models:
            target_key = override_key
        else:
            for k, v in models.items():
                if v.get("api", {}).get("model_id") == override_key:
                    target_key = k
                    break

        if target_key:
            models[target_key] = deep_merge(models[target_key], override_data)
            models[target_key].pop("key", None)

    return models


def filter_stable(models: Dict[str, dict]) -> Dict[str, dict]:
    """Filter models to only stable releases. Local/ollama/silent always pass."""
    stable = {}
    for key, entry in models.items():
        provider = entry.get("provider", "")
        if provider in {"local", "ollama", "silent"}:
            entry["metadata"]["stable"] = True
            stable[key] = entry
        elif is_stable_model(key):
            entry["metadata"]["stable"] = True
            stable[key] = entry
        else:
            entry["metadata"]["stable"] = False
    return stable


# ---------------------------------------------------------------------------
# Interactive curation
# ---------------------------------------------------------------------------


def interactive_curate(models_path: str) -> int:
    """Interactive checklist to select curated models using Rich."""
    try:
        from rich.console import Console
        from rich.prompt import Confirm
        from rich.table import Table
    except ImportError:
        print(
            "Rich is required for interactive curation. Install with: pip install rich",
            file=sys.stderr,
        )
        return 1

    with open(models_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    models = data.get("models", {})
    console = Console()

    # Group by provider
    by_provider: Dict[str, List[Tuple[str, dict]]] = {}
    for key, entry in sorted(models.items()):
        provider = entry.get("provider", "unknown")
        by_provider.setdefault(provider, []).append((key, entry))

    # Provider display order
    provider_order = [
        "anthropic",
        "openai",
        "google",
        "xai",
        "ollama",
        "local",
        "silent",
    ]
    providers = [p for p in provider_order if p in by_provider]
    providers += [p for p in sorted(by_provider) if p not in providers]

    currently_curated = {
        k for k, v in models.items() if v.get("metadata", {}).get("curated")
    }

    console.print("\n[bold]Model Curation Checklist[/bold]")
    console.print(
        "Select which models should be marked as [bold cyan]curated[/bold cyan] (essential tier).\n"
    )

    new_curated: set[str] = set()

    for provider in providers:
        provider_models = by_provider[provider]
        if not provider_models:
            continue

        table = Table(
            title=f"[bold]{provider.upper()}[/bold]",
            show_header=True,
            header_style="bold",
            padding=(0, 1),
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Model ID", min_width=30)
        table.add_column("Display Name", min_width=20)
        table.add_column("Alias", min_width=10)
        table.add_column("Curated?", justify="center", width=8)

        for i, (key, entry) in enumerate(provider_models, 1):
            is_curated = key in currently_curated
            aliases = ", ".join(entry.get("aliases", []))
            curated_mark = (
                "[bold green]\u2713[/bold green]" if is_curated else "[dim]\u00b7[/dim]"
            )
            table.add_row(
                str(i),
                key,
                entry.get("display_name", ""),
                aliases or "[dim]-[/dim]",
                curated_mark,
            )

        console.print(table)

        # Ask for selections
        console.print(
            f"\nEnter model numbers to toggle curation for [bold]{provider}[/bold]"
        )
        console.print(
            "(comma-separated, or [dim]enter[/dim] to keep current, [dim]'all'[/dim] for all, [dim]'none'[/dim] for none):"
        )
        response = input("> ").strip()

        if response.lower() == "all":
            for key, _ in provider_models:
                new_curated.add(key)
        elif response.lower() == "none":
            pass
        elif response:
            # Parse comma-separated numbers
            try:
                indices = [int(x.strip()) for x in response.split(",") if x.strip()]
            except ValueError:
                console.print(
                    "[yellow]Invalid input, keeping current selections[/yellow]"
                )
                for key, _ in provider_models:
                    if key in currently_curated:
                        new_curated.add(key)
                continue

            # Start with current curation, then toggle specified indices
            provider_curated = {k for k, _ in provider_models if k in currently_curated}
            for idx in indices:
                if 1 <= idx <= len(provider_models):
                    key = provider_models[idx - 1][0]
                    if key in provider_curated:
                        provider_curated.discard(key)
                    else:
                        provider_curated.add(key)
            new_curated.update(provider_curated)
        else:
            # Keep current
            for key, _ in provider_models:
                if key in currently_curated:
                    new_curated.add(key)

        console.print()

    # Show summary
    console.print("\n[bold]Curated models summary:[/bold]")
    for key in sorted(new_curated):
        aliases = ", ".join(models[key].get("aliases", []))
        alias_str = f" ({aliases})" if aliases else ""
        console.print(f"  [green]\u2713[/green] {key}{alias_str}")

    added = new_curated - currently_curated
    removed = currently_curated - new_curated
    if added:
        console.print(f"\n[green]Added:[/green] {', '.join(sorted(added))}")
    if removed:
        console.print(f"[red]Removed:[/red] {', '.join(sorted(removed))}")
    if not added and not removed:
        console.print("\n[dim]No changes.[/dim]")
        return 0

    if not Confirm.ask("\nApply these changes?"):
        console.print("[dim]Cancelled.[/dim]")
        return 0

    # Apply changes
    for key in models:
        models[key].setdefault("metadata", {})["curated"] = key in new_curated

    data["models"] = models
    data["last_updated"] = now_iso()

    with open(models_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    console.print(
        f"\n[bold green]Saved {len(new_curated)} curated models to {models_path}[/bold green]"
    )
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate models.json per models_schema_v2.json"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="pidgin/data/models.json",
        help="Output file path (default: pidgin/data/models.json)",
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
        "--no-filter",
        action="store_true",
        help="Don't filter to stable models (include all)",
    )
    parser.add_argument(
        "--curate",
        action="store_true",
        help="Interactive curation mode: select curated models from existing models.json",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate output against local models_schema_v2.json if jsonschema is available",
    )
    args = parser.parse_args()

    # Interactive curation mode
    if args.curate:
        return interactive_curate(args.output)

    # Load overrides
    overrides_path = args.overrides
    if not os.path.isabs(overrides_path):
        overrides_path = os.path.join(os.path.dirname(__file__), overrides_path)
    overrides = load_overrides(overrides_path)

    or_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anth_key = os.getenv("ANTHROPIC_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    xai_key = os.getenv("XAI_API_KEY")

    print("Fetching OpenRouter models ...", file=sys.stderr)
    or_models = fetch_openrouter_models(or_key)
    print(f"  OpenRouter: {len(or_models)} models", file=sys.stderr)

    provider_lists: Dict[str, List[str]] = {}
    if "openai" in args.include_providers:
        print("Fetching OpenAI models ...", file=sys.stderr)
        provider_lists["openai"] = fetch_openai_models(openai_key)
        print(f"  OpenAI: {len(provider_lists['openai'])} models", file=sys.stderr)
    if "anthropic" in args.include_providers:
        print("Fetching Anthropic models ...", file=sys.stderr)
        provider_lists["anthropic"] = fetch_anthropic_models(anth_key)
        print(
            f"  Anthropic: {len(provider_lists['anthropic'])} models", file=sys.stderr
        )
    if "google" in args.include_providers:
        print("Fetching Google models ...", file=sys.stderr)
        provider_lists["google"] = fetch_google_models(google_key)
        print(f"  Google: {len(provider_lists['google'])} models", file=sys.stderr)
    if "xai" in args.include_providers:
        print("Fetching X.ai models ...", file=sys.stderr)
        provider_lists["xai"] = fetch_xai_models(xai_key)
        print(f"  X.ai: {len(provider_lists['xai'])} models", file=sys.stderr)

    all_models = merge_models(or_models, provider_lists, overrides)
    print(f"\nTotal merged: {len(all_models)} models", file=sys.stderr)

    # Filter to stable unless --no-filter
    if args.no_filter:
        models_map = all_models
    else:
        models_map = filter_stable(all_models)
        filtered = len(all_models) - len(models_map)
        print(
            f"Stable filter: kept {len(models_map)}, filtered {filtered}",
            file=sys.stderr,
        )

    # Assign aliases
    assign_aliases(models_map)

    # Sort by provider then model name
    sorted_models = dict(
        sorted(models_map.items(), key=lambda x: (x[1].get("provider", ""), x[0]))
    )

    output_obj = {
        "schema_version": SCHEMA_VERSION,
        "last_updated": now_iso(),
        "generator": "generate_models.py",
        "models": sorted_models,
    }

    out_path = args.output
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_obj, f, indent=2, ensure_ascii=False)

    # Summary
    by_provider: Dict[str, int] = {}
    curated_count = 0
    for entry in sorted_models.values():
        p = entry.get("provider", "unknown")
        by_provider[p] = by_provider.get(p, 0) + 1
        if entry.get("metadata", {}).get("curated"):
            curated_count += 1

    print(f"\nWrote {out_path} with {len(sorted_models)} models:", file=sys.stderr)
    for p in sorted(by_provider):
        print(f"  {p}: {by_provider[p]}", file=sys.stderr)
    print(f"  curated: {curated_count}", file=sys.stderr)

    if args.validate:
        try:
            import jsonschema  # type: ignore
        except Exception:
            print("jsonschema not installed; skipping validation", file=sys.stderr)
        else:
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
