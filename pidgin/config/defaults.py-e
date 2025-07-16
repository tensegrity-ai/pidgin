"""Smart defaults for configuration."""

from typing import Optional, Tuple

from .models import get_model_config


def get_smart_convergence_defaults(
    model_a_id: str, model_b_id: str
) -> Tuple[Optional[float], str]:
    """Get smart convergence defaults based on model types.

    For API models (non-local, non-silent), we default to a high
    convergence threshold with stop action to prevent token waste.

    Args:
        model_a_id: First model identifier
        model_b_id: Second model identifier

    Returns:
        Tuple of (convergence_threshold, convergence_action)
        Returns (None, 'notify') if no smart defaults apply
    """
    # Get model configurations
    model_config_a = get_model_config(model_a_id)
    model_config_b = get_model_config(model_b_id)

    # Check if using API models (not local or silent)
    is_api_model_a = model_config_a and model_config_a.provider not in [
        "local",
        "silent",
    ]
    is_api_model_b = model_config_b and model_config_b.provider not in [
        "local",
        "silent",
    ]
    using_api_models = is_api_model_a or is_api_model_b

    # Return smart defaults for API models
    if using_api_models:
        return 0.95, "stop"

    # No smart defaults for local models
    return None, "notify"
