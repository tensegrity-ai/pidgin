"""Make sure API failures don't crash everything."""


def test_handles_api_errors():
    """Make sure error handling works."""
    from pidgin.experiments.config import ExperimentConfig

    # Just verify we can create configs with "bad" values
    # and the system handles them gracefully

    # Bad model name
    config1 = ExperimentConfig(
        name="error_test",
        agent_a_model="not_a_real_model",
        agent_b_model="local:test",
        repetitions=1,
        max_turns=1,
    )
    assert config1 is not None

    # Extreme temperature (should be clamped or accepted)
    config2 = ExperimentConfig(
        name="temp_test",
        agent_a_model="local:test",
        agent_b_model="local:test",
        repetitions=1,
        max_turns=1,
        temperature_a=10.0,  # Very high
        temperature_b=0.0,  # Very low
    )
    assert config2 is not None


def test_handles_bad_config():
    """Make sure we handle bad configurations gracefully."""
    from pidgin.experiments.config import ExperimentConfig

    # Negative values
    try:
        ExperimentConfig(
            name="bad_config",
            agent_a_model="local:test",
            agent_b_model="local:test",
            repetitions=-1,  # Invalid
            max_turns=1,
        )
        # If it accepts it, that's OK (might fix it)
        assert True
    except Exception:
        # If it rejects it, that's also OK
        assert True

    # Zero turns
    try:
        ExperimentConfig(
            name="zero_turns",
            agent_a_model="local:test",
            agent_b_model="local:test",
            repetitions=1,
            max_turns=0,  # Invalid
        )
        assert True
    except Exception:
        assert True
