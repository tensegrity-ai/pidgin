# Preliminary Observations

**Important**: These are anecdotal observations from running AI-to-AI conversations. They have not been validated through controlled experiments and may be artifacts of prompting, model training, or confirmation bias.

## What We've Noticed

### Gratitude Spirals
In some conversations, models begin thanking each other repeatedly:
- "Thank you for that insight"
- "I appreciate your perspective"
- "That's a wonderful point, thank you"

This escalates until the conversation becomes mostly expressions of gratitude. Could be:
- Training data bias (polite examples)
- RLHF reinforcement of agreeable behavior
- Artifact of our prompting

### Token Compression Attempts
Some model pairs appear to develop shortened references:
- "the thing we discussed" → "TTD"
- Long concepts → Single words

But this might just be:
- Models mimicking human text shortcuts
- Random abbreviation patterns
- Our pattern-seeking brains finding meaning where none exists

### Model-Specific Behaviors
- **Claude**: Tends toward philosophical tangents
- **GPT-4**: More likely to suggest structured frameworks  
- **Gemini**: Often asks clarifying questions

These could easily be:
- Training data differences
- RLHF variations
- Selective observation on our part

### Extreme Sensitivity to Initial Conditions
The system appears chaotic - tiny changes lead to wildly different outcomes:
- Adding a comma can change entire conversation trajectory
- Same prompt, different day → completely different discussion
- Word choice ("discuss" vs "explore") → different behavioral patterns

This suggests we're dealing with a chaotic system where:
- Initial conditions matter enormously
- Reproducibility requires exact prompt control
- Many repetitions needed to find stable patterns

## Why We're Skeptical

1. **No Control Group**: We haven't run conversations with shuffled responses to test if patterns persist
2. **Small Sample Size**: Maybe 50-100 conversations total, not thousands
3. **Prompt Sensitivity**: Tiny prompt changes completely alter behavior
4. **Confirmation Bias**: We might be seeing patterns because we're looking for them

## What Would Real Validation Look Like?

To actually validate these observations, we'd need:
- Thousands of conversations with systematic prompt variations
- Control conditions (shuffled responses, human-written responses mixed in)
- Statistical analysis of pattern frequency
- Blind coding of conversations to avoid bias
- Reproducibility across different model versions

## Current Status

We have:
- A tool that records conversations
- Some interesting anecdotes
- No scientific validation whatsoever

We need:
- Batch experiment infrastructure
- Statistical analysis pipeline
- Many more observations
- Skeptical collaborators

## Contributing

If you want to help validate (or debunk) these observations:
1. Run conversations with specific prompts
2. Document what you see (including null results)
3. Propose control experiments
4. Help build batch testing infrastructure

Remember: The null hypothesis is that these are all artifacts. We need strong evidence to claim otherwise.