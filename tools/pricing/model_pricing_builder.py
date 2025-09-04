#!/usr/bin/env python3
"""
Simple model pricing data builder
Takes manually extracted pricing data from screenshots and builds a comprehensive JSON file
No web scraping, no heavy dependencies - just data organization
"""

import json
from datetime import datetime
from typing import Dict, List


def build_openai_pricing() -> List[Dict]:
    """OpenAI pricing from screenshots provided by user"""
    models = [
        # GPT-5 series (from first screenshot)
        {"model_id": "gpt-5", "input": 1.25, "cached_input": 0.125, "output": 10.00},
        {
            "model_id": "gpt-5-mini",
            "input": 0.25,
            "cached_input": 0.025,
            "output": 2.00,
        },
        {
            "model_id": "gpt-5-nano",
            "input": 0.05,
            "cached_input": 0.005,
            "output": 0.40,
        },
        {
            "model_id": "gpt-5-chat-latest",
            "input": 1.25,
            "cached_input": 0.125,
            "output": 10.00,
        },
        # GPT-4.1 series
        {"model_id": "gpt-4.1", "input": 2.00, "cached_input": 0.50, "output": 8.00},
        {
            "model_id": "gpt-4.1-mini",
            "input": 0.40,
            "cached_input": 0.10,
            "output": 1.60,
        },
        {
            "model_id": "gpt-4.1-nano",
            "input": 0.10,
            "cached_input": 0.025,
            "output": 0.40,
        },
        # GPT-4o series
        {"model_id": "gpt-4o", "input": 2.50, "cached_input": 1.25, "output": 10.00},
        {
            "model_id": "gpt-4o-2024-05-13",
            "input": 5.00,
            "cached_input": None,
            "output": 15.00,
        },
        {
            "model_id": "gpt-4o-audio-preview",
            "input": 2.50,
            "cached_input": None,
            "output": 10.00,
        },
        {
            "model_id": "gpt-4o-realtime-preview",
            "input": 5.00,
            "cached_input": 2.50,
            "output": 20.00,
        },
        {
            "model_id": "gpt-4o-mini",
            "input": 0.15,
            "cached_input": 0.075,
            "output": 0.60,
        },
        {
            "model_id": "gpt-4o-mini-audio-preview",
            "input": 0.15,
            "cached_input": None,
            "output": 0.60,
        },
        {
            "model_id": "gpt-4o-mini-realtime-preview",
            "input": 0.60,
            "cached_input": 0.30,
            "output": 2.40,
        },
        # O-series reasoning models
        {"model_id": "o1", "input": 15.00, "cached_input": 7.50, "output": 60.00},
        {
            "model_id": "o1-mini",
            "input": 3.00,
            "cached_input": 1.50,
            "output": 12.00,
        },  # From API docs
        {"model_id": "o1-pro", "input": 150.00, "cached_input": None, "output": 600.00},
        # O3 series
        {"model_id": "o3", "input": 2.00, "cached_input": 0.50, "output": 8.00},
        {"model_id": "o3-pro", "input": 20.00, "cached_input": None, "output": 80.00},
        {
            "model_id": "o3-deep-research",
            "input": 10.00,
            "cached_input": 2.50,
            "output": 40.00,
        },
        # O4 series
        {"model_id": "o4-mini", "input": 1.10, "cached_input": 0.275, "output": 4.40},
        # GPT-4 legacy (from second screenshot)
        {"model_id": "gpt-4", "input": 30.00, "cached_input": None, "output": 60.00},
        {
            "model_id": "gpt-4-32k",
            "input": 60.00,
            "cached_input": None,
            "output": 120.00,
        },
        {
            "model_id": "gpt-4-turbo",
            "input": 10.00,
            "cached_input": None,
            "output": 30.00,
        },
        {
            "model_id": "gpt-4-turbo-preview",
            "input": 10.00,
            "cached_input": None,
            "output": 30.00,
        },
        # GPT-3.5 series
        {
            "model_id": "gpt-3.5-turbo",
            "input": 0.50,
            "cached_input": None,
            "output": 1.50,
        },
        {
            "model_id": "gpt-3.5-turbo-16k",
            "input": 3.00,
            "cached_input": None,
            "output": 4.00,
        },
    ]

    # Add provider and format
    for model in models:
        model["provider"] = "openai"
        model["currency"] = "USD"
        model["unit"] = "per_million_tokens"

    return models


