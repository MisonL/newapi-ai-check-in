from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from control_plane.models import ArtifactRef, ConfigDomain, JobLogLine, JobRun, JobType, ScheduleSpec
from control_plane.storage.base import StorageBackend
from control_plane.task_center_models import (
	AccountRecord,
	CheckinResultRecord,
	DailyTaskRecord,
	IncidentRecord,
	SiteRecord,
)


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
                CREATE TABLE IF NOT EXISTS sites (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS daily_tasks (
                    id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    task_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(account_id, task_date)
                );
                CREATE TABLE IF NOT EXISTS checkin_results (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL UNIQUE,
                    site_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    checkin_date TEXT,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    task_id TEXT,
                    resolved INTEGER NOT NULL,
                    severity TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                """
			)

	def load_config(self, domain: ConfigDomain) -> dict:
		with self._connect() as conn:
			row = conn.execute('SELECT payload FROM configs WHERE domain = ?', (domain.value,)).fetchone()
		return {} if row is None else __import__('json').loads(row['payload'])

	def save_config(self, domain: ConfigDomain, payload: dict) -> None:
		data = json.dumps(payload, ensure_ascii=False)
		with self._connect() as conn:
			conn.execute(
				'INSERT INTO configs(domain, payload) VALUES(?, ?) '
				'ON CONFLICT(domain) DO UPDATE SET payload = excluded.payload',
				(domain.value, data),
			)

	def load_schedule(self, job_type: JobType) -> ScheduleSpec:
		with self._connect() as conn:
			row = conn.execute('SELECT payload FROM schedules WHERE job_type = ?', (job_type.value,)).fetchone()
		if row is None:
			return ScheduleSpec(job_type=job_type)
		return ScheduleSpec.model_validate_json(row['payload'])

	def save_schedule(self, schedule: ScheduleSpec) -> None:
		with self._connect() as conn:
			conn.execute(
				'INSERT INTO schedules(job_type, payload) VALUES(?, ?) '
				'ON CONFLICT(job_type) DO UPDATE SET payload = excluded.payload',
				(schedule.job_type.value, schedule.model_dump_json()),
			)

	def list_schedules(self) -> list[ScheduleSpec]:
		with self._connect() as conn:
			rows = conn.execute('SELECT payload FROM schedules').fetchall()
		return [ScheduleSpec.model_validate_json(row['payload']) for row in rows]

	def create_job_run(self, run: JobRun) -> None:
		with self._connect() as conn:
			conn.execute('INSERT INTO job_runs(id, payload) VALUES(?, ?)', (run.id, run.model_dump_json()))

	def update_job_run(self, run: JobRun) -> None:
		with self._connect() as conn:
			conn.execute('UPDATE job_runs SET payload = ? WHERE id = ?', (run.model_dump_json(), run.id))

	def get_job_run(self, run_id: str) -> JobRun | None:
		with self._connect() as conn:
			row = conn.execute('SELECT payload FROM job_runs WHERE id = ?', (run_id,)).fetchone()
		return None if row is None else JobRun.model_validate_json(row['payload'])

	def list_job_runs(self, job_type: JobType | None = None, limit: int | None = None) -> list[JobRun]:
		with self._connect() as conn:
			rows = conn.execute('SELECT payload FROM job_runs').fetchall()
		runs = [JobRun.model_validate_json(row['payload']) for row in rows]
		if job_type is not None:
			runs = [run for run in runs if run.job_type == job_type]
		ordered = sorted(runs, key=lambda item: item.started_at, reverse=True)
		return ordered[:limit] if limit is not None else ordered

	def append_job_log(self, log_line: JobLogLine) -> None:
		with self._connect() as conn:
			conn.execute(
				'INSERT INTO job_logs(run_id, payload) VALUES(?, ?)',
				(log_line.run_id, log_line.model_dump_json()),
			)

	def get_job_logs(self, run_id: str) -> list[JobLogLine]:
		with self._connect() as conn:
			rows = conn.execute('SELECT payload FROM job_logs WHERE run_id = ? ORDER BY id ASC', (run_id,)).fetchall()
		return [JobLogLine.model_validate_json(row['payload']) for row in rows]

	def save_artifact(self, run_id: str, artifact: ArtifactRef, content: bytes) -> ArtifactRef:
		run_dir = self._artifact_root / run_id
		run_dir.mkdir(parents=True, exist_ok=True)
		target = run_dir / Path(artifact.path).name
		target.write_bytes(content)
		saved = artifact.model_copy(update={'path': str(target), 'size': target.stat().st_size})
		run = self.get_job_run(run_id)
		if run is not None:
			run.artifacts.append(saved)
			self.update_job_run(run)
		return saved

	def list_sites(self) -> list[SiteRecord]:
		with self._connect() as conn:
			rows = conn.execute('SELECT payload FROM sites').fetchall()
		items = [SiteRecord.model_validate_json(row['payload']) for row in rows]
		return sorted(items, key=lambda item: item.updated_at, reverse=True)

	def get_site(self, site_id: str) -> SiteRecord | None:
		with self._connect() as conn:
			row = conn.execute('SELECT payload FROM sites WHERE id = ?', (site_id,)).fetchone()
		return None if row is None else SiteRecord.model_validate_json(row['payload'])

	def save_site(self, site: SiteRecord) -> None:
		with self._connect() as conn:
			conn.execute(
				'INSERT INTO sites(id, payload) VALUES(?, ?) ON CONFLICT(id) DO UPDATE SET payload = excluded.payload',
				(site.id, site.model_dump_json()),
			)

	def delete_site(self, site_id: str) -> None:
		with self._connect() as conn:
			conn.execute('DELETE FROM sites WHERE id = ?', (site_id,))

	def list_accounts(self, site_id: str | None = None) -> list[AccountRecord]:
		with self._connect() as conn:
			if site_id is None:
				rows = conn.execute('SELECT payload FROM accounts').fetchall()
			else:
				rows = conn.execute('SELECT payload FROM accounts WHERE site_id = ?', (site_id,)).fetchall()
		items = [AccountRecord.model_validate_json(row['payload']) for row in rows]
		return sorted(items, key=lambda item: item.updated_at, reverse=True)

	def get_account(self, account_id: str) -> AccountRecord | None:
		with self._connect() as conn:
			row = conn.execute('SELECT payload FROM accounts WHERE id = ?', (account_id,)).fetchone()
		return None if row is None else AccountRecord.model_validate_json(row['payload'])

	def save_account(self, account: AccountRecord) -> None:
		with self._connect() as conn:
			conn.execute(
				'INSERT INTO accounts(id, site_id, payload) VALUES(?, ?, ?) '
				'ON CONFLICT(id) DO UPDATE SET site_id = excluded.site_id, payload = excluded.payload',
				(account.id, account.site_id, account.model_dump_json()),
			)

	def delete_account(self, account_id: str) -> None:
		with self._connect() as conn:
			conn.execute('DELETE FROM accounts WHERE id = ?', (account_id,))

	def list_daily_tasks(
		self,
		task_date: date | None = None,
		status: str | None = None,
		site_id: str | None = None,
		account_id: str | None = None,
	) -> list[DailyTaskRecord]:
		query = 'SELECT payload FROM daily_tasks WHERE 1=1'
		params: list[str] = []
		if task_date is not None:
			query += ' AND task_date = ?'
			params.append(task_date.isoformat())
		if status is not None:
			query += ' AND status = ?'
			params.append(status)
		if site_id is not None:
			query += ' AND site_id = ?'
			params.append(site_id)
		if account_id is not None:
			query += ' AND account_id = ?'
			params.append(account_id)
		query += ' ORDER BY task_date DESC, updated_at DESC'
		with self._connect() as conn:
			rows = conn.execute(query, params).fetchall()
		return [DailyTaskRecord.model_validate_json(row['payload']) for row in rows]

	def get_daily_task(self, task_id: str) -> DailyTaskRecord | None:
		with self._connect() as conn:
			row = conn.execute('SELECT payload FROM daily_tasks WHERE id = ?', (task_id,)).fetchone()
		return None if row is None else DailyTaskRecord.model_validate_json(row['payload'])

	def save_daily_task(self, task: DailyTaskRecord) -> None:
		with self._connect() as conn:
			existing = conn.execute(
				'SELECT id FROM daily_tasks WHERE account_id = ? AND task_date = ?',
				(task.account_id, task.task_date.isoformat()),
			).fetchone()
			task_id = existing['id'] if existing is not None else task.id
			payload = task.model_copy(update={'id': task_id}).model_dump_json()
			conn.execute(
				'INSERT INTO daily_tasks(id, site_id, account_id, task_date, status, updated_at, payload) '
				'VALUES(?, ?, ?, ?, ?, ?, ?) '
				'ON CONFLICT(id) DO UPDATE SET site_id = excluded.site_id, account_id = excluded.account_id, '
				'task_date = excluded.task_date, status = excluded.status, updated_at = excluded.updated_at, payload = excluded.payload',
				(
					task_id,
					task.site_id,
					task.account_id,
					task.task_date.isoformat(),
					task.status,
					task.updated_at.isoformat(),
					payload,
				),
			)

	def delete_daily_task(self, task_id: str) -> None:
		with self._connect() as conn:
			conn.execute('DELETE FROM daily_tasks WHERE id = ?', (task_id,))

	def list_checkin_results(
		self,
		task_id: str | None = None,
		site_id: str | None = None,
		account_id: str | None = None,
	) -> list[CheckinResultRecord]:
		query = 'SELECT payload FROM checkin_results WHERE 1=1'
		params: list[str] = []
		if task_id is not None:
			query += ' AND task_id = ?'
			params.append(task_id)
		if site_id is not None:
			query += ' AND site_id = ?'
			params.append(site_id)
		if account_id is not None:
			query += ' AND account_id = ?'
			params.append(account_id)
		query += ' ORDER BY created_at DESC'
		with self._connect() as conn:
			rows = conn.execute(query, params).fetchall()
		return [CheckinResultRecord.model_validate_json(row['payload']) for row in rows]

	def get_checkin_result(self, task_id: str) -> CheckinResultRecord | None:
		with self._connect() as conn:
			row = conn.execute('SELECT payload FROM checkin_results WHERE task_id = ?', (task_id,)).fetchone()
		return None if row is None else CheckinResultRecord.model_validate_json(row['payload'])

	def save_checkin_result(self, result: CheckinResultRecord) -> None:
		with self._connect() as conn:
			existing = conn.execute(
				'SELECT id FROM checkin_results WHERE task_id = ?',
				(result.task_id,),
			).fetchone()
			result_id = existing['id'] if existing is not None else result.id
			payload = result.model_copy(update={'id': result_id}).model_dump_json()
			conn.execute(
				'INSERT INTO checkin_results(id, task_id, site_id, account_id, checkin_date, created_at, payload) '
				'VALUES(?, ?, ?, ?, ?, ?, ?) '
				'ON CONFLICT(id) DO UPDATE SET task_id = excluded.task_id, site_id = excluded.site_id, '
				'account_id = excluded.account_id, checkin_date = excluded.checkin_date, created_at = excluded.created_at, payload = excluded.payload',
				(
					result_id,
					result.task_id,
					result.site_id,
					result.account_id,
					result.checkin_date.isoformat() if result.checkin_date is not None else None,
					result.created_at.isoformat(),
					payload,
				),
			)

	def delete_checkin_result(self, result_id: str) -> None:
		with self._connect() as conn:
			conn.execute('DELETE FROM checkin_results WHERE id = ?', (result_id,))

	def list_incidents(
		self,
		resolved: bool | None = None,
		site_id: str | None = None,
		account_id: str | None = None,
	) -> list[IncidentRecord]:
		query = 'SELECT payload FROM incidents WHERE 1=1'
		params: list[object] = []
		if resolved is not None:
			query += ' AND resolved = ?'
			params.append(1 if resolved else 0)
		if site_id is not None:
			query += ' AND site_id = ?'
			params.append(site_id)
		if account_id is not None:
			query += ' AND account_id = ?'
			params.append(account_id)
		query += ' ORDER BY last_seen_at DESC'
		with self._connect() as conn:
			rows = conn.execute(query, params).fetchall()
		return [IncidentRecord.model_validate_json(row['payload']) for row in rows]

	def save_incident(self, incident: IncidentRecord) -> None:
		with self._connect() as conn:
			if incident.dedupe_key:
				row = conn.execute(
					"SELECT payload FROM incidents WHERE json_extract(payload, '$.dedupe_key') = ?",
					(incident.dedupe_key,),
				).fetchone()
				if row is not None:
					duplicate = IncidentRecord.model_validate_json(row['payload'])
					update = {
						'id': duplicate.id,
						'first_seen_at': duplicate.first_seen_at,
					}
					if not incident.resolved:
						update['resolved'] = duplicate.resolved
					if not incident.resolution_action:
						update['resolution_action'] = duplicate.resolution_action
					incident = incident.model_copy(update=update)
			conn.execute(
				'INSERT INTO incidents(id, site_id, account_id, task_id, resolved, severity, last_seen_at, payload) '
				'VALUES(?, ?, ?, ?, ?, ?, ?, ?) '
				'ON CONFLICT(id) DO UPDATE SET site_id = excluded.site_id, account_id = excluded.account_id, '
				'task_id = excluded.task_id, resolved = excluded.resolved, severity = excluded.severity, '
				'last_seen_at = excluded.last_seen_at, payload = excluded.payload',
				(
					incident.id,
					incident.site_id,
					incident.account_id,
					incident.task_id,
					1 if incident.resolved else 0,
					incident.severity,
					incident.last_seen_at.isoformat(),
					incident.model_dump_json(),
				),
			)

	def delete_incident(self, incident_id: str) -> None:
		with self._connect() as conn:
			conn.execute('DELETE FROM incidents WHERE id = ?', (incident_id,))
