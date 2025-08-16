"""Quick sanity check that metrics still work."""

from pidgin.metrics.flat_calculator import FlatMetricsCalculator


def test_metrics_are_sane():
    """Quick sanity check that metrics still work."""

    calc = FlatMetricsCalculator()

    # Calculate metrics for a simple turn
    metrics = calc.calculate_turn_metrics(
        turn_number=1, agent_a_message="Hello world", agent_b_message="Hello there"
    )

    # Just check they exist and are reasonable
    assert "overall_convergence" in metrics
    assert 0 <= metrics["overall_convergence"] <= 1

    assert "a_message_length" in metrics
    assert metrics["a_message_length"] == len("Hello world")

    assert "b_message_length" in metrics
    assert metrics["b_message_length"] == len("Hello there")

    assert "vocabulary_overlap" in metrics
    assert 0 <= metrics["vocabulary_overlap"] <= 1


def test_convergence_increases_with_similarity():
    """Convergence should be higher for similar messages."""

    calc = FlatMetricsCalculator()

    # Different messages
    metrics1 = calc.calculate_turn_metrics(
        turn_number=1, agent_a_message="I like cats", agent_b_message="I hate dogs"
    )

    # Similar messages
    metrics2 = calc.calculate_turn_metrics(
        turn_number=1, agent_a_message="I like cats", agent_b_message="I love cats"
    )

    # Similar should have higher convergence
    assert metrics2["overall_convergence"] > metrics1["overall_convergence"]
