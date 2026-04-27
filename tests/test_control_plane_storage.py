from __future__ import annotations

from datetime import date, datetime, timezone

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
from control_plane.task_center_models import (
	AccountRecord,
	CheckinResultRecord,
	DailyTaskRecord,
	IncidentRecord,
	SiteRecord,
)


def _exercise_backend(storage) -> None:
	storage.save_config(ConfigDomain.SYSTEM, {'debug': True})
	assert storage.load_config(ConfigDomain.SYSTEM) == {'debug': True}

	schedule = ScheduleSpec(job_type=JobType.MAIN_CHECKIN, enabled=True, cron='*/5 * * * *')
	storage.save_schedule(schedule)
	assert storage.load_schedule(JobType.MAIN_CHECKIN).enabled is True

	run = JobRun(
		id='run-1',
		job_type=JobType.MAIN_CHECKIN,
		trigger=TriggerType.MANUAL,
		status=JobStatus.SUCCESS,
		finished_at=datetime.now(timezone.utc),
		exit_code=0,
	)
	storage.create_job_run(run)
	storage.append_job_log(JobLogLine(run_id='run-1', stream='stdout', message='hello'))
	saved = storage.save_artifact(
		'run-1',
		ArtifactRef(kind='text', path='report.txt', content_type='text/plain', size=0),
		b'artifact',
	)
	loaded = storage.get_job_run('run-1')
	assert loaded is not None
	assert loaded.artifacts[0].path == saved.path
	assert storage.get_job_logs('run-1')[0].message == 'hello'

	newer_run = JobRun(
		id='run-2',
		job_type=JobType.CHECKIN_996,
		trigger=TriggerType.MANUAL,
		status=JobStatus.FAILED,
		finished_at=datetime.now(timezone.utc),
		exit_code=1,
	)
	storage.create_job_run(newer_run)
	assert [item.id for item in storage.list_job_runs(limit=1)] == ['run-2']
	assert [item.id for item in storage.list_job_runs(JobType.MAIN_CHECKIN, limit=1)] == ['run-1']

	site = SiteRecord(name='Primary Site', base_url='https://example.com')
	storage.save_site(site)
	assert storage.get_site(site.id) is not None
	assert storage.list_sites()[0].name == 'Primary Site'

	account = AccountRecord(site_id=site.id, username='alice', password='secret-pass')
	storage.save_account(account)
	assert storage.get_account(account.id) is not None
	assert storage.list_accounts(site.id)[0].username == 'alice'

	task = DailyTaskRecord(site_id=site.id, account_id=account.id, task_date=date(2026, 4, 13))
	storage.save_daily_task(task)
	assert storage.get_daily_task(task.id) is not None
	assert storage.list_daily_tasks(task_date=date(2026, 4, 13))[0].account_id == account.id

	result = CheckinResultRecord(
		task_id=task.id,
		site_id=site.id,
		account_id=account.id,
		checked_in_today_before_run=False,
		quota_awarded=1234,
		checkin_date=date(2026, 4, 13),
		total_checkins=10,
		total_quota_awarded=23456,
	)
	storage.save_checkin_result(result)
	assert storage.get_checkin_result(task.id) is not None
	assert storage.list_checkin_results(task_id=task.id)[0].quota_awarded == 1234

	incident = IncidentRecord(
		task_id=task.id,
		account_id=account.id,
		site_id=site.id,
		display_name='Alice',
		site_name='Primary Site',
		status='failed',
		last_error_message='login failed',
		type='login_failed',
	)
	storage.save_incident(incident)
	assert storage.list_incidents()[0].type == 'login_failed'

	newer_incident = incident.model_copy(
		update={
			'id': 'incident-newer',
			'task_id': 'task-newer',
			'dedupe_key': 'alice:2026-04-13:login_failed',
			'last_error_message': 'login failed again',
			'last_seen_at': datetime(2026, 4, 13, 9, tzinfo=timezone.utc),
		}
	)
	storage.save_incident(incident.model_copy(update={'dedupe_key': 'alice:2026-04-13:login_failed'}))
	storage.save_incident(newer_incident)
	incidents = storage.list_incidents()
	assert len(incidents) == 1
	assert incidents[0].id == incident.id
	assert incidents[0].task_id == 'task-newer'
	assert incidents[0].last_error_message == 'login failed again'


def test_memory_storage(tmp_path):
	_exercise_backend(MemoryStorage(tmp_path / 'artifacts'))


def test_sqlite_storage(tmp_path):
	_exercise_backend(SqliteStorage(tmp_path / 'control.db', tmp_path / 'artifacts'))
