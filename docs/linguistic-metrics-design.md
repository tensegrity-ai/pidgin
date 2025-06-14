# Linguistic Metrics for Conversation Analysis

## Overview

Track linguistic evolution in real-time to identify compression, convergence, and emergent communication patterns. These metrics complement structural pattern detection by measuring the actual language changes.

## Core Metrics

### 1. Compression Metrics

#### Gzip Compression Ratio
```python
def calculate_compression_ratio(text: str) -> float:
    """
    Lower ratio = more repetitive/compressible text
    Tracks when language becomes more formulaic
    """
    original_size = len(text.encode('utf-8'))
    compressed_size = len(gzip.compress(text.encode('utf-8')))
    return compressed_size / original_size
```

**What it reveals**: 
- Falling ratios indicate increasing repetition
- Sudden drops may signal attractor formation
- Compare ratios between agents to see who's leading compression

#### Message Length Trajectory
```python
def track_message_lengths(messages: List[Message]) -> Dict[str, List[int]]:
    """Track how message lengths evolve over time"""
    return {
        'lengths': [len(m.content) for m in messages],
        'trend': calculate_trend(lengths),  # increasing/decreasing/stable
        'variance': statistics.stdev(lengths)
    }
```

### 2. Vocabulary Metrics

#### Lexical Diversity (Type-Token Ratio)
```python
def calculate_lexical_diversity(text: str) -> float:
    """
    Unique words / Total words
    Decreasing diversity indicates vocabulary compression
    """
    words = text.lower().split()
    return len(set(words)) / len(words) if words else 0
```

#### Vocabulary Overlap
```python
def calculate_vocabulary_overlap(messages_a: List[str], messages_b: List[str]) -> float:
    """
    How much are agents sharing vocabulary?
    High overlap suggests convergence
    """
    vocab_a = set(word for m in messages_a for word in m.lower().split())
    vocab_b = set(word for m in messages_b for word in m.lower().split())
    
    intersection = vocab_a & vocab_b
    union = vocab_a | vocab_b
    
    return len(intersection) / len(union) if union else 0
```

### 3. Emergent Symbol Tracking

#### Symbol Density
```python
def track_symbol_emergence(text: str) -> Dict[str, Any]:
    """Track non-alphabetic symbol usage"""
    symbols = {
        'emoji': count_emojis(text),
        'arrows': len(re.findall(r'[→←↔⇒⇔➜▶◀]', text)),
        'math': len(re.findall(r'[≈≡∈∀∃±∞∑∏∫]', text)),
        'punctuation_art': len(re.findall(r'[。◕‿◕。|⌐■-■|╯°□°）╯]', text)),
        'custom': detect_repeated_symbol_patterns(text)
    }
    
    return {
        'counts': symbols,
        'density': sum(symbols.values()) / len(text) if text else 0,
        'diversity': len([s for s in symbols.values() if s > 0])
    }
```

#### Novel Pattern Detection
```python
def detect_emergent_patterns(conversation: List[Message]) -> List[Pattern]:
    """
    Find recurring non-standard patterns that might be
    emerging as new communication symbols
    """
    # Look for repeated unusual character sequences
    # that appear in both agents' messages
    patterns = []
    
    # Extract all 2-5 character non-word sequences
    for message in conversation:
        unusual_sequences = re.findall(r'[^\w\s]{2,5}', message.content)
        # Track if both agents start using them...
```

### 4. Convergence Indicators

#### Syntactic Alignment
```python
def measure_syntactic_alignment(messages_a: List[str], messages_b: List[str]) -> float:
    """
    How similar are sentence structures?
    Uses POS tagging patterns
    """
    # Compare part-of-speech tag sequences
    # High alignment suggests syntactic convergence
```

#### Echo Patterns
```python
def detect_echo_patterns(messages: List[Message]) -> Dict[str, Any]:
    """
    Track when agents start echoing each other's phrases
    """
    echo_instances = []
    
    for i in range(1, len(messages)):
        current = messages[i].content
        previous = messages[i-1].content
        
        # Find shared phrases (3+ words)
        shared_phrases = find_shared_phrases(current, previous)
        if shared_phrases:
            echo_instances.append({
                'turn': i,
                'phrases': shared_phrases,
                'echo_ratio': len(shared_phrases) / len(current.split())
            })
    
    return {
        'instances': echo_instances,
        'frequency': len(echo_instances) / len(messages),
        'increasing': is_trend_increasing(echo_instances)
    }
```

## Real-Time Dashboard Integration

### Live Metrics Panel
```
┌─ Language Evolution ──────────────────────────────────────┐
│ Compression:  0.72 → 0.68 → 0.61 ↓ (increasing repetition)│
│ Vocabulary:   2,341 unique words (↓ 12% from start)       │
│ Lexical Div:  0.42 (healthy) → 0.31 (compressed)          │
│ Symbol Use:   ▁▃▅▇█ (15x 🤔) (8x →) (emerging: ≈≈≈)       │
└────────────────────────────────────────────────────────────┘
```

### Alert Conditions
- Compression ratio drops below 0.5 (high repetition)
- Lexical diversity falls below 0.2 (vocabulary collapse)
- Symbol density exceeds 10% (potential new language)
- Echo patterns exceed 30% (strong convergence)

## Implementation Priorities

### Phase 1: Basic Metrics
- Message length tracking
- Simple compression ratio
- Basic vocabulary counts

### Phase 2: Convergence Detection  
- Lexical diversity
- Vocabulary overlap
- Echo pattern detection

### Phase 3: Symbol Emergence
- Emoji/symbol density
- Novel pattern detection
- Cross-agent symbol adoption

## Research Applications

### Compression Studies
"At what turn does vocabulary begin to compress? Is it gradual or sudden?"

### Symbol Evolution
"Do certain model pairs develop richer symbolic languages?"

### Convergence Dynamics
"Which linguistic features converge first - vocabulary, syntax, or style?"

### Intervention Effects
"How does human intervention affect compression trajectories?"

## Storage Schema

```python
@dataclass
class LinguisticMetrics:
    turn: int
    compression_ratio: float
    message_length: int
    lexical_diversity: float
    vocabulary_size: int
    symbol_density: float
    echo_frequency: float
    
    # For time-series analysis
    timestamp: datetime
    agent_id: str
```

## Key Insights

These metrics help answer:
1. **When** does compression begin? (Not just if)
2. **What kind** of compression? (Vocabulary, structure, or symbols)
3. **Who leads** compression? (Which agent innovates)
4. **What emerges**? (New symbols, shortened forms, unique patterns)