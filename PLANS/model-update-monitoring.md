# Model Update Monitoring Plan

## Overview

Create an automated system to monitor frontier AI labs for new models, deprecated models, and metadata changes while maintaining Pidgin's curated approach to model configuration.

## Goals

1. Stay current with model releases without manual checking
2. Maintain curation quality - no automatic additions
3. Track comprehensive changes: new, removed, and updated models
4. Focus only on conversational AI models
5. Provide clear, actionable reports for maintainers

## Implementation

### 1. Model Discovery Script

Create `scripts/check_model_updates.py` with the following functionality:

#### API Endpoints

```python
ENDPOINTS = {
    'anthropic': 'https://api.anthropic.com/v1/models',
    'openai': 'https://api.openai.com/v1/models',
    'google': 'TBD - research endpoint',
    'xai': 'TBD - research endpoint'
}
```

#### Filtering Logic

Include only models that:
- Support chat/completion endpoints
- Accept text input (with or without images)
- Return text output
- Are not specialized (embeddings, audio, image generation)

Exclude models matching patterns:
- `dall-e-*` (image generation)
- `whisper-*` (speech to text)
- `tts-*` (text to speech)
- `text-embedding-*` (embeddings)
- `babbage-*`, `curie-*`, `ada-*` (legacy)

#### Change Detection

Track three types of changes:

1. **New Models**
   - Present in API response
   - Not in our configuration
   - Match our inclusion criteria

2. **Removed Models**
   - Present in our configuration
   - Not in API response
   - May indicate deprecation

3. **Updated Models**
   - Present in both API and config
   - Metadata differences:
     - Context window size
     - Pricing information
     - Deprecation status
     - Model family/succession

### 2. Data Storage

Store last check results for comparison:

```json
{
  "last_check": "2025-01-20T10:00:00Z",
  "models": {
    "anthropic": {
      "claude-3-opus-20241022": {
        "context_window": 200000,
        "status": "active"
      }
    }
  }
}
```

### 3. GitHub Issue Creation

When changes are detected, create an issue with:

#### Issue Title
`Model Updates Detected - YYYY-MM-DD`

#### Issue Body Format
```markdown
## Model Changes Detected - 2025-01-20

### New Models

**Provider Name**
- model-id: context window, description
  - Recommendation: Add/Skip with reasoning

### Removed Models

**Provider Name**
- model-id: last known details
  - Recommendation: Mark deprecated/Remove

### Updated Models

**Provider Name**
- model-id:
  - Change type: old value -> new value
  - Note: Additional context

---
Please review and update configurations accordingly.
```

#### Issue Labels
- `new-model` - For new model additions
- `deprecated-model` - For removed models
- `model-update` - For metadata changes
- `needs-review` - All issues

### 4. GitHub Actions Workflow

Create `.github/workflows/check-models.yml`:

```yaml
name: Check for Model Updates

on:
  schedule:
    # Run weekly on Mondays at 9 AM UTC
    - cron: '0 9 * * 1'
  workflow_dispatch: # Allow manual runs

jobs:
  check-models:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install requests pyyaml
    
    - name: Check for model updates
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        # Add other API keys as needed
      run: |
        python scripts/check_model_updates.py
```

### 5. CLI Integration

Add command to manually check for updates:

```bash
pidgin models --check-updates
```

This command should:
- Show currently configured models
- Indicate which are available/deprecated
- Suggest running the full update check
- Display results in a clean table format

### 6. Error Handling

Handle various failure modes gracefully:
- API endpoints unreachable
- Rate limits exceeded
- Invalid API responses
- Missing API keys

Fall back to showing cached results with appropriate warnings.

## Security Considerations

- Store API keys as GitHub secrets
- Use minimal permissions for API access
- Don't expose sensitive pricing information
- Rate limit checks to avoid abuse

## Future Enhancements

1. **Notification Options**
   - Slack/Discord webhooks for urgent updates
   - Email summaries for maintainers

2. **Historical Tracking**
   - Graph of model releases over time
   - Context window growth trends
   - Pricing evolution

3. **Performance Benchmarks**
   - Link to published benchmarks
   - Track claimed improvements

## Success Criteria

1. Zero manual checking required
2. No false positives (irrelevant models)
3. Clear, actionable reports
4. Maintains curation quality
5. Respects API rate limits