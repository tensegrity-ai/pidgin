```
CURRENT APPROACH (Dashboard Does Everything)
════════════════════════════════════════════

┌─────────────────┐    ┌─────────────────────────────────────┐    ┌──────────────┐
│   Experiment    │    │           Dashboard                 │    │   Terminal   │
│     Runner      │    │                                     │    │    Display   │
│                 │    │  ┌─────────────────────────────────┐│    │              │
│  Writes raw     │───▶│  │     EVERY 2 SECONDS:            ││───▶│  Sparklines  │
│  turn data      │    │  │                                 ││    │  Metrics     │
│  to SQLite      │    │  │  SELECT tm.vocabulary_overlap,  ││    │  Progress    │
│                 │    │  │         tm.convergence_score,   ││    │              │
│                 │    │  │         AVG(mm.type_token_ratio)││    │              │
│                 │    │  │  FROM turn_metrics tm           ││    │              │
│                 │    │  │  LEFT JOIN message_metrics mm   ││    │              │
│                 │    │  │  WHERE conversation_id IN (...)  ││    │              │
│                 │    │  │  GROUP BY turn_number           ││    │              │
│                 │    │  │  ORDER BY turn_number DESC      ││    │              │
│                 │    │  │                                 ││    │              │
│                 │    │  │  FOR EACH CONVERSATION          ││    │              │
│                 │    │  │  FOR EACH METRIC                ││    │              │
│                 │    │  │  BUILD SPARKLINES               ││    │              │
│                 │    │  │  CALCULATE AGGREGATES           ││    │              │
│                 │    │  └─────────────────────────────────┘│    │              │
└─────────────────┘    └─────────────────────────────────────┘    └──────────────┘

Problems:
• Complex JOINs across 3+ tables every 2 seconds
• Recalculates sparklines from scratch repeatedly  
• Scans thousands of rows for simple aggregates
• Dashboard logic mixed with data processing
• SQLite doing heavy lifting at display time


PROPOSED APPROACH (Pre-Calculate During Experiment)
══════════════════════════════════════════════════

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐
│   Experiment    │    │   Aggregate     │    │    Dashboard    │    │   Terminal   │
│     Runner      │    │    Builder      │    │                 │    │    Display   │
│                 │    │                 │    │                 │    │              │
│  Conversation   │───▶│  ON EACH TURN:  │───▶│  Simple reads:  │───▶│  Sparklines  │
│  completes      │    │                 │    │                 │    │  Metrics     │
│                 │    │  UPDATE         │    │  SELECT *       │    │  Progress    │
│  Writes raw     │───▶│  experiment_    │    │  FROM           │    │              │
│  turn data      │    │  metrics SET    │    │  experiment_    │    │              │
│                 │    │  avg_conv=X,    │    │  metrics        │    │              │
│                 │    │  high_conv=Y    │    │                 │    │              │
│                 │    │                 │    │  SELECT *       │    │              │
│                 │    │  INSERT INTO    │    │  FROM           │    │              │
│                 │    │  sparklines     │    │  sparklines     │    │              │
│                 │    │  VALUES(...)    │    │                 │    │              │
│                 │    │                 │    │  SELECT *       │    │              │
│                 │    │  Pattern        │    │  FROM           │    │              │
│                 │    │  detection      │    │  current_conv   │    │              │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └──────────────┘

Benefits:
• Dashboard queries are simple SELECT statements
• Sparklines pre-built, just read JSON arrays
• No JOINs at display time
• Separation of concerns (MVC pattern)
• SQLite excels at simple reads


DATA FLOW COMPARISON
═══════════════════

BEFORE (Query-Time Aggregation):
───────────────────────────────

Raw Data → Dashboard Query → Heavy Processing → Display
   │             │                    │
   │             │              ┌─────▼─────┐
   │             │              │ Complex   │
   │             │              │ JOINs &   │
   │             │              │ GROUP BY  │
   │             │              │ every 2s  │
   │             │              └───────────┘
   │             │
   ▼             ▼
┌─────────────────────────────┐
│     Raw Tables              │
│  • turns (5000+ rows)       │
│  • message_metrics          │  
│  • turn_metrics            │
│  • conversations           │
└─────────────────────────────┘


AFTER (Write-Time Aggregation):
──────────────────────────────

Raw Data → Incremental Updates → Simple Reads → Display
   │              │                    │
   │              ▼                    │
   │    ┌─────────────────┐           │
   │    │ Aggregate       │           │
   │    │ Builder         │           │
   │    │ (runs once per  │           │
   │    │  conversation)  │           │
   │    └─────────────────┘           │
   │                                  │
   ▼                                  ▼
┌─────────────────┐            ┌─────────────────┐
│  Raw Tables     │            │ Aggregate Tables│
│ • turns         │            │ • experiment_   │
│ • messages      │            │   metrics       │
│ • conversations │            │ • sparklines    │
│                 │            │ • current_conv  │
└─────────────────┘            └─────────────────┘


PERFORMANCE COMPARISON
═════════════════════

Current Approach:
┌──────────────────────────────────────────────────────────┐
│ Every 2 seconds:                                         │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ For each conversation (1-10):                        │ │
│ │   ┌────────────────────────────────────────────────┐ │ │
│ │   │ For each metric (convergence, TTR, overlap...): │ │ │
│ │   │   • JOIN 3 tables                             │ │ │
│ │   │   • GROUP BY turn_number                      │ │ │
│ │   │   • Calculate sparkline points               │ │ │
│ │   │   • Aggregate across conversations           │ │ │
│ │   └────────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────┘ │
│ Total: ~50 complex queries every 2 seconds              │
└──────────────────────────────────────────────────────────┘

Proposed Approach:
┌──────────────────────────────────────────────────────────┐
│ Per conversation completion (~every 30-60 seconds):     │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ • Update experiment_metrics (1 UPDATE)              │ │
│ │ • Insert sparkline points (3-5 INSERTs)            │ │
│ │ • Update current conversation (1 UPDATE)           │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ Every 2 seconds (dashboard):                            │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ • SELECT * FROM experiment_metrics                   │ │
│ │ • SELECT * FROM sparklines                          │ │
│ │ • SELECT * FROM current_conv                        │ │
│ └──────────────────────────────────────────────────────┘ │
│ Total: 3 simple SELECTs every 2 seconds                │
└──────────────────────────────────────────────────────────┘

Result: ~95% reduction in dashboard query complexity
```