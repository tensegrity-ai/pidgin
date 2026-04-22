"""Smoke test that core imports and basic object construction work."""

from pidgin.experiments.config import ExperimentConfig
from pidgin.providers.test_model import LocalTestModel


def test_core_imports_and_construction():
    """Core modules import and basic objects construct without error."""
    from pidgin.core.conductor import Conductor
    from pidgin.experiments.runner import ExperimentRunner

    assert Conductor is not None
    assert ExperimentRunner is not None

    config = ExperimentConfig(
        name="test",
        agent_a_model="local:test",
        agent_b_model="local:test",
        repetitions=1,
        max_turns=1,
    )
    assert config.name == "test"

    model = LocalTestModel()
    assert model is not None
