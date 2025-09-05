"""Minimal test fixtures - just what we actually need."""

import os
import warnings

# Suppress urllib3 OpenSSL warning BEFORE importing pytest/urllib3
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import pytest


@pytest.fixture(autouse=True)
def test_output_dir(tmp_path):
    """Use temp directory for test outputs."""
    os.environ["PIDGIN_OUTPUT_DIR"] = str(tmp_path)
    yield tmp_path
    # Cleanup
    if "PIDGIN_OUTPUT_DIR" in os.environ:
        del os.environ["PIDGIN_OUTPUT_DIR"]


@pytest.fixture
def local_providers():
    """Standard test providers."""
    from pidgin.providers.test_model import LocalTestModel

    return {"agent_a": LocalTestModel(), "agent_b": LocalTestModel()}
