# Pidgin Tools

Auxiliary tools for maintaining pidgin data. **These are NOT part of the pidgin package.**

## Purpose

These tools help maintain model pricing and configuration data that pidgin uses, but they:
- Are NOT included in the pidgin pip/pipx package
- Have NO dependencies beyond Python standard library
- Are only used for development/maintenance

## Tools

### `pricing/` - Model Pricing Data

Maintains model pricing information extracted from provider documentation.

**Usage:**
```bash
cd tools/pricing
python3 model_pricing_builder.py
```

This generates `model_pricing.json` with current pricing for:
- OpenAI models (GPT-4, GPT-5, O-series)
- Anthropic Claude models
- Google Gemini models
- xAI Grok models

**Data sources:**
- OpenAI: Manual extraction from screenshots of platform.openai.com/docs/pricing
- Anthropic: docs.anthropic.com pricing page
- Google: ai.google.dev rate limits page
- xAI: x.ai/api documentation

## How to Update Pricing

1. Take screenshots of provider pricing pages
2. Update the data in `model_pricing_builder.py`
3. Run the script to regenerate `model_pricing.json`
4. Copy the JSON to where pidgin expects it (if needed)

## Future Tools

Potential additions:
- Database migration scripts
- Experiment analysis tools
- Cost calculators

## Important

These tools are intentionally kept simple:
- No web scraping (unreliable with React/SPA sites)
- No heavy dependencies (no playwright, selenium, etc.)
- Manual data entry from authoritative sources
- Clear data provenance