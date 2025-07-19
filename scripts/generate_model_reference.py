#!/usr/bin/env python3
"""Generate model reference documentation in multiple formats."""

import csv
import json
from pathlib import Path
from typing import Dict, List

# Import model configurations
from pidgin.config.models import MODELS


def generate_markdown() -> str:
    """Generate markdown table of all models."""
    lines = ["# Pidgin Model Reference\n"]
    lines.append("This document lists all available models in Pidgin with their aliases and characteristics.\n")
    
    # Group by provider
    providers = {}
    for model_id, config in MODELS.items():
        provider = config.provider
        if provider not in providers:
            providers[provider] = []
        providers[provider].append((model_id, config))
    
    # Sort providers
    for provider in sorted(providers.keys()):
        lines.append(f"\n## {provider.capitalize()} Models\n")
        lines.append("| Model ID | Display Name | Aliases | Context | Pricing | Style | Verbosity |")
        lines.append("|----------|--------------|---------|---------|---------|-------|-----------|")
        
        # Sort models within provider
        for model_id, config in sorted(providers[provider], key=lambda x: x[0]):
            aliases = ", ".join(f"`{a}`" for a in config.aliases)
            context = f"{config.context_window:,}"
            verbosity = config.characteristics.verbosity_level
            style = config.characteristics.conversation_style
            
            lines.append(f"| `{model_id}` | {config.shortname} | {aliases} | {context} | {config.pricing_tier} | {style} | {verbosity}/10 |")
    
    # Add usage section
    lines.append("\n## Usage Examples\n")
    lines.append("You can use any of the model ID or aliases when running Pidgin:\n")
    lines.append("```bash")
    lines.append("# Using full model ID")
    lines.append("pidgin run -a claude-3-5-sonnet-20241022 -b gpt-4o")
    lines.append("")
    lines.append("# Using shorthand aliases") 
    lines.append("pidgin run -a sonnet3.5 -b 4o")
    lines.append("pidgin run -a claude -b gpt-4")
    lines.append("```\n")
    
    # Add pairing recommendations
    lines.append("## Recommended Pairings\n")
    lines.append("Based on conversation characteristics:\n")
    
    seen_pairings = set()
    for model_id, config in MODELS.items():
        for pairing in config.characteristics.recommended_pairings:
            if pairing in MODELS:
                pair = tuple(sorted([config.shortname, MODELS[pairing].shortname]))
                if pair not in seen_pairings:
                    seen_pairings.add(pair)
                    lines.append(f"- {pair[0]} + {pair[1]}")
    
    return "\n".join(lines)


def generate_json() -> str:
    """Generate JSON representation of all models."""
    output = {}
    
    for model_id, config in MODELS.items():
        output[model_id] = {
            "shortname": config.shortname,
            "aliases": config.aliases,
            "provider": config.provider,
            "context_window": config.context_window,
            "pricing_tier": config.pricing_tier,
            "characteristics": {
                "verbosity_level": config.characteristics.verbosity_level,
                "avg_response_length": config.characteristics.avg_response_length,
                "conversation_style": config.characteristics.conversation_style,
                "recommended_pairings": config.characteristics.recommended_pairings
            },
            "deprecated": config.deprecated,
            "notes": config.notes
        }
    
    return json.dumps(output, indent=2)


def generate_csv() -> str:
    """Generate CSV representation of all models."""
    output = []
    writer = csv.StringWriter()
    
    # Header
    fieldnames = [
        "model_id", "shortname", "aliases", "provider", "context_window",
        "pricing_tier", "verbosity_level", "response_length", "conversation_style",
        "deprecated", "notes"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for model_id, config in sorted(MODELS.items()):
        writer.writerow({
            "model_id": model_id,
            "shortname": config.shortname,
            "aliases": "; ".join(config.aliases),
            "provider": config.provider,
            "context_window": config.context_window,
            "pricing_tier": config.pricing_tier,
            "verbosity_level": config.characteristics.verbosity_level,
            "response_length": config.characteristics.avg_response_length,
            "conversation_style": config.characteristics.conversation_style,
            "deprecated": "Yes" if config.deprecated else "No",
            "notes": config.notes or ""
        })
    
    return "\n".join(output)


def main():
    """Generate model reference documentation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate model reference documentation")
    parser.add_argument("--csv", action="store_true", help="Also generate CSV format")
    parser.add_argument("--json", action="store_true", help="Also generate JSON format")
    parser.add_argument("--all", action="store_true", help="Generate all formats")
    args = parser.parse_args()
    
    # Always generate markdown
    with open("models-reference.md", "w") as f:
        f.write(generate_markdown())
    print("Generated models-reference.md")
    
    # Optionally generate JSON
    if args.json or args.all:
        with open("models-reference.json", "w") as f:
            f.write(generate_json())
        print("Generated models-reference.json")
    
    # Optionally generate CSV
    if args.csv or args.all:
        with open("models-reference.csv", "w") as f:
            # Header
            f.write("model_id,shortname,aliases,provider,context_window,pricing_tier,verbosity_level,response_length,conversation_style,deprecated,notes\n")
            
            # Data
            for model_id, config in sorted(MODELS.items()):
                aliases = ";".join(config.aliases)
                deprecated = "Yes" if config.deprecated else "No"
                notes = config.notes or ""
                
                f.write(f'"{model_id}","{config.shortname}","{aliases}","{config.provider}",{config.context_window},"{config.pricing_tier}",{config.characteristics.verbosity_level},"{config.characteristics.avg_response_length}","{config.characteristics.conversation_style}","{deprecated}","{notes}"\n')
        
        print("Generated models-reference.csv")
    
    # Print summary
    print(f"\nTotal models: {len(MODELS)}")
    provider_counts = {}
    for config in MODELS.values():
        provider_counts[config.provider] = provider_counts.get(config.provider, 0) + 1
    
    for provider, count in sorted(provider_counts.items()):
        print(f"  {provider}: {count} models")


if __name__ == "__main__":
    main()