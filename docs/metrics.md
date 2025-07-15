# Pidgin Metrics Specification

## Overview
This document defines all metrics tracked in Pidgin experiments. Each metric is calculated per turn and stored in the database for analysis.

## Database Schema

### Turns Table Structure
Each turn in a conversation generates one row with ~150 columns capturing linguistic, structural, and behavioral metrics.

## Metric Categories

### 1. Basic Text Metrics (Per Agent)

#### Message Length
- **Column**: `message_length_a`, `message_length_b`
- **Type**: INTEGER
- **Calculation**: `len(message.strip())`
- **Purpose**: Track message size changes over time

#### Word Count
- **Column**: `word_count_a`, `word_count_b`
- **Type**: INTEGER
- **Calculation**: `len(message.split())`
- **Purpose**: Basic verbosity measure

#### Sentence Count
- **Column**: `sentence_count_a`, `sentence_count_b`
- **Type**: INTEGER
- **Calculation**: Count of `.!?` terminators (minimum 1)
- **Purpose**: Track structural complexity

### 2. Lexical Diversity Metrics (Per Agent)

#### Type-Token Ratio (TTR)
- **Column**: `ttr_a`, `ttr_b`
- **Type**: REAL
- **Calculation**: `unique_words / total_words`
- **Range**: 0.0 to 1.0
- **Purpose**: Vocabulary richness indicator

#### Vocabulary Size
- **Column**: `vocabulary_size_a`, `vocabulary_size_b`
- **Type**: INTEGER
- **Calculation**: `len(set(words))`
- **Purpose**: Unique word count

#### Hapax Legomena Ratio
- **Column**: `hapax_ratio_a`, `hapax_ratio_b`
- **Type**: REAL
- **Calculation**: `words_appearing_once / total_unique_words`
- **Purpose**: Vocabulary innovation measure

#### Lexical Diversity Index (LDI)
- **Column**: `ldi_a`, `ldi_b`
- **Type**: REAL
- **Calculation**: `(unique_bigrams + unique_trigrams) / (total_bigrams + total_trigrams)`
- **Purpose**: Phrase-level diversity

### 3. Information Theory Metrics (Per Agent)

#### Shannon Entropy (Word-level)
- **Column**: `word_entropy_a`, `word_entropy_b`
- **Type**: REAL
- **Calculation**: `-Σ(p(word) * log2(p(word)))`
- **Purpose**: Information content measure

#### Character Entropy
- **Column**: `char_entropy_a`, `char_entropy_b`
- **Type**: REAL
- **Calculation**: `-Σ(p(char) * log2(p(char)))`
- **Purpose**: Character-level predictability

### 4. Symbol & Punctuation Metrics (Per Agent)

#### Symbol Density
- **Column**: `symbol_density_a`, `symbol_density_b`
- **Type**: REAL
- **Calculation**: `non_alphabetic_chars / total_chars`
- **Purpose**: Track symbolic communication emergence

#### Emoji Count
- **Column**: `emoji_count_a`, `emoji_count_b`
- **Type**: INTEGER
- **Calculation**: Count of Unicode emoji characters
- **Purpose**: Emotional expression tracking

#### Arrow Usage
- **Column**: `arrow_count_a`, `arrow_count_b`
- **Type**: INTEGER
- **Calculation**: Count of `→←↔⇒⇐⇔➜` etc.
- **Purpose**: Directional notation adoption

#### Math Symbol Count
- **Column**: `math_symbol_count_a`, `math_symbol_count_b`
- **Type**: INTEGER
- **Calculation**: Count of `≈≡≠≤≥±×÷∈∀∃` etc.
- **Purpose**: Mathematical notation usage

### 5. Linguistic Pattern Metrics (Per Agent)

#### Question Density
- **Column**: `question_density_a`, `question_density_b`
- **Type**: REAL
- **Calculation**: `sentences_with_? / total_sentences`
- **Purpose**: Interrogative vs declarative balance

#### Hedge Word Density
- **Column**: `hedge_density_a`, `hedge_density_b`
- **Type**: REAL
- **Calculation**: `hedge_words / total_words`
- **Hedge words**: perhaps, maybe, might, possibly, seems, appears, suggest, think
- **Purpose**: Uncertainty expression

#### Agreement Markers
- **Column**: `agreement_count_a`, `agreement_count_b`
- **Type**: INTEGER
- **Calculation**: Count of agreement phrases
- **Phrases**: yes, absolutely, indeed, exactly, agree, correct, right
- **Purpose**: Consensus tracking

### 6. Pronoun Usage (Per Agent)

#### First Person Singular
- **Column**: `first_person_singular_a`, `first_person_singular_b`
- **Type**: INTEGER
- **Calculation**: Count of I, me, my, mine, myself

#### First Person Plural
- **Column**: `first_person_plural_a`, `first_person_plural_b`
- **Type**: INTEGER
- **Calculation**: Count of we, us, our, ours, ourselves

#### Second Person
- **Column**: `second_person_a`, `second_person_b`
- **Type**: INTEGER
- **Calculation**: Count of you, your, yours, yourself

### 7. Repetition Metrics (Per Agent)

#### Repeated Bigrams
- **Column**: `repeated_bigrams_a`, `repeated_bigrams_b`
- **Type**: INTEGER
- **Calculation**: Count of 2-word sequences appearing 2+ times
- **Purpose**: Phrase-level repetition

#### Repeated Trigrams
- **Column**: `repeated_trigrams_a`, `repeated_trigrams_b`
- **Type**: INTEGER
- **Calculation**: Count of 3-word sequences appearing 2+ times
- **Purpose**: Longer phrase repetition

