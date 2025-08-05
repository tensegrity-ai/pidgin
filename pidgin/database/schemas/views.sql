-- Real-time experiment dashboard
CREATE OR REPLACE VIEW experiment_dashboard AS
SELECT
    e.experiment_id,
    e.name,
    e.status,
    e.created_at,
    e.total_conversations as total_convs,
    e.completed_conversations as completed,
    e.failed_conversations as failed,

    -- Progress percentage
    CASE
        WHEN e.total_conversations > 0
        THEN e.completed_conversations * 100.0 / e.total_conversations
        ELSE 0
    END as progress_pct,

    -- Aggregate metrics from conversations
    COUNT(DISTINCT c.conversation_id) as actual_convs,
    AVG(c.final_convergence_score) as avg_convergence,
    MEDIAN(c.final_convergence_score) as median_convergence,
    STDDEV(c.final_convergence_score) as stddev_convergence,

    -- Duration stats
    AVG(c.duration_ms) / 1000.0 as avg_duration_sec,
    SUM(c.total_turns) as total_turns,

    -- Token usage
    COALESCE(SUM(tu.total_tokens), 0) as total_tokens,
    COALESCE(SUM(tu.total_cost), 0) / 100.0 as total_cost_usd

FROM experiments e
LEFT JOIN conversations c ON e.experiment_id = c.experiment_id
LEFT JOIN (
    SELECT conversation_id,
           SUM(total_tokens) as total_tokens,
           SUM(total_cost) as total_cost
    FROM token_usage
    GROUP BY conversation_id
) tu ON c.conversation_id = tu.conversation_id
GROUP BY e.experiment_id, e.name, e.status, e.created_at,
         e.total_conversations, e.completed_conversations,
         e.failed_conversations;

-- Convergence trends view
CREATE OR REPLACE VIEW convergence_trends AS
SELECT
    tm.conversation_id,
    tm.turn_number,
    tm.convergence_score,

    -- Rolling averages
    AVG(tm.convergence_score) OVER (
        PARTITION BY tm.conversation_id
        ORDER BY tm.turn_number
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) as rolling_avg_5,

    AVG(tm.convergence_score) OVER (
        PARTITION BY tm.conversation_id
        ORDER BY tm.turn_number
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as rolling_avg_10,

    -- Rate of change
    tm.convergence_score - LAG(tm.convergence_score, 1) OVER (
        PARTITION BY tm.conversation_id ORDER BY tm.turn_number
    ) as convergence_delta,

    -- Message length trends
    tm.message_a_length as msg_length_a,
    tm.message_b_length as msg_length_b

FROM turn_metrics tm;

-- Simple vocabulary analysis view
CREATE OR REPLACE VIEW vocabulary_analysis AS
SELECT
    conversation_id,
    turn_number,
    message_a_unique_words as vocab_size_a,
    message_b_unique_words as vocab_size_b,
    message_a_unique_words + message_b_unique_words as total_vocab_size
FROM turn_metrics;