from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from control_plane.models import ArtifactRef, ConfigDomain, JobLogLine, JobRun, JobType, ScheduleSpec
from control_plane.storage.base import StorageBackend


class MemoryStorage(StorageBackend):
    def __init__(self, artifact_root: Path) -> None:
        self._configs: dict[str, dict] = {}
        self._schedules: dict[str, ScheduleSpec] = {}
        self._runs: dict[str, JobRun] = {}
        self._logs: dict[str, list[JobLogLine]] = defaultdict(list)
        self._artifact_root = artifact_root
        self._artifact_root.mkdir(parents=True, exist_ok=True)

    def load_config(self, domain: ConfigDomain) -> dict:
        return deepcopy(self._configs.get(domain.value, {}))

    def save_config(self, domain: ConfigDomain, payload: dict) -> None:
        self._configs[domain.value] = deepcopy(payload)

    def load_schedule(self, job_type: JobType) -> ScheduleSpec:
        return self._schedules.get(job_type.value, ScheduleSpec(job_type=job_type))

    def save_schedule(self, schedule: ScheduleSpec) -> None:
        self._schedules[schedule.job_type.value] = schedule

    def list_schedules(self) -> list[ScheduleSpec]:
        return list(self._schedules.values())

    def create_job_run(self, run: JobRun) -> None:
        self._runs[run.id] = run

    def update_job_run(self, run: JobRun) -> None:
        self._runs[run.id] = run

    def get_job_run(self, run_id: str) -> JobRun | None:
        return self._runs.get(run_id)

    def list_job_runs(self, job_type: JobType | None = None, limit: int | None = None) -> list[JobRun]:
        runs = list(self._runs.values())
        if job_type is not None:
            runs = [run for run in runs if run.job_type == job_type]
        ordered = sorted(runs, key=lambda item: item.started_at, reverse=True)
        return ordered[:limit] if limit is not None else ordered

    def append_job_log(self, log_line: JobLogLine) -> None:
        self._logs[log_line.run_id].append(log_line)

    def get_job_logs(self, run_id: str) -> list[JobLogLine]:
        return list(self._logs.get(run_id, []))

    def save_artifact(self, run_id: str, artifact: ArtifactRef, content: bytes) -> ArtifactRef:
        run_dir = self._artifact_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        target = run_dir / Path(artifact.path).name
        target.write_bytes(content)
        saved = artifact.model_copy(update={"path": str(target), "size": target.stat().st_size})
        run = self._runs.get(run_id)
        if run is not None:
            run.artifacts.append(saved)
        return saved
