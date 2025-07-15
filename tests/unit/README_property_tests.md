# Property-Based Testing for Metrics

This directory contains property-based tests for the Pidgin metrics calculation system using [Hypothesis](https://hypothesis.readthedocs.io/).

## Overview

Property-based testing complements our unit tests by:
- Testing with automatically generated inputs
- Finding edge cases we might not have considered
- Verifying mathematical invariants and properties
- Ensuring consistency across different metric calculations

## Test Files

### test_metrics_property.py
Core property tests for individual metric calculators:
- **TextAnalyzerProperties**: Tests text analysis functions (tokenization, sentence splitting, etc.)
- **LinguisticAnalyzerProperties**: Tests linguistic metrics (entropy, diversity, formality scores)
- **ConvergenceCalculatorProperties**: Tests convergence metrics (overlap, similarity, mimicry)
- **MetricsCalculatorProperties**: Tests the main metrics calculator
- **EdgeCases**: Tests specific edge cases with generated data

### test_metrics_invariants.py
Tests mathematical invariants and relationships between metrics:
- **MetricInvariants**: Properties that should always hold (e.g., vocabulary size ≤ word count)
- **MetricRelationships**: Relationships between different metrics
- **StatefulProperties**: Properties involving state across multiple conversation turns
- **EdgeCasesWithProperties**: Edge cases like emoji-heavy or math-heavy text

## Key Properties Being Tested

### Range Constraints
- All ratios and probabilities should be between 0 and 1
- Counts should be non-negative
- Entropy should be bounded by log2(alphabet_size)

### Consistency Properties
- Tokenization should be case-insensitive
- Word count should match number of tokens
- Message length should equal character count

### Symmetry Properties
- Vocabulary overlap should be symmetric: overlap(A,B) = overlap(B,A)
- Message length ratio should be symmetric
- Cross repetition should be symmetric

### Monotonicity Properties
- Cumulative vocabulary should grow monotonically
- New words count should decrease over time (or stay constant)

### Mathematical Invariants
- Unique word ratio = vocabulary_size / word_count
- Special symbol count ≥ emoji_count + arrow_count
- Sum of linguistic markers ≤ total word count

## Running the Tests

Run all property tests:
```bash
poetry run pytest tests/unit/test_metrics_property.py tests/unit/test_metrics_invariants.py -v
```

Run with more examples (slower but more thorough):
```bash
poetry run pytest tests/unit/test_metrics_property.py --hypothesis-profile=dev -v
```

Run a specific test class:
```bash
poetry run pytest tests/unit/test_metrics_property.py::TestTextAnalyzerProperties -v
```

## Custom Strategies

We define several custom Hypothesis strategies for generating realistic test data:

- `sentence_strategy()`: Generates sentences with punctuation
- `message_strategy()`: Generates multi-sentence messages
- `word_list_strategy()`: Generates lists of words
- `repeated_word_text()`: Generates text with controlled repetition
- `mixed_case_text()`: Generates text with mixed capitalization
- `structured_message()`: Generates messages with known structure

## Adding New Property Tests

When adding new metrics or modifying existing ones:

1. Identify the properties/invariants of your metric
2. Add test methods to the appropriate test class
3. Use appropriate Hypothesis strategies for input generation
4. Consider edge cases (empty text, unicode, special characters)
5. Test relationships with other metrics if applicable

Example template:
```python
@given(st.text())
def test_my_metric_property(self, text):
    """My metric should satisfy this property."""
    result = MyAnalyzer.calculate_metric(text)
    
    # Test the property
    assert 0.0 <= result <= 1.0  # Example: bounded metric
    assert result >= 0  # Example: non-negative count
```

## Benefits

Property-based testing has helped us:
- Find edge cases in tokenization with special characters
- Ensure mathematical consistency across metrics
- Verify that caching doesn't affect results
- Test with a wide variety of input data automatically
- Catch boundary conditions in entropy calculations
- Ensure proper handling of empty/whitespace-only text