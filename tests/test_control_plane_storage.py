from __future__ import annotations

from datetime import datetime, timezone

from control_plane.models import (
    ArtifactRef,
    ConfigDomain,
    JobLogLine,
    JobRun,
    JobStatus,
    JobType,
    ScheduleSpec,
    TriggerType,
)
from control_plane.storage.memory import MemoryStorage
from control_plane.storage.sqlite import SqliteStorage


def _exercise_backend(storage) -> None:
    storage.save_config(ConfigDomain.SYSTEM, {"debug": True})
    assert storage.load_config(ConfigDomain.SYSTEM) == {"debug": True}

    schedule = ScheduleSpec(job_type=JobType.MAIN_CHECKIN, enabled=True, cron="*/5 * * * *")
    storage.save_schedule(schedule)
    assert storage.load_schedule(JobType.MAIN_CHECKIN).enabled is True

    run = JobRun(
        id="run-1",
        job_type=JobType.MAIN_CHECKIN,
        trigger=TriggerType.MANUAL,
        status=JobStatus.SUCCESS,
        finished_at=datetime.now(timezone.utc),
        exit_code=0,
    )
    storage.create_job_run(run)
    storage.append_job_log(JobLogLine(run_id="run-1", stream="stdout", message="hello"))
    saved = storage.save_artifact(
        "run-1",
        ArtifactRef(kind="text", path="report.txt", content_type="text/plain", size=0),
        b"artifact",
    )
    loaded = storage.get_job_run("run-1")
    assert loaded is not None
    assert loaded.artifacts[0].path == saved.path
    assert storage.get_job_logs("run-1")[0].message == "hello"

    newer_run = JobRun(
        id="run-2",
        job_type=JobType.CHECKIN_996,
        trigger=TriggerType.MANUAL,
        status=JobStatus.FAILED,
        finished_at=datetime.now(timezone.utc),
        exit_code=1,
    )
    storage.create_job_run(newer_run)
    assert [item.id for item in storage.list_job_runs(limit=1)] == ["run-2"]
    assert [item.id for item in storage.list_job_runs(JobType.MAIN_CHECKIN, limit=1)] == ["run-1"]


def test_memory_storage(tmp_path):
    _exercise_backend(MemoryStorage(tmp_path / "artifacts"))


def test_sqlite_storage(tmp_path):
    _exercise_backend(SqliteStorage(tmp_path / "control.db", tmp_path / "artifacts"))
