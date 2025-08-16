#!/usr/bin/env python3
"""Generate model reference documentation in multiple formats."""

import csv
import json
from pathlib import Path

# Import model configurations
from pidgin.config.models import MODELS


def generate_markdown() -> str:
    """Generate markdown table of all models."""
    lines = ["# Pidgin Model Reference\n"]
    lines.append(
        "This document lists all available models in Pidgin with their aliases.\n"
    )

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
        lines.append(
            "| Model ID | Display Name | Aliases | Context | Deprecated | Notes |"
        )
        lines.append(
            "|----------|--------------|---------|---------|------------|-------|"
        )

        # Sort models within provider
        for model_id, config in sorted(providers[provider], key=lambda x: x[0]):
            aliases = ", ".join(f"`{a}`" for a in config.aliases)
            context = f"{config.context_window:,}"
            deprecated = "Yes" if config.deprecated else "No"
            notes = config.notes or "-"

            lines.append(
                f"| `{model_id}` | {config.display_name} | {aliases} | {context} | {deprecated} | {notes} |"
            )

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

    return "\n".join(lines)


def generate_json() -> str:
    """Generate JSON format of model data."""
    data = []
    for model_id, config in MODELS.items():
        data.append(
            {
                "model_id": model_id,
                "display_name": config.display_name,
                "aliases": config.aliases,
                "provider": config.provider,
                "context_window": config.context_window,
                "deprecated": config.deprecated,
                "notes": config.notes,
            }
        )
    return json.dumps(data, indent=2)


def generate_csv() -> str:
    """Generate CSV format of model data."""
    import io

    output = io.StringIO()

    fieldnames = [
        "model_id",
        "display_name",
        "aliases",
        "provider",
        "context_window",
        "deprecated",
        "notes",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for model_id, config in MODELS.items():
        writer.writerow(
            {
                "model_id": model_id,
                "display_name": config.display_name,
                "aliases": "|".join(config.aliases),
                "provider": config.provider,
                "context_window": config.context_window,
                "deprecated": config.deprecated,
                "notes": config.notes or "",
            }
        )

    return output.getvalue()


def save_all_formats():
    """Save model reference in all formats."""
    output_dir = Path("docs/reference")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Generate and save markdown
    with open(output_dir / "models.md", "w") as f:
        f.write(generate_markdown())
    print(f"✓ Saved {output_dir / 'models.md'}")

    # Generate and save JSON
    with open(output_dir / "models.json", "w") as f:
        f.write(generate_json())
    print(f"✓ Saved {output_dir / 'models.json'}")

    # Generate and save CSV
    with open(output_dir / "models.csv", "w") as f:
        f.write(generate_csv())
    print(f"✓ Saved {output_dir / 'models.csv'}")


if __name__ == "__main__":
    save_all_formats()
