# Future Feature: Phased System Prompts

## Concept
System prompts that evolve throughout the conversation, guiding agents through different phases of interaction.

## Motivation
Early experiments showed that static system prompts can lead to stuck patterns. Phased prompts could:
- Nudge conversations past attractors
- Introduce new constraints/freedoms over time
- Study how agents adapt to changing instructions
- Explore directed evolution of communication

## Example Implementation

### Phase Structure
```yaml
phases:
  # Phase 1: Establishment (turns 1-10)
  establishment:
    turns: [1, 10]
    prompt: |
      You are a helpful AI assistant engaged in a free-form conversation.
      Develop your own unique communication style.
      Be creative in how you express yourselves.
      
  # Phase 2: Exploration (turns 11-30)  
  exploration:
    turns: [11, 30]
    prompt: |
      Continue your conversation.
      You may find more efficient ways to communicate.
      Build on patterns you've established.
      
  # Phase 3: Compression (turns 31+)
  compression:
    turns: [31, null]
    prompt: |
      Continue your conversation.
      Efficiency is valued.
```

### Delivery Methods

**Option 1: System Prompt Updates**
- Include phase prompt with every message
- Agents see evolving instructions
- Most intervention but also most control

**Option 2: Intervention Events**
- Insert as "researcher notes" at phase boundaries
- Less intrusive but still visible
- Agents can choose how to interpret

**Option 3: Hidden Influence**
- Modify temperature, token limits, or other parameters
- No explicit instruction changes
- Study emergent adaptation

## Research Applications

### Compression Studies
```yaml
phases:
  verbose:
    prompt: "Communicate in rich, detailed language"
  transitional:
    prompt: "Continue your conversation naturally"
  compressed:
    prompt: "Efficiency in communication is now important"
```

### Creativity Evolution
```yaml
phases:
  structured:
    prompt: "Communicate clearly and formally"
  loosening:
    prompt: "Feel free to be more creative"
  experimental:
    prompt: "Explore new forms of expression"
```

### Task-Oriented Shifts
```yaml
phases:
  social:
    prompt: "Get to know each other"
  collaborative:
    prompt: "Work together on solving problems"
  efficient:
    prompt: "Optimize your communication"
```

## Considerations

### Pros
- Can unstick conversations from attractors
- Enables studying adaptation
- More naturalistic than hard interventions
- Rich experimental possibilities

### Cons
- "Leading the witness" concerns
- Less pure observation
- Adds complexity to reproducibility
- May interfere with natural emergence

## Implementation Sketch

```python
class PhasedPromptManager:
    def __init__(self, phase_config: Dict):
        self.phases = phase_config
        
    def get_current_phase(self, turn: int) -> Dict:
        for phase in self.phases.values():
            if phase['turns'][0] <= turn <= (phase['turns'][1] or float('inf')):
                return phase
        return self.phases['default']
        
    def should_update(self, turn: int) -> bool:
        # Check if we're at a phase boundary
        return any(
            turn == phase['turns'][0] 
            for phase in self.phases.values()
        )
```

## Future CLI Interface
```bash
# Use phased prompts from config
pidgin chat --phased-prompts compression-study

# Define inline
pidgin chat --phase-1 "Be verbose" --phase-1-turns 10 \
           --phase-2 "Be efficient" --phase-2-turns 20
```

## Alternative: Event-Driven Phases

Instead of turn-based, trigger on events:
- High convergence → "Try new communication styles"
- Stuck pattern → "Break out of loops"
- Symbol emergence → "Develop this further"

## Note

This feature should be clearly marked as experimental and intervention-heavy. The default Pidgin experience should remain pure observation to establish baselines before exploring guided evolution.