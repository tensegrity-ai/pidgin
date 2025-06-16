# Project Status

Honest assessment of an experimental research tool.

## ✅ What Actually Works

- **Conversation recording**: Runs and logs AI-to-AI conversations
- **Event-driven architecture**: Complete audit trail in events.jsonl
- **Streaming output**: Real-time response display
- **Pause/resume**: Ctrl+C interrupt handling
- **Multi-provider support**: Anthropic, OpenAI, Google, xAI
- **Clean abstractions**: Providers, event bus, output management
- **2-agent conversations**: Current implementation focus

## 🚧 Experimental Features (Need Validation)

- **Convergence metrics**: 
  - Measures vocabulary overlap and compression
  - Interesting patterns observed
  - Not scientifically validated
  - Needs statistical testing

- **Pattern observations**:
  - Gratitude spirals documented
  - Compression attempts noted
  - Could be real or artifacts
  - Requires controlled experiments

## ❌ Critical Missing Pieces (Needed for Research)

- **Batch experiments**: Single conversation limit (need hundreds for validity)
- **Statistical analysis**: No tools to test if patterns are significant
- **Control conditions**: No shuffled/baseline comparisons
- **Reproducibility**: Chaotic system - tiny changes → different results
- **N-agent support**: Architecture ready but not implemented
- **Hypothesis testing**: No framework for systematic experiments

## 📊 Current Understanding

### What we've observed:
- Strange patterns DO appear in AI conversations
- Gratitude spirals, compression, behavioral signatures
- Extreme sensitivity to initial conditions
- Different model pairs show different dynamics

### What we don't know:
- Are these patterns real or artifacts?
- Do they emerge from training or interaction?
- Can they be reproduced reliably?
- Do they have any practical significance?

### Architecture choices:
- Event-driven design enables future n-agent support
- Complete logging allows retrospective analysis
- Clean provider abstraction supports multiple models

## 🔬 What Would Make This Scientific?

To do actual research, we'd need:

1. **Batch runner**: Run 1000s of conversations with systematic variations
2. **Control conditions**: Shuffled responses, human-written responses
3. **Statistical analysis**: Pattern frequency, significance testing
4. **Hypothesis testing**: Pre-registered experiments with clear predictions
5. **Reproducibility**: Version locking, seed management, exact replay

## 🎯 Next Steps for Valid Research

1. **Build batch runner**: Critical for statistical validity
2. **Design control experiments**: Test against random baselines
3. **Statistical framework**: Proper hypothesis testing
4. **Reproducibility tools**: Seed management, version locking
5. **Collaborate with skeptics**: Need rigorous validation

## 🔬 Research Questions

What we're trying to determine:
- Are the observed patterns reproducible?
- Do they emerge from interaction or just reflect training?
- Can we distinguish real phenomena from artifacts?
- Is this worth studying further?

We need rigorous experiments to answer these questions.

## 🤝 How to Help

We need collaborators to:

1. **Build batch infrastructure**: Run hundreds of controlled conversations
2. **Design experiments**: Test specific hypotheses
3. **Statistical analysis**: Validate or debunk patterns
4. **Document null results**: "Found nothing" is valuable data
5. **Challenge observations**: Skeptical review essential

**Core message**: We saw weird stuff in AI conversations. Built a tool to capture it. Still figuring out if it's real. Want to help?