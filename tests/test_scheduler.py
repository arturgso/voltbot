import threading
from datetime import date

from voltbot.db import Database
from voltbot.scheduler import WEEK_SECONDS, next_run_at, claim_due_run, scheduler_loop


def test_schedule_survives_restart_and_history_cleanup(tmp_path):
    path = tmp_path / 'schedule.db'
    db = Database(path)
    assert next_run_at(db, 100) == 100 + WEEK_SECONDS
    manual = db.create_run('today', {}, True)
    db.delete_run(manual)
    db.close()
    db = Database(path)
    assert next_run_at(db, 200) == 100 + WEEK_SECONDS
    assert claim_due_run(db, 100 + WEEK_SECONDS - 1) is None
    claimed = claim_due_run(db, 100 + WEEK_SECONDS)
    assert claimed is not None
    run_id, params = claimed
    assert params['scheduled'] is True
    assert params['dry_run'] is False
    assert (date.fromisoformat(params['end']) - date.fromisoformat(params['start'])).days == 8
    assert db.get_run(run_id)['kind'] == 'week'
    assert claim_due_run(db, 100 + WEEK_SECONDS) is None
    assert next_run_at(db, 0) == 100 + 2 * WEEK_SECONDS
    db.close()


def test_missed_slots_create_only_one_run(tmp_path):
    db = Database(tmp_path / 'schedule.db')
    next_run_at(db, 0)
    assert claim_due_run(db, 5 * WEEK_SECONDS + 10) is not None
    assert claim_due_run(db, 5 * WEEK_SECONDS + 10) is None
    assert next_run_at(db, 0) == 6 * WEEK_SECONDS
    assert len(db.list_runs()) == 1
    db.close()


def test_stopped_scheduler_never_runs(tmp_path):
    stop = threading.Event()
    stop.set()
    scheduler_loop(str(tmp_path / 'schedule.db'), stop, lambda *args: (_ for _ in ()).throw(AssertionError()))
    assert not (tmp_path / 'schedule.db').exists()


def test_scheduler_waits_for_manual_execution(tmp_path):
    from voltbot.scheduler import RUN_LOCK
    path = tmp_path / 'schedule.db'
    db = Database(path)
    next_run_at(db, 0)
    db.close()
    stop = threading.Event()
    calls = []
    def wait(_):
        stop.set()
    stop.wait = wait
    with RUN_LOCK:
        scheduler_loop(str(path), stop, lambda *args: calls.append(args))
    assert calls == []
    db = Database(path)
    assert db.list_runs() == []
    db.close()


def test_weekly_windows_overlap_previous_execution_day(tmp_path, monkeypatch):
    import voltbot.scheduler as scheduler
    class Friday(date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 6)
    monkeypatch.setattr(scheduler, 'date', Friday)
    db = Database(tmp_path / 'schedule.db')
    next_run_at(db, 0)
    _, params = claim_due_run(db, WEEK_SECONDS)
    # A message on Oct 30 after the previous run must still be searched Nov 6.
    assert params['start'] == '2026-10-30'
    assert params['end'] == '2026-11-07'
    db.close()


def test_two_connections_cannot_claim_same_slot(tmp_path):
    path = tmp_path / 'schedule.db'
    first, second = Database(path), Database(path)
    next_run_at(first, 0)
    assert claim_due_run(first, WEEK_SECONDS) is not None
    assert claim_due_run(second, WEEK_SECONDS) is None
    first.close()
    second.close()
