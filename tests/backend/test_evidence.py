from scripts.generate_demo_evidence import preserve_timestamps_if_unchanged


def test_preserve_timestamps_when_evidence_semantics_are_unchanged() -> None:
    existing = {
        "generated_at": "old-root",
        "metric": 1,
        "nested": {"generated_at": "old-nested", "passed": True},
    }
    current = {
        "generated_at": "new-root",
        "metric": 1,
        "nested": {"generated_at": "new-nested", "passed": True},
    }

    result = preserve_timestamps_if_unchanged(existing, current)

    assert result["generated_at"] == "old-root"
    assert result["nested"]["generated_at"] == "old-nested"


def test_refreshes_timestamps_when_evidence_semantics_change() -> None:
    existing = {"generated_at": "old", "metric": 1}
    current = {"generated_at": "new", "metric": 2}

    result = preserve_timestamps_if_unchanged(existing, current)

    assert result["generated_at"] == "new"
