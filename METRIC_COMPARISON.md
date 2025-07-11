# Metrics Comparison: Documentation vs Implementation

## Summary

This document compares the metrics defined in `docs/metrics.md` with the actual implementation in the database schema and metric calculator.

## Key Findings

### 1. Missing Metrics in Implementation

The following metrics are documented but **NOT implemented** in the calculator:

#### Information Theory
- **Character Entropy** (`char_entropy_a/b`) - Only word entropy is calculated

#### Symbol & Punctuation
- **Symbol Density** (`symbol_density_a/b`) - Not calculated as a ratio
- **Emoji Count** (`emoji_count_a/b`) - Not tracked separately
- **Arrow Usage** (`arrow_count_a/b`) - Not tracked
- **Math Symbol Count** (`math_symbol_count_a/b`) - Not tracked separately

#### Linguistic Patterns  
- **Question Density** (`question_density_a/b`) - Only count is tracked, not density
- **Hedge Word Density** (`hedge_density_a/b`) - Only count is tracked, not density
- **Agreement Count** (`agreement_count_a/b`) - Named as `agreement_markers` in implementation

#### Lexical Diversity
- **Hapax Legomena Ratio** (`hapax_ratio_a/b`) - Not calculated
- **Lexical Diversity Index (LDI)** as defined (using bigrams/trigrams) - Different calculation used

#### Repetition Metrics
- **Repeated Bigrams** (`repeated_bigrams_a/b`) - Not calculated
- **Repeated Trigrams** (`repeated_trigrams_a/b`) - Not calculated

#### Cross-Agent Metrics
- **Message Length Ratio** (`length_ratio`) - Not calculated
- **Sentence Pattern Similarity** (`sentence_pattern_similarity`) - Not calculated
- **Repetition Ratio** (`repetition_ratio`) - Not calculated as documented

### 2. Naming Mismatches

Several metrics have different names in implementation:

| Documentation | Implementation |
|--------------|----------------|
| `vocabulary_size_a/b` | `message_a/b_unique_words` |
| `ttr_a/b` | `message_a/b_type_token_ratio` |
| `ldi_a/b` | `message_a/b_lexical_diversity` |
| `word_entropy_a/b` | `message_a/b_entropy` |
| `agreement_count_a/b` | `message_a/b_agreement_markers` |

### 3. Schema vs Calculator Mismatches

The database schema defines these columns but they're not populated correctly:

- **`topic_similarity`** - Always set to 0.0
- **`style_match`** - Always set to 0.0  
- **`message_a/b_response_time_ms`** - Always set to 0
- **`turn_start_time`, `turn_end_time`, `duration_ms`** - Always NULL

### 4. Additional Metrics in Implementation

The implementation includes metrics not documented:

- **`new_words`** - Words not seen before by each agent
- **`disagreement_markers`** - Count of disagreement phrases
- **`politeness_markers`** - Count of polite phrases
- **`formality_score`** - Formality measure
- **`starts_with_acknowledgment`** - Boolean flag
- **`unique_word_ratio`** - Simple TTR calculation
- **Word frequencies as JSON** - Stored but not documented

### 5. Calculation Differences

Some metrics are calculated differently than documented:

1. **Lexical Diversity Index**: 
   - Documented: `(unique_bigrams + unique_trigrams) / (total_bigrams + total_trigrams)`
   - Implemented: Simple ratio based on vocabulary size and word count

2. **Type-Token Ratio**:
   - Calculated inline during import as `vocabulary_size / max(word_count, 1)`
   - Not using the calculator's `unique_word_ratio`

3. **Compression Ratio**:
   - Documented as zlib compression ratio
   - Implementation unclear if using zlib

## Recommendations

1. **Update Documentation**: Either update `docs/metrics.md` to reflect actual implementation or implement missing metrics

2. **Fix Non-functional Metrics**: Remove or implement `topic_similarity`, `style_match`, and timing metrics

3. **Standardize Naming**: Use consistent names between documentation and code

4. **Implement Priority Metrics**:
   - Character entropy (for deeper analysis)
   - Symbol density (for pidgin emergence tracking)
   - Hapax legomena ratio (for vocabulary innovation)
   - Repeated bigrams/trigrams (for phrase-level patterns)
   - Message length ratio (for structural convergence)

5. **Remove Unused Schema Columns**: If metrics won't be implemented, remove from schema to avoid confusion

## Database Column Mapping

The actual database insertion maps metrics as follows:

```python
# From import_service.py
convergence_score → existing_metric.get('convergence_score', 0.0)  # From live calc
vocabulary_overlap → metrics['convergence'].get('vocabulary_overlap', 0.0)
structural_similarity → metrics['convergence'].get('structural_similarity', 0.0)
topic_similarity → 0.0  # NOT IMPLEMENTED
style_match → 0.0  # NOT IMPLEMENTED

# Per-agent metrics use 'message_a/b_' prefix instead of just suffix
message_a_length → metrics['agent_a']['message_length']
message_a_word_count → metrics['agent_a']['word_count']
message_a_unique_words → metrics['agent_a']['vocabulary_size']
# ... etc
```

This mismatch between the documented metric names and implementation makes analysis queries more complex than necessary.