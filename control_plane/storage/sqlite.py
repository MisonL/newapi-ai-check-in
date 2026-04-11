from __future__ import annotations

import sqlite3
from pathlib import Path

from control_plane.models import ArtifactRef, ConfigDomain, JobLogLine, JobRun, JobType, ScheduleSpec
from control_plane.storage.base import StorageBackend


class SqliteStorage(StorageBackend):
    def __init__(self, db_path: Path, artifact_root: Path) -> None:
        self._db_path = db_path
        self._artifact_root = artifact_root
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS configs (
                    domain TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS schedules (
                    job_type TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_runs (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                """
            )

    def load_config(self, domain: ConfigDomain) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM configs WHERE domain = ?", (domain.value,)).fetchone()
        return {} if row is None else __import__("json").loads(row["payload"])

    def save_config(self, domain: ConfigDomain, payload: dict) -> None:
        data = __import__("json").dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO configs(domain, payload) VALUES(?, ?) "
                "ON CONFLICT(domain) DO UPDATE SET payload = excluded.payload",
                (domain.value, data),
            )

    def load_schedule(self, job_type: JobType) -> ScheduleSpec:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM schedules WHERE job_type = ?", (job_type.value,)).fetchone()
        if row is None:
            return ScheduleSpec(job_type=job_type)
        return ScheduleSpec.model_validate_json(row["payload"])

    def save_schedule(self, schedule: ScheduleSpec) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO schedules(job_type, payload) VALUES(?, ?) "
                "ON CONFLICT(job_type) DO UPDATE SET payload = excluded.payload",
                (schedule.job_type.value, schedule.model_dump_json()),
            )

    def list_schedules(self) -> list[ScheduleSpec]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM schedules").fetchall()
        return [ScheduleSpec.model_validate_json(row["payload"]) for row in rows]

    def create_job_run(self, run: JobRun) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO job_runs(id, payload) VALUES(?, ?)", (run.id, run.model_dump_json()))

    def update_job_run(self, run: JobRun) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE job_runs SET payload = ? WHERE id = ?", (run.model_dump_json(), run.id))

    def get_job_run(self, run_id: str) -> JobRun | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM job_runs WHERE id = ?", (run_id,)).fetchone()
        return None if row is None else JobRun.model_validate_json(row["payload"])

    def list_job_runs(self, job_type: JobType | None = None, limit: int | None = None) -> list[JobRun]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM job_runs").fetchall()
        runs = [JobRun.model_validate_json(row["payload"]) for row in rows]
        if job_type is not None:
            runs = [run for run in runs if run.job_type == job_type]
        ordered = sorted(runs, key=lambda item: item.started_at, reverse=True)
        return ordered[:limit] if limit is not None else ordered

    def append_job_log(self, log_line: JobLogLine) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO job_logs(run_id, payload) VALUES(?, ?)",
                (log_line.run_id, log_line.model_dump_json()),
            )

    def get_job_logs(self, run_id: str) -> list[JobLogLine]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM job_logs WHERE run_id = ? ORDER BY id ASC", (run_id,)).fetchall()
        return [JobLogLine.model_validate_json(row["payload"]) for row in rows]

    def save_artifact(self, run_id: str, artifact: ArtifactRef, content: bytes) -> ArtifactRef:
        run_dir = self._artifact_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        target = run_dir / Path(artifact.path).name
        target.write_bytes(content)
        saved = artifact.model_copy(update={"path": str(target), "size": target.stat().st_size})
        run = self.get_job_run(run_id)
        if run is not None:
            run.artifacts.append(saved)
            self.update_job_run(run)
        return saved
