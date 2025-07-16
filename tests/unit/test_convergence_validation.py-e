"""Test convergence weight validation."""

import pytest

from pidgin.analysis.convergence import ConvergenceCalculator


class TestConvergenceValidation:
    """Test weight validation in ConvergenceCalculator."""

    def test_default_weights_valid(self):
        """Test that default weights are valid."""
        # Should not raise
        calc = ConvergenceCalculator()
        assert sum(calc.weights.values()) == 1.0

    def test_custom_valid_weights(self):
        """Test with valid custom weights."""
        weights = {
            "content": 0.5,
            "length": 0.1,
            "sentences": 0.2,
            "structure": 0.1,
            "punctuation": 0.1,
        }
        calc = ConvergenceCalculator(weights=weights)
        assert calc.weights == weights

    def test_weights_not_sum_to_one(self):
        """Test that weights must sum to 1.0."""
        weights = {
            "content": 0.5,
            "length": 0.2,
            "sentences": 0.2,
            "structure": 0.2,
            "punctuation": 0.2,  # Sum is 1.3
        }
        with pytest.raises(ValueError, match="Weights must sum to 1.0, got 1.300"):
            ConvergenceCalculator(weights=weights)

    def test_missing_weight_key(self):
        """Test that all required keys must be present."""
        weights = {
            "content": 0.5,
            "length": 0.5,
            # Missing sentences, structure, punctuation
        }
        with pytest.raises(ValueError, match="missing keys"):
            ConvergenceCalculator(weights=weights)

    def test_extra_weight_key(self):
        """Test that no extra keys are allowed."""
        weights = {
            "content": 0.3,
            "length": 0.1,
            "sentences": 0.2,
            "structure": 0.1,
            "punctuation": 0.1,
            "extra_key": 0.2,  # Extra key
        }
        with pytest.raises(ValueError, match="extra keys"):
            ConvergenceCalculator(weights=weights)

    def test_negative_weight(self):
        """Test that weights must be non-negative."""
        weights = {
            "content": 0.5,
            "length": -0.1,  # Negative weight
            "sentences": 0.3,
            "structure": 0.2,
            "punctuation": 0.1,
        }
        with pytest.raises(ValueError, match="must be a non-negative number"):
            ConvergenceCalculator(weights=weights)

    def test_non_numeric_weight(self):
        """Test that weights must be numeric."""
        weights = {
            "content": "high",  # Non-numeric
            "length": 0.2,
            "sentences": 0.2,
            "structure": 0.2,
            "punctuation": 0.2,
        }
        with pytest.raises(ValueError, match="must be a non-negative number"):
            ConvergenceCalculator(weights=weights)

    def test_weights_sum_within_tolerance(self):
        """Test that small floating point errors are acceptable."""
        # This should work due to tolerance
        weights = {
            "content": 0.4,
            "length": 0.15,
            "sentences": 0.2,
            "structure": 0.15,
            "punctuation": 0.0999999,  # Close to 0.1
        }
        # Should not raise - sum is 0.9999999 which is within tolerance
        calc = ConvergenceCalculator(weights=weights)
        assert calc.weights == weights
