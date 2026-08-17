"""Régressions du planificateur de tâches."""

import threading
import time

import pytest

from superbot.scheduler import SuperBotScheduler


def test_scheduler_instances_have_isolated_calendars():
    first = SuperBotScheduler()
    second = SuperBotScheduler()
    try:
        first.schedule_job("first", lambda: None, 60)
        assert first.get_job_status("first") is not None
        assert second.get_job_status("first") is None
        assert len(first.schedule.get_jobs()) == 1
        assert len(second.schedule.get_jobs()) == 0
    finally:
        first.executor.shutdown(wait=True)
        second.executor.shutdown(wait=True)


def test_scheduler_validates_interval_and_callable():
    scheduler = SuperBotScheduler()
    try:
        with pytest.raises(ValueError):
            scheduler.schedule_job("", lambda: None, 1)
        with pytest.raises(ValueError):
            scheduler.schedule_job("bad", None, 1)
        with pytest.raises(ValueError):
            scheduler.schedule_job("bad", lambda: None, 0)
    finally:
        scheduler.executor.shutdown(wait=True)


def test_scheduler_status_before_first_run_has_next_run():
    scheduler = SuperBotScheduler()
    try:
        scheduler.schedule_job("heartbeat", lambda: None, 60)
        status = scheduler.get_job_status("heartbeat")
        assert status is not None
        assert status["next_run"] is not None
        assert status["run_count"] == 0
    finally:
        scheduler.executor.shutdown(wait=True)


def test_scheduler_can_stop_and_restart():
    scheduler = SuperBotScheduler()
    calls = []
    event = threading.Event()

    def job():
        calls.append(1)
        event.set()

    scheduler.schedule_job("job", job, 1, run_immediately=True)
    scheduler.start()
    try:
        assert event.wait(2)
    finally:
        scheduler.stop()

    event.clear()
    scheduler.schedule_job("job", job, 1, run_immediately=True)
    scheduler.start()
    try:
        assert event.wait(2)
        assert len(calls) >= 2
    finally:
        scheduler.stop()
