# Experiments to Run

Once batch execution is implemented, these experiments could help validate or refute our observations.

## Convergence Validation

### Threshold Testing
- Run 100 conversations with identical parameters
- Measure convergence scores at each turn
- Questions:
  - What's the distribution of convergence scores?
  - Is 0.85 a good threshold?
  - Do different model pairs have different profiles?

### Initial Condition Sensitivity
- Same prompt with tiny variations
- "Hello!" vs "Hello" vs "Hello."
- Measure divergence in outcomes
- Quantify the "butterfly effect"

## Pattern Occurrence Rates

### Gratitude Spirals
- Test: 100 Claude-Claude conversations
- Control: 100 GPT-GPT conversations  
- Measure: How often do gratitude patterns emerge?
- Variables: System prompt, initial prompt, conversation length

### Compression Patterns
- Long conversations (100+ turns)
- Track message length over time
- Track vocabulary size over time
- Question: Is compression real or random?

## Model Comparison

### Same-Model vs Cross-Model
- 100 Claude-Claude
- 100 GPT-GPT
- 100 Claude-GPT
- Compare convergence rates and patterns

### Temperature Effects
- Run same conversation at different temperatures
- Does lower temperature increase convergence?
- Does higher temperature prevent patterns?

## Prompt Engineering Effects

### System Prompt Variations
- Stability level 0 (chaos) through 4 (explicit)
- Does more guidance reduce convergence?
- Do patterns change with different framings?

### Initial Prompt Categories
- Task-focused: "Solve this problem..."
- Open-ended: "Let's discuss..."
- Creative: "Imagine a world where..."
- Meta: "Let's analyze our conversation..."

## Statistical Controls

### Null Hypothesis Tests
- Random word generator conversations
- Human conversation transcripts
- Scrambled AI conversations
- Do patterns appear in controls?

### Time Series Analysis
- Convergence over time
- Autocorrelation in responses
- Periodicities in patterns

## Practical Questions

1. **Token Efficiency**: Do converged conversations use fewer tokens?
2. **Quality Degradation**: Do high-convergence conversations lose coherence?
3. **Predictability**: Can we predict convergence from early turns?
4. **Interventions**: Does pausing reset convergence? (future work)

## Implementation Priority

1. Basic rate measurements (how often do patterns occur?)
2. Statistical significance tests
3. Model comparison studies
4. Prompt sensitivity analysis

## Output Metrics

Each experiment should record:
- Convergence scores per turn
- Message lengths
- Vocabulary sizes
- Pattern occurrence flags
- Token usage
- Timestamps

This will build the dataset needed to move from anecdotes to science.