def build_anthropic_pricing() -> List[Dict]:
    """Anthropic pricing from their docs"""
    models = [
        # Claude 3.5 series
        {
            "model_id": "claude-3-5-sonnet-20241022",
            "display_name": "Claude 3.5 Sonnet",
            "input": 3.00,
            "cached_input": 0.30,
            "output": 15.00,
        },
        {
            "model_id": "claude-3-5-haiku-20241022",
            "display_name": "Claude 3.5 Haiku",
            "input": 0.80,
            "cached_input": 0.08,
            "output": 4.00,
        },
        # Claude 3 Opus
        {
            "model_id": "claude-3-opus-20240229",
            "display_name": "Claude 3 Opus",
            "input": 15.00,
            "cached_input": 1.50,
            "output": 75.00,
        },
        # Claude 3 Haiku
        {
            "model_id": "claude-3-haiku-20240307",
            "display_name": "Claude 3 Haiku",
            "input": 0.25,
            "cached_input": 0.03,
            "output": 1.25,
        },
    ]

    for model in models:
        model["provider"] = "anthropic"
        model["currency"] = "USD"
        model["unit"] = "per_million_tokens"

    return models


def build_google_pricing() -> List[Dict]:
    """Google pricing - mostly free tier with rate limits"""
    models = [
        # Gemini 2.0
        {
            "model_id": "gemini-2.0-flash-exp",
            "display_name": "Gemini 2.0 Flash",
            "input": 0.0,
            "output": 0.0,
            "tier": "free",
            "rpm": 10,
            "tpm": 1000000,
        },
        # Gemini 1.5
        {
            "model_id": "gemini-1.5-pro",
            "display_name": "Gemini 1.5 Pro",
            "input": 3.50,
            "cached_input": 0.875,
            "output": 10.50,
        },  # Paid tier
        {
            "model_id": "gemini-1.5-flash",
            "display_name": "Gemini 1.5 Flash",
            "input": 0.075,
            "cached_input": 0.01875,
            "output": 0.30,
        },  # Paid tier
    ]

    for model in models:
        model["provider"] = "google"
        model["currency"] = "USD"
        model["unit"] = "per_million_tokens"

    return models


def build_xai_pricing() -> List[Dict]:
    """xAI Grok pricing"""
    models = [
        {
            "model_id": "grok-2-1212",
            "display_name": "Grok 2",
            "input": 2.00,
            "output": 10.00,
        },
        {
            "model_id": "grok-2-vision-1212",
            "display_name": "Grok 2 Vision",
            "input": 2.00,
            "output": 10.00,
        },
        {
            "model_id": "grok-beta",
            "display_name": "Grok Beta",
            "input": 5.00,
            "output": 15.00,
        },
    ]

    for model in models:
        model["provider"] = "xai"
        model["currency"] = "USD"
        model["unit"] = "per_million_tokens"
        model["cached_input"] = None  # xAI doesn't have cache pricing yet

    return models


def build_complete_pricing_data():
    """Build complete pricing dataset from all providers"""

    all_models = []
    all_models.extend(build_openai_pricing())
    all_models.extend(build_anthropic_pricing())
    all_models.extend(build_google_pricing())
    all_models.extend(build_xai_pricing())

    # Group by provider
    by_provider = {}
    for model in all_models:
        provider = model["provider"]
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)

    # Build final structure
    data = {
        "metadata": {
            "version": "1.0.0",
            "updated": datetime.now().isoformat(),
            "sources": {
                "openai": "Screenshots from platform.openai.com/docs/pricing",
                "anthropic": "docs.anthropic.com/en/docs/about-claude/pricing",
                "google": "ai.google.dev/gemini-api/docs/rate-limits",
                "xai": "x.ai/api",
            },
            "total_models": len(all_models),
        },
        "providers": by_provider,
        "models": all_models,
    }

    return data


def main():
    """Generate the pricing JSON file"""
    print("Building model pricing data...")

    data = build_complete_pricing_data()

    # Save to JSON
    output_file = "model_pricing.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Saved {data['metadata']['total_models']} models to {output_file}")

    # Print summary
    print("\nSummary by provider:")
    for provider, models in data["providers"].items():
        print(f"  {provider}: {len(models)} models")

        # Show price range for text models
        prices = [(m.get("input", 0), m.get("output", 0)) for m in models]
        if prices and any(p[0] > 0 for p in prices):
            min_in = min(p[0] for p in prices if p[0] > 0)
            max_in = max(p[0] for p in prices)
            min_out = min(p[1] for p in prices if p[1] > 0)
            max_out = max(p[1] for p in prices)
            print(f"    Input: ${min_in:.3f} - ${max_in:.2f} per 1M tokens")
            print(f"    Output: ${min_out:.3f} - ${max_out:.2f} per 1M tokens")


if __name__ == "__main__":
    main()
