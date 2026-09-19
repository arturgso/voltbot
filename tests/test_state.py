from pathlib import Path

from voltbot.state import (
    already_processed,
    is_intro_sent,
    load_state,
    mark_intro_sent,
    mark_processed,
)


def test_intro_state_flow(tmp_path: Path):
    state_file = tmp_path / "state.json"

    # Initially false
    assert not is_intro_sent("11934720814", path=state_file)
    assert not is_intro_sent("5511934720814", path=state_file)

    # Mark with 11 digits
    mark_intro_sent("11934720814", path=state_file)

    # Both forms should now return true because of normalization
    assert is_intro_sent("11934720814", path=state_file)
    assert is_intro_sent("5511934720814", path=state_file)

    # State file content check
    raw = load_state(state_file)
    assert "intro:5511934720814" in raw
    assert raw["intro:5511934720814"]["sent"] is True
    assert "sent_at" in raw["intro:5511934720814"]


def test_intro_state_does_not_interfere_with_processed_bills(tmp_path: Path):
    state_file = tmp_path / "state.json"

    mark_processed("0200420281", "conta.pdf", path=state_file)
    mark_intro_sent("5511998550758", path=state_file)

    assert already_processed("0200420281", "conta.pdf", path=state_file)
    assert not already_processed("0200420281", "outra.pdf", path=state_file)
    assert is_intro_sent("5511998550758", path=state_file)
    assert not is_intro_sent("5511888888888", path=state_file)
