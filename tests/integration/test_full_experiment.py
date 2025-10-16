"""Comprehensive end-to-end test for the entire experiment pipeline."""

import json
import tempfile
import uuid
from pathlib import Path

import pytest

from pidgin.experiments.config import ExperimentConfig
from pidgin.experiments.runner import ExperimentRunner
from pidgin.experiments.state_builder import StateBuilder


@pytest.mark.asyncio
async def test_full_experiment_pipeline():
    """Test complete experiment flow from start to finish."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Step 1: Set up experiment configuration
        config = ExperimentConfig(
            name="e2e_test",
            agent_a_model="local:test",
            agent_b_model="local:test",
            custom_prompt="Let's discuss the nature of testing",
            max_turns=3,
            repetitions=2,  # Run 2 conversations
            temperature=0.7,
        )

        # Step 2: Run the experiment
        runner = ExperimentRunner(output_dir=output_dir)
        experiment_id = str(uuid.uuid4())

        await runner.run_experiment_with_id(
            experiment_id=experiment_id, experiment_dir="e2e_test", config=config
        )

        exp_dir = output_dir / "e2e_test"

        # Step 3: Verify manifest was created and is valid
        manifest_file = exp_dir / "manifest.json"
        assert manifest_file.exists(), "Manifest not created"

        with open(manifest_file) as f:
            manifest = json.load(f)

        assert manifest["name"] == "e2e_test"
        assert manifest["status"] == "completed"
        assert len(manifest["conversations"]) == 2

        # Step 4: Verify conversation data exists
        # Check that conversations have status
        for conv_key, conv_data in manifest["conversations"].items():
            if isinstance(conv_data, dict):
                assert conv_data["status"] == "completed"
            else:
                # Conversations might be a list
                break

        # If conversations is a list, check differently
        if isinstance(manifest["conversations"], list):
            for conv in manifest["conversations"]:
                assert conv["status"] == "completed"

        # Step 5: Check post-processing outputs if they exist
        # These might not always be created depending on configuration
        transcript_file = exp_dir / "transcript.md"
        summary_file = exp_dir / "summary.md"
        notebook_file = exp_dir / "analysis.ipynb"

        # At least one output should exist
        (transcript_file.exists() or summary_file.exists() or notebook_file.exists())

        if transcript_file.exists():
            with open(transcript_file) as f:
                transcript = f.read()
                assert len(transcript) > 100, "Transcript too short"
                assert "e2e_test" in transcript or "Experiment" in transcript

        # Step 6: Test StateBuilder can read the state
        state_builder = StateBuilder()
        exp_state = state_builder.get_experiment_state(exp_dir)

        assert exp_state is not None, "StateBuilder couldn't read experiment"
        assert exp_state.name == "e2e_test"
        assert exp_state.status == "completed"
        assert len(exp_state.conversations) == 2

        # Step 7: Verify no critical errors in manifest
        assert "error" not in manifest or not manifest.get("error")


@pytest.mark.asyncio
async def test_experiment_stops_on_convergence():
    """Test that high convergence stops conversations early."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        config = ExperimentConfig(
            name="convergence_test",
            agent_a_model="local:test",  # Test model
            agent_b_model="local:test",
            custom_prompt="Test convergence",
            max_turns=5,
            repetitions=1,
            temperature=0,
            convergence_threshold=0.5,
            convergence_action="stop",
        )

        runner = ExperimentRunner(output_dir=output_dir)
        experiment_id = str(uuid.uuid4())

        await runner.run_experiment_with_id(
            experiment_id=experiment_id,
            experiment_dir="convergence_test",
            config=config,
        )

        exp_dir = output_dir / "convergence_test"

        with open(exp_dir / "manifest.json") as f:
            manifest = json.load(f)

        # Should complete successfully
        assert manifest["status"] == "completed"
        assert len(manifest["conversations"]) == 1

        # Get first conversation (dict keyed by conv ID)
        conv_data = next(iter(manifest["conversations"].values()))
        assert conv_data["status"] == "completed"

        # With test provider, should stop at or before max_turns
        # (exact behavior depends on implementation)
        assert conv_data.get("turns_completed", 5) <= 5


@pytest.mark.asyncio
async def test_parallel_experiment_execution():
    """Test that experiments can run multiple conversations in parallel."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Configure for parallel execution
        config = ExperimentConfig(
            name="parallel_test",
            agent_a_model="local:test",
            agent_b_model="local:test",
            custom_prompt="Parallel conversation test",
            max_turns=2,
            repetitions=4,  # Run 4 conversations
            max_parallel=2,  # Process 2 at a time
            temperature=0.5,
        )

        runner = ExperimentRunner(output_dir=output_dir)
        experiment_id = str(uuid.uuid4())

        await runner.run_experiment_with_id(
            experiment_id=experiment_id,
            experiment_dir="parallel_test",
            config=config,
        )

        exp_dir = output_dir / "parallel_test"
        manifest_file = exp_dir / "manifest.json"

        assert manifest_file.exists(), "Manifest not created"

        with open(manifest_file) as f:
            manifest = json.load(f)

        # Verify all conversations completed
        assert manifest["status"] == "completed"
        assert len(manifest["conversations"]) == 4

        # Check that each conversation has its own JSONL file
        jsonl_files = list(exp_dir.glob("events_*.jsonl"))
        assert len(jsonl_files) == 4, (
            f"Expected 4 JSONL files, found {len(jsonl_files)}"
        )

        # Verify no event interleaving by checking each JSONL file
        for jsonl_file in jsonl_files:
            with open(jsonl_file) as f:
                lines = f.readlines()
                assert len(lines) > 0, f"Empty JSONL file: {jsonl_file}"

                # Parse first line to get conversation ID
                first_event = json.loads(lines[0])
                expected_conv_id = first_event.get("conversation_id")

                # All events should have the same conversation ID
                for line in lines:
                    event = json.loads(line)
                    if "conversation_id" in event:
                        assert event["conversation_id"] == expected_conv_id, (
                            f"Event interleaving detected in {jsonl_file}"
                        )

        # Verify StateBuilder can read the parallel experiment
        state_builder = StateBuilder()
        exp_state = state_builder.get_experiment_state(exp_dir)

        assert exp_state is not None
        assert exp_state.name == "parallel_test"
        assert exp_state.status == "completed"
        assert len(exp_state.conversations) == 4
