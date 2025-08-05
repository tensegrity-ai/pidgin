#!/usr/bin/env python3
"""Sync model information and pricing from LiteLLM's model database.

This script fetches the latest model configurations and pricing from LiteLLM's
community-maintained database and generates updates for our provider files.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.error

# LiteLLM's model database URL
LITELLM_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

# Map LiteLLM provider prefixes to our provider names
PROVIDER_MAP = {
    "anthropic/": "anthropic",
    "claude": "anthropic",  # Some Claude models don't have prefix
    "openai/": "openai",
    "gpt": "openai",
    "o1": "openai",
    "o3": "openai",
    "google/": "google", 
    "gemini": "google",
    "vertex_ai/": "google",
    "xai/": "xai",
    "grok": "xai",
}

# Models we care about (filter out noise)
INCLUDE_PATTERNS = [
    # Anthropic
    "claude-3",
    "claude-3-5",
    "claude-opus",
    "claude-sonnet", 
    "claude-haiku",
    # OpenAI
    "gpt-4",
    "gpt-3.5",
    "o1",
    "o3",
    "o4",
    # Google
    "gemini",
    # xAI
    "grok",
]

# Models to skip (deprecated, test, etc.)
EXCLUDE_PATTERNS = [
    "test",
    "preview",
    "beta",
    "instruct",
    "vision",
    "0301",  # Old date-versioned models
    "0314",
    "0613",
    "ft:",  # Fine-tuned models
]


def fetch_litellm_data() -> Dict:
    """Fetch the latest model data from LiteLLM."""
    try:
        print(f"Fetching model data from LiteLLM...")
        with urllib.request.urlopen(LITELLM_URL) as response:
            data = json.loads(response.read())
        print(f"Found {len(data)} total models")
        return data
    except Exception as e:
        print(f"Error fetching LiteLLM data: {e}")
        sys.exit(1)


def determine_provider(model_id: str) -> Optional[str]:
    """Determine which provider a model belongs to."""
    model_lower = model_id.lower()
    
    for pattern, provider in PROVIDER_MAP.items():
        if model_lower.startswith(pattern):
            return provider
    
    return None


def should_include_model(model_id: str) -> bool:
    """Check if we should include this model."""
    model_lower = model_id.lower()
    
    # Check exclude patterns first
    for pattern in EXCLUDE_PATTERNS:
        if pattern in model_lower:
            return False
    
    # Check include patterns
    for pattern in INCLUDE_PATTERNS:
        if pattern in model_lower:
            return True
    
    return False


def extract_model_info(model_id: str, data: Dict) -> Dict:
    """Extract relevant information for a model."""
    info = {
        "model_id": model_id,
        "display_name": model_id.replace("-", " ").title(),
        "context_window": data.get("max_tokens") or data.get("max_input_tokens") or 128000,
    }
    
    # Extract pricing
    if "input_cost_per_token" in data:
        info["input_cost_per_million"] = data["input_cost_per_token"] * 1_000_000
    if "output_cost_per_token" in data:
        info["output_cost_per_million"] = data["output_cost_per_token"] * 1_000_000
    
    # Check for caching support (Anthropic)
    if "anthropic" in model_id.lower() or "claude" in model_id.lower():
        if "cache_read_input_token_cost" in data:
            info["supports_caching"] = True
            info["cache_read_cost_per_million"] = data["cache_read_input_token_cost"] * 1_000_000
        if "cache_creation_input_token_cost" in data:
            info["cache_write_cost_per_million"] = data["cache_creation_input_token_cost"] * 1_000_000
    
    info["pricing_updated"] = datetime.now().isoformat()[:10]
    
    return info


def load_existing_models() -> Dict[str, Dict]:
    """Load our existing model configurations."""
    # Import our model registry
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    try:
        from pidgin.config.models import MODELS
        existing = {}
        
        for model_id, config in MODELS.items():
            if config.provider not in existing:
                existing[config.provider] = {}
            existing[config.provider][model_id] = {
                "display_name": config.display_name,
                "aliases": config.aliases,
                "context_window": config.context_window,
                "input_cost_per_million": config.input_cost_per_million,
                "output_cost_per_million": config.output_cost_per_million,
            }
        
        return existing
    except ImportError as e:
        print(f"Warning: Could not import existing models: {e}")
        return {}


def generate_model_config(model_id: str, info: Dict, existing_aliases: List[str] = None) -> str:
    """Generate Python code for a ModelConfig."""
    # Use existing aliases or generate simple ones
    if existing_aliases:
        aliases = existing_aliases
    else:
        # Generate simple aliases
        aliases = []
        if "gpt-4o" in model_id:
            aliases.append("4o")
        elif "gpt-3.5" in model_id:
            aliases.append("3.5")
        elif "claude" in model_id:
            if "sonnet" in model_id:
                aliases.append("sonnet")
            elif "opus" in model_id:
                aliases.append("opus")
            elif "haiku" in model_id:
                aliases.append("haiku")
    
    lines = [
        f'    "{model_id}": ModelConfig(',
        f'        model_id="{model_id}",',
        f'        display_name="{info["display_name"]}",',
        f'        aliases={aliases},',
        f'        provider="{info["provider"]}",',
        f'        context_window={info["context_window"]},',
    ]
    
    if "input_cost_per_million" in info:
        lines.append(f'        input_cost_per_million={info["input_cost_per_million"]:.2f},')
    if "output_cost_per_million" in info:
        lines.append(f'        output_cost_per_million={info["output_cost_per_million"]:.2f},')
    if info.get("supports_caching"):
        lines.append(f'        supports_caching=True,')
        if "cache_read_cost_per_million" in info:
            lines.append(f'        cache_read_cost_per_million={info["cache_read_cost_per_million"]:.2f},')
        if "cache_write_cost_per_million" in info:
            lines.append(f'        cache_write_cost_per_million={info["cache_write_cost_per_million"]:.2f},')
    if "pricing_updated" in info:
        lines.append(f'        pricing_updated="{info["pricing_updated"]}",')
    
    lines.append('    ),')
    
    return "\n".join(lines)


def main():
    """Main sync process."""
    # Fetch latest data
    litellm_data = fetch_litellm_data()
    
    # Load existing models
    existing = load_existing_models()
    
    # Organize by provider
    updates = {
        "anthropic": {"new": [], "updated": []},
        "openai": {"new": [], "updated": []},
        "google": {"new": [], "updated": []},
        "xai": {"new": [], "updated": []},
    }
    
    # Process each model
    for model_id, data in litellm_data.items():
        if not should_include_model(model_id):
            continue
        
        provider = determine_provider(model_id)
        if not provider or provider not in updates:
            continue
        
        # Extract model information
        info = extract_model_info(model_id, data)
        info["provider"] = provider
        
        # Check if this is new or an update
        if provider in existing and model_id in existing[provider]:
            # Check if pricing changed
            existing_model = existing[provider][model_id]
            if (info.get("input_cost_per_million") != existing_model.get("input_cost_per_million") or
                info.get("output_cost_per_million") != existing_model.get("output_cost_per_million")):
                updates[provider]["updated"].append((model_id, info, existing_model.get("aliases")))
        else:
            updates[provider]["new"].append((model_id, info))
    
    # Generate report
    print("\n" + "="*60)
    print("MODEL SYNC REPORT")
    print("="*60)
    
    has_updates = False
    
    for provider in ["openai", "anthropic", "google", "xai"]:
        if not updates[provider]["new"] and not updates[provider]["updated"]:
            continue
        
        has_updates = True
        print(f"\n## {provider.upper()}")
        
        if updates[provider]["new"]:
            print(f"\nNew models found ({len(updates[provider]['new'])}):")
            for model_id, info in updates[provider]["new"][:5]:  # Show first 5
                price_str = ""
                if "input_cost_per_million" in info:
                    price_str = f" (${info['input_cost_per_million']:.2f}/${info.get('output_cost_per_million', 0):.2f})"
                print(f"  - {model_id}{price_str}")
            if len(updates[provider]["new"]) > 5:
                print(f"  ... and {len(updates[provider]['new']) - 5} more")
        
        if updates[provider]["updated"]:
            print(f"\nPricing updates found ({len(updates[provider]['updated'])}):")
            for model_id, info, _ in updates[provider]["updated"][:5]:
                print(f"  - {model_id}: ${info.get('input_cost_per_million', 0):.2f}/${info.get('output_cost_per_million', 0):.2f}")
            if len(updates[provider]["updated"]) > 5:
                print(f"  ... and {len(updates[provider]['updated']) - 5} more")
        
        # Generate code snippet
        print(f"\nTo update, add to providers/{provider}.py:")
        print("-" * 40)
        
        # Show first model as example
        if updates[provider]["new"]:
            model_id, info = updates[provider]["new"][0]
            print(generate_model_config(model_id, info))
        elif updates[provider]["updated"]:
            model_id, info, aliases = updates[provider]["updated"][0]
            print(generate_model_config(model_id, info, aliases))
    
    if not has_updates:
        print("\nNo updates needed - models are up to date!")
    else:
        print("\n" + "="*60)
        print("Run this script weekly to stay up to date with model changes.")
        print("Review generated code before adding to provider files.")
    
    # Return exit code for GitHub Actions
    sys.exit(0 if not has_updates else 1)


if __name__ == "__main__":
    main()