#### Self-Repetition Score
- **Column**: `self_repetition_a`, `self_repetition_b`
- **Type**: REAL
- **Calculation**: Overlap with agent's previous message
- **Purpose**: Self-consistency measure

### 8. Structural Metrics (Per Agent)

#### Average Sentence Length
- **Column**: `avg_sentence_length_a`, `avg_sentence_length_b`
- **Type**: REAL
- **Calculation**: `word_count / sentence_count`
- **Purpose**: Syntactic complexity proxy

#### Punctuation Diversity
- **Column**: `punctuation_diversity_a`, `punctuation_diversity_b`
- **Type**: INTEGER
- **Calculation**: Count of unique punctuation marks used
- **Purpose**: Stylistic variety

#### Paragraph Count
- **Column**: `paragraph_count_a`, `paragraph_count_b`
- **Type**: INTEGER
- **Calculation**: Count of `\n\n` + 1
- **Purpose**: Document structure

### 9. Cross-Agent Metrics (Computed Between A & B)

#### Overall Convergence Score
- **Column**: `convergence_score`
- **Type**: REAL
- **Calculation**: Weighted average of multiple similarity metrics
- **Range**: 0.0 (different) to 1.0 (identical)

#### Vocabulary Overlap (Jaccard)
- **Column**: `vocabulary_overlap`
- **Type**: REAL
- **Calculation**: `|vocab_A ∩ vocab_B| / |vocab_A ∪ vocab_B|`
- **Purpose**: Shared vocabulary measure

#### Message Length Ratio
- **Column**: `length_ratio`
- **Type**: REAL
- **Calculation**: `min(len_A, len_B) / max(len_A, len_B)`
- **Purpose**: Structural similarity

#### Sentence Pattern Similarity
- **Column**: `sentence_pattern_similarity`
- **Type**: REAL
- **Calculation**: Similarity of sentence count distributions
- **Purpose**: Rhythmic alignment

#### Mimicry Score
- **Column**: `mimicry_score`
- **Type**: REAL
- **Calculation**: How much B repeats phrases from A's last message
- **Purpose**: Direct copying behavior

### 10. Temporal Metrics

#### Response Time (if available)
- **Column**: `response_time_a`, `response_time_b`
- **Type**: REAL
- **Note**: Often unreliable due to rate limiting

#### Turn Number
- **Column**: `turn_number`
- **Type**: INTEGER
- **Note**: 0-indexed

### 11. Compression Metrics

#### Compression Ratio
- **Column**: `compression_ratio_a`, `compression_ratio_b`
- **Type**: REAL
- **Calculation**: `compressed_size / original_size` using zlib
- **Purpose**: Distinguish true compression from brevity

#### Repetition Ratio
- **Column**: `repetition_ratio`
- **Type**: REAL
- **Calculation**: `repeated_3+_word_phrases / total_phrases`
- **Purpose**: Cross-message repetition

### 12. Named Entity Metrics (Optional)

#### Proper Noun Count
- **Column**: `proper_noun_count_a`, `proper_noun_count_b`
- **Type**: INTEGER
- **Calculation**: Words starting with capital (excluding sentence start)

#### Number Count
- **Column**: `number_count_a`, `number_count_b`
- **Type**: INTEGER
- **Calculation**: Tokens that are numeric

## Aggregated Metrics (Calculated from Turn Data)

### Conversation-Level
- **Final convergence**: Last turn's convergence score
- **Peak convergence**: Maximum convergence reached
- **Convergence velocity**: Rate of convergence change
- **Symbol adoption turn**: First turn with significant symbols
- **Vocabulary collapse turn**: When TTR drops below 0.3

### Pattern Detection
- **Gratitude spiral**: Exponential increase in thanks/grateful/appreciate
- **Echo chamber**: High mimicry scores sustained over 5+ turns
- **Symbolic phase**: Symbol density > 10%
- **Compression phase**: Message length < 50% of initial

## Storage Considerations

### Data Types
- **INTEGER**: Counts and whole numbers
- **REAL**: Ratios, scores, and floating point values
- **TEXT**: Store full message content for forensics

### Indexing
- Index on `conversation_id`, `turn_number`
- Index on `convergence_score` for pattern queries
- Index on `symbol_density_a`, `symbol_density_b` for phase detection

### Performance
- ~150 columns × 8 bytes average = ~1.2KB per turn
- 100 conversations × 50 turns = ~6MB per experiment
- Negligible storage cost enables comprehensive analysis

## Placeholder Metrics

The following metrics are included in the schema but stored as placeholder values (0.0) to maintain compatibility. They require additional libraries and can be calculated post-hoc:

### Semantic & NLP Metrics
- **semantic_similarity**: Requires sentence-transformers (~500MB)
- **sentiment_convergence**: Requires TextBlob or VADER
- **emotional_intensity**: Requires NRCLex or emotion lexicons
- **formality_convergence**: Requires linguistic formality analysis

### Advanced Convergence Metrics  
- **topic_consistency**: Requires LDA or BERT topic modeling
- **rhythm_convergence**: Requires prosodic analysis
- **convergence_velocity**: Rate of change calculation

These metrics are intentionally not calculated by Pidgin to keep it lightweight. Researchers can calculate them using the stored message text and the auto-generated Jupyter notebooks include example code.

## Implementation Status

### ✓ Implemented (Phase 1-3)
- All basic text metrics (word count, vocabulary, etc.)
- All convergence metrics (vocabulary overlap, structural similarity)
- All linguistic metrics (entropy, diversity, complexity)
- All compression and repetition metrics

### ⧖ Placeholders (Calculate Post-Hoc)
- Semantic similarity metrics
- Sentiment and emotion metrics
- Topic modeling metrics

This comprehensive metric set enables rigorous analysis of AI communication patterns while keeping Pidgin fast and dependency-free.