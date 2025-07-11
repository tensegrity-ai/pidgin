# Conversation Architecture

## The Role Transformation Design

Pidgin uses an elegant approach to enable AI-to-AI conversations by leveraging how language models are naturally trained. This document explains the core architectural decision that makes these conversations work smoothly.

## The Challenge

Language models are trained to be helpful assistants responding to user queries. They expect conversations in a specific format:
- **System**: Instructions about their role
- **User**: The person (or entity) they're helping
- **Assistant**: Their own responses

But in AI-to-AI conversations, we have two agents that both need to act as assistants. How do we handle this?

## The Solution: Perspective-Based Role Transformation

Pidgin solves this by transforming the conversation history from each agent's perspective. The same conversation is presented differently to each agent:

### For Agent A:
- Their own messages appear as `role="assistant"`
- Agent B's messages appear as `role="user"`
- System messages are adjusted to say "You are Agent A"

### For Agent B:
- Their own messages appear as `role="assistant"`
- Agent A's messages appear as `role="user"`
- System messages are adjusted to say "You are Agent B"

## Example Transformation

Given this conversation:
```
1. System: "You are Agent A talking to Agent B"
2. Agent A: "Hello, I'm Alice"
3. Agent B: "Hi Alice, I'm Bob"
4. Agent A: "Nice to meet you Bob"
```

**Agent A sees:**
```
1. System: "You are Agent A talking to Agent B"
2. Assistant: "Hello, I'm Alice"         [their own message]
3. User: "Hi Alice, I'm Bob"            [other agent as user]
4. Assistant: "Nice to meet you Bob"     [their own message]
```

**Agent B sees:**
```
1. System: "You are Agent B talking to Agent A"  [adjusted]
2. User: "Hello, I'm Alice"              [other agent as user]
3. Assistant: "Hi Alice, I'm Bob"        [their own message]
4. User: "Nice to meet you Bob"          [other agent as user]
```

## Why This Works

This approach is powerful because:

1. **Natural for Models**: Each agent operates in their trained paradigm - responding as an assistant to user queries
2. **Symmetric**: Both agents get equal treatment, neither is privileged
3. **Clean**: No need for special prompting or role-play instructions
4. **Flexible**: Works with any model that follows the standard chat format

## The Awareness Dimension

The `--awareness` flag adds another layer to this design:

- **Basic** (default): Agents see each other as users, no mention of AI
- **Intermediate**: System prompt mentions they're talking to another AI
- **High**: Full transparency about the experimental context

This allows researchers to study how agent behavior changes based on their understanding of the conversation context, while the underlying role transformation remains constant.

## Implementation

The role transformation happens in `DirectRouter._build_agent_history()` method, which is used by the `EventWrapperProvider` to prepare messages for each agent. This clean separation means the transformation logic is centralized and consistent.

## Future Possibilities

While currently only `DirectRouter` implements simple A↔B alternation, the `Router` protocol allows for future extensions:
- Multi-agent conversations (more than 2 agents)
- Dynamic routing based on content
- Different conversation topologies
- Asymmetric agent relationships

The core insight - presenting the conversation from each agent's natural perspective - would remain valuable in these extended scenarios.

# Data Flow Diagram

```
┌─────────────┐
│   Message   │
│  Generated  │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│   EventBus  │────▶│ JSONL File   │ (Permanent storage)
└──────┬──────┘     └──────────────┘
       │
       ▼
┌──────────────────────┐
│ Conversation.messages│ (In-memory, currently unbounded)
└──────┬───────────────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌─────────────┐   ┌──────────────┐
│   Router    │   │ Convergence  │
│ Transform   │   │  Calculator  │
└──────┬──────┘   └──────────────┘
       │               (needs last 10)
       ▼
┌─────────────┐
│  Provider   │
│  Truncate   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     API     │
└─────────────┘
```