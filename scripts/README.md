# Pidgin Scripts

This directory contains utility scripts for maintaining and analyzing Pidgin.

## check_model_updates.py

This script checks for model and SDK updates to help maintainers keep Pidgin current.

### What it does

1. **SDK Version Check**: Compares installed SDK versions against latest PyPI releases
2. **Model Configuration Check**: Compares our curated model list against a known models list
3. **GitHub Issue Creation**: Creates issues when discrepancies are found

### How it works

Since we can't query provider APIs without API keys in GitHub Actions, this script:
- Maintains a static list of known models (`KNOWN_MODELS`)
- Compares this against our configured models
- Checks PyPI for SDK updates (no authentication needed)
- Reports any differences

### Running manually

```bash
python scripts/check_model_updates.py
```

### GitHub Actions

The script runs automatically every Monday via GitHub Actions (`.github/workflows/check-models.yml`).
It will create an issue if it finds:
- Models in the known list that aren't configured
- Configured models not in the known list
- SDK updates available

### Maintaining the known models list

When you become aware of new models:
1. Update the `KNOWN_MODELS` dictionary in the script
2. Commit the change
3. The next run will flag these for potential inclusion

### Adding new models to Pidgin

When the script identifies new models:
1. Test the model manually
2. Determine appropriate context window and other settings
3. Add to `pidgin/config/models.py`
4. Update documentation as needed


## Other Scripts

- `generate_model_reference.py`: Generates markdown documentation for supported models
- `convergence_analysis_script.py`: Analyzes conversation convergence patterns