# Pidgin Model Reference

This document lists all available models in Pidgin with their aliases and characteristics.


## Anthropic Models

| Model ID | Display Name | Aliases | Context | Pricing | Style | Verbosity |
|----------|--------------|---------|---------|---------|-------|-----------|
| `claude-3-5-haiku-20241022` | Haiku | `haiku`, `haiku3.5`, `claude-haiku` | 200,000 | economy | concise | 3/10 |
| `claude-3-5-sonnet-20241022` | Sonnet3.5 | `sonnet3.5`, `claude-3.5`, `sonnet3.7`, `claude-3.7` | 200,000 | standard | analytical | 7/10 |
| `claude-3-haiku-20240307` | Haiku3 | `haiku3`, `claude-3-haiku` | 200,000 | economy | concise | 3/10 |
| `claude-4-opus-20250514` | Opus | `opus`, `opus4`, `claude-opus` | 200,000 | premium | analytical | 8/10 |
| `claude-4-sonnet-20250514` | Sonnet | `sonnet`, `sonnet4`, `claude-sonnet`, `claude` | 200,000 | standard | verbose | 6/10 |

## Google Models

| Model ID | Display Name | Aliases | Context | Pricing | Style | Verbosity |
|----------|--------------|---------|---------|---------|-------|-----------|
| `gemini-1.5-flash` | Flash-1.5 | `flash-1.5` | 1,048,576 | economy | concise | 3/10 |
| `gemini-1.5-flash-8b` | Flash-8B | `flash-8b`, `gemini-8b` | 1,048,576 | economy | concise | 2/10 |
| `gemini-1.5-pro` | Gemini-Pro | `gemini-pro`, `1.5-pro` | 2,097,152 | premium | verbose | 7/10 |
| `gemini-2.0-flash-exp` | Flash | `gemini-flash`, `flash` | 1,048,576 | economy | concise | 4/10 |
| `gemini-2.0-flash-thinking-exp` | Thinking | `gemini-thinking`, `thinking`, `flash-thinking` | 32,767 | standard | analytical | 8/10 |
| `gemini-2.5-pro` | Gemini-2.5-Pro | `gemini` | 2,097,152 | premium | balanced | 7/10 |
| `gemini-exp-1206` | Gemini-Exp | `gemini-exp`, `exp-1206` | 2,097,152 | premium | verbose | 8/10 |

## Local Models

| Model ID | Display Name | Aliases | Context | Pricing | Style | Verbosity |
|----------|--------------|---------|---------|---------|-------|-----------|
| `local:mistral` | Mistral-7B | `mistral`, `mistral7b` | 32,768 | free | verbose | 7/10 |
| `local:phi` | Phi-3 | `phi`, `phi3` | 4,096 | free | analytical | 6/10 |
| `local:qwen` | Qwen-0.5B | `qwen`, `qwen-tiny` | 32,768 | free | concise | 4/10 |
| `local:test` | TestModel | `test`, `local-test` | 8,192 | free | analytical | 5/10 |

## Openai Models

| Model ID | Display Name | Aliases | Context | Pricing | Style | Verbosity |
|----------|--------------|---------|---------|---------|-------|-----------|
| `gpt-4.1` | GPT-4.1 | `gpt-4.1` | 1,000,000 | premium | analytical | 7/10 |
| `gpt-4.1-mini` | GPT-Mini | `gpt` | 1,000,000 | standard | verbose | 5/10 |
| `gpt-4.1-nano` | GPT-Nano | `nano` | 1,000,000 | economy | concise | 3/10 |
| `gpt-4.5` | GPT-4.5 | `gpt-4.5` | 128,000 | premium | analytical | 7/10 |
| `gpt-4o` | GPT-4o | `4o` | 128,000 | standard | verbose | 6/10 |
| `gpt-4o-mini` | GPT-4o-Mini | `4o-mini` | 128,000 | economy | concise | 4/10 |
| `o3` | O3 | `o3` | 128,000 | premium | analytical | 9/10 |
| `o3-mini` | O3-Mini | `o3-mini` | 128,000 | standard | analytical | 6/10 |
| `o4-mini` | O4 | `o4-mini` | 128,000 | standard | analytical | 7/10 |
| `o4-mini-high` | O4-High | `o4-mini-high` | 128,000 | premium | analytical | 8/10 |

## Silent Models

| Model ID | Display Name | Aliases | Context | Pricing | Style | Verbosity |
|----------|--------------|---------|---------|---------|-------|-----------|
| `silent` | Silence | `void`, `quiet`, `meditation` | 999,999 | free | concise | 0/10 |

## Xai Models

| Model ID | Display Name | Aliases | Context | Pricing | Style | Verbosity |
|----------|--------------|---------|---------|---------|-------|-----------|
| `grok-2-1212` | Grok-2 | `grok-2` | 131,072 | premium | analytical | 8/10 |
| `grok-3` | Grok-3 | `grok` | 131,072 | premium | analytical | 8/10 |
| `grok-beta` | Grok-Beta | `grok-beta`, `xai` | 131,072 | premium | analytical | 7/10 |

## Usage Examples

You can use any of the model ID or aliases when running Pidgin:

```bash
# Using full model ID
pidgin run -a claude-3-5-sonnet-20241022 -b gpt-4o

# Using shorthand aliases
pidgin run -a sonnet3.5 -b 4o
pidgin run -a claude -b gpt-4
```

## Recommended Pairings

Based on conversation characteristics:

- GPT-4.1 + Opus
- O3 + Opus
- GPT-Mini + Sonnet
- Sonnet + Sonnet
- O4 + Sonnet3.5
- GPT-Mini + Sonnet3.5
- GPT-Nano + Haiku
- Haiku + Haiku
- GPT-4o-Mini + Haiku3
- Haiku3 + Haiku3
- GPT-4.1 + O3
- GPT-Mini + GPT-Mini
- GPT-Nano + GPT-Nano
- O3-Mini + O4
- GPT-Mini + O4
- O4-High + Opus
- O3 + O4-High
- GPT-4.5 + Opus
- GPT-4.1 + GPT-4.5
- GPT-4o + Sonnet
- GPT-4o + GPT-4o-Mini
- GPT-4o-Mini + GPT-Nano
- GPT-4.1 + Gemini-2.5-Pro
- Gemini-2.5-Pro + Opus
- Flash + GPT-Nano
- Flash + Flash
- O3 + Thinking
- Opus + Thinking
- Gemini-Exp + Opus
- GPT-4.1 + Gemini-Exp
- GPT-4o + Gemini-Pro
- Gemini-Pro + Sonnet
- Flash-1.5 + GPT-4o-Mini
- Flash-1.5 + Haiku
- Flash-8B + GPT-Nano
- Flash-8B + Flash-8B
- GPT-4.1 + Grok-3
- Grok-3 + Opus
- GPT-4o + Grok-Beta
- Grok-Beta + Sonnet
- GPT-4.1 + Grok-2
- Grok-2 + Sonnet
- TestModel + TestModel
- GPT-4o-Mini + TestModel
- Phi-3 + Qwen-0.5B
- Qwen-0.5B + TestModel
- Phi-3 + TestModel
- Mistral-7B + Opus
- GPT-4.1 + Mistral-7B
- Opus + Silence
- GPT-4.1 + Silence