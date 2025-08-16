#!/usr/bin/env python3
"""Check for SDK updates and compare known models against configured ones."""

import os
import re
import sys
from datetime import datetime
from typing import Dict, Set, Tuple

# Known models as of last manual update
# This list should be manually updated when we become aware of new models
KNOWN_MODELS = {
    "anthropic": {
        # Claude 3.5 family
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        # Claude 3 family
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    },
    "openai": {
        # GPT-4o family
        "gpt-4o",
        "gpt-4o-2024-11-20",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-05-13",
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18",
        # O1 family
        "o1",
        "o1-2024-12-17",
        "o1-mini",
        "o1-mini-2024-09-12",
        "o1-preview",
        "o1-preview-2024-09-12",
        # GPT-4 family
        "gpt-4-turbo",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-turbo-preview",
        "gpt-4-1106-preview",
        "gpt-4-0125-preview",
        "gpt-4",
        "gpt-4-0613",
        # GPT-3.5 family
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-1106",
    },
    "google": {
        # Gemini 2.0 family
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-thinking-exp-1219",
        # Gemini 1.5 family
        "gemini-1.5-pro",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-8b-latest",
        # Gemini 1.0 family
        "gemini-1.0-pro",
    },
    "xai": {
        # xAI Grok models
        "grok-2-1212",
        "grok-2-vision-1212",
        "grok-beta",
    },
}


def get_configured_models() -> Dict[str, Set[str]]:
    """Load currently configured models from pidgin."""
    # Import pidgin's model config
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from pidgin.config.models import MODELS

        configured = {
            "anthropic": set(),
            "openai": set(),
            "google": set(),
            "xai": set(),
        }

        for model_name, model_config in MODELS.items():
            model_id = model_config.model_id

            if "claude" in model_name:
                configured["anthropic"].add(model_id)
            elif model_name.startswith(("gpt", "o1", "o3")):
                configured["openai"].add(model_id)
            elif "gemini" in model_name:
                configured["google"].add(model_id)
            elif "grok" in model_name:
                configured["xai"].add(model_id)

        return configured
    except Exception as e:
        print(f"Error loading configured models: {e}")
        return {"anthropic": set(), "openai": set(), "google": set(), "xai": set()}


def check_pypi_versions() -> Dict[str, Tuple[str, str]]:
    """Check for SDK updates on PyPI."""
    updates = {}

    # Read current versions from pyproject.toml
    try:
        with open("pyproject.toml") as f:
            content = f.read()

        # Extract versions using regex
        patterns = {
            "anthropic": r'anthropic = "([^"]+)"',
            "openai": r'openai = "([^"]+)"',
            "google-generativeai": r'google-generativeai = "([^"]+)"',
        }

        for package, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                current_version = match.group(1).replace("^", "")

                # Get latest version from PyPI using simpler method
                try:
                    # Use curl to get PyPI JSON API
                    import json
                    import urllib.request

                    url = f"https://pypi.org/pypi/{package}/json"
                    with urllib.request.urlopen(url) as response:
                        data = json.loads(response.read())
                        latest_version = data["info"]["version"]

                        if current_version != latest_version:
                            updates[package] = (current_version, latest_version)

                except Exception as e:
                    print(f"Error checking {package} version: {e}")

    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")

    return updates


def create_github_issue(
    changes: Dict[str, any], sdk_updates: Dict[str, Tuple[str, str]]
):
    """Create a GitHub issue for model changes."""

    if (
        not changes["missing_known"]
        and not changes["configured_unknown"]
        and not sdk_updates
    ):
        print("No changes detected")
        return

    # Build issue content
    lines = ["# Model Configuration Review", ""]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # Missing known models section
    if changes["missing_known"]:
        lines.append("## 🆕 Known Models Not in Configuration")
        lines.append("")
        lines.append("These models are known to exist but are not in our curated list:")
        lines.append("")

        for provider, models in changes["missing_known"].items():
            if models:
                lines.append(f"### {provider.title()}")
                for model in sorted(models):
                    lines.append(f"- `{model}`")
                lines.append("")

    # Unknown configured models section
    if changes["configured_unknown"]:
        lines.append("## ⚠️ Configured Models Not in Known List")
        lines.append("")
        lines.append("These models are configured but not in our known models list.")
        lines.append("They may be deprecated or the known list needs updating:")
        lines.append("")

        for provider, models in changes["configured_unknown"].items():
            if models:
                lines.append(f"### {provider.title()}")
                for model in sorted(models):
                    lines.append(f"- `{model}`")
                lines.append("")

    # SDK updates section
    if sdk_updates:
        lines.append("## 📦 SDK Updates Available")
        lines.append("")

        for package, (current, latest) in sdk_updates.items():
            lines.append(f"- **{package}**: {current} → {latest}")
        lines.append("")

    # Recommendations
    lines.append("## 📋 Next Steps")
    lines.append("")

    if changes["missing_known"]:
        lines.append(
            "1. Review known models not in configuration for potential inclusion"
        )
    if changes["configured_unknown"]:
        lines.append(
            "2. Verify configured models are still available or update known list"
        )
    if sdk_updates:
        lines.append("3. Update SDK dependencies and test compatibility")

    lines.append("")
    lines.append(
        "Note: The 'known models' list is manually maintained and may need updating."
    )

    # Output for GitHub Actions
    issue_body = "\n".join(lines)

    # GitHub Actions will read this output
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            # Escape newlines for GitHub Actions
            escaped_body = issue_body.replace("\n", "%0A").replace("%", "%25")
            f.write("has_changes=true\n")
            f.write(f"issue_body={escaped_body}\n")
    else:
        # Local testing - just print
        print("=== Issue Content ===")
        print(issue_body)


def main():
    """Main entry point."""
    print("Checking model configuration and SDK versions...")

    # Get configured models
    configured_models = get_configured_models()

    # Find differences between known and configured
    changes = {
        "missing_known": {},  # Known models not in our config
        "configured_unknown": {},  # Configured models not in known list
    }

    for provider in ["anthropic", "openai", "google", "xai"]:
        known = KNOWN_MODELS.get(provider, set())
        configured = configured_models.get(provider, set())

        # Known models we haven't configured
        missing = known - configured
        if missing:
            changes["missing_known"][provider] = missing

        # Configured models not in our known list
        unknown = configured - known
        if unknown:
            changes["configured_unknown"][provider] = unknown

    # Check for SDK updates
    sdk_updates = check_pypi_versions()

    # Create issue if there are changes
    create_github_issue(changes, sdk_updates)

    # Exit with appropriate code
    if any(changes.values()) or sdk_updates:
        sys.exit(0)  # Changes found
    else:
        sys.exit(0)  # No changes


if __name__ == "__main__":
    main()
