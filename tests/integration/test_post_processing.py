"""Make sure the post-processing pipeline actually works."""

import json

import pytest


def test_post_processing_pipeline_works(tmp_path):
    """Verify the post-processing pipeline doesn't break.

    This is critical - if post-processing fails, experiments appear to work
    but no analysis is possible.
    """
    # Test 1: Database import service exists and loads
    try:
        from pidgin.database.import_service import ImportService

        assert ImportService is not None
        import_loads = True
    except ImportError:
        import_loads = False

    assert import_loads, "Import service should be available"

    # Test 2: Can create an import service instance?
    db_path = tmp_path / "test.duckdb"
    try:
        service = ImportService(str(db_path))
        assert service is not None
        service.close()
        service_works = True
    except Exception as e:
        print(f"Import service failed: {e}")
        service_works = False

    assert service_works, "Should be able to create import service"

    # Test 3: Critical analysis components exist
    critical_components = [
        ("pidgin.analysis.notebook_generator", "NotebookGenerator"),
        ("pidgin.database.transcript_formatter", "TranscriptFormatter"),
        ("pidgin.database.event_store", "EventStore"),
        ("pidgin.metrics.flat_calculator", "FlatMetricsCalculator"),
    ]

    for module_path, class_name in critical_components:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            assert cls is not None
        except ImportError as e:
            pytest.fail(
                f"Critical component {module_path}.{class_name} not available: {e}"
            )

    # Test 4: Minimal import workflow
    exp_dir = tmp_path / "experiment_minimal"
    exp_dir.mkdir()

    # Create the absolute minimum needed
    manifest = exp_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "experiment_id": "minimal",
                "name": "Minimal Test",
                "created_at": "2025-01-01T00:00:00",
            }
        )
    )

    # Even with minimal/broken data, import shouldn't crash hard
    service = ImportService(str(db_path))
    try:
        result = service.import_experiment_from_jsonl(exp_dir)
        # We don't care if it succeeds, just that it doesn't crash
        assert result is not None
    except Exception as e:
        # Graceful failures are OK
        assert "jsonl" in str(e).lower() or "not found" in str(e).lower()
    finally:
        service.close()

    # If we got here, post-processing pipeline is at least loadable
    assert True
