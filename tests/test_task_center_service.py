from __future__ import annotations

from datetime import datetime, timezone

from control_plane.services.task_center_service import TaskCenterService
from control_plane.storage.memory import MemoryStorage
from control_plane.task_center_models import AccountRecord, IncidentRecord, SiteRecord


def _service_with_account(tmp_path):
	storage = MemoryStorage(tmp_path / 'artifacts')
	site = SiteRecord(name='Primary Site', base_url='https://example.com')
	account = AccountRecord(site_id=site.id, display_name='Alice', username='alice', password='secret-pass')
	storage.save_site(site)
	storage.save_account(account)
	return TaskCenterService(storage), storage, site, account


def test_summary_does_not_mark_accounts_pending_before_today_tasks_exist(tmp_path):
	service, storage, _, account = _service_with_account(tmp_path)
	storage.save_account(
		account.model_copy(
			update={
				'last_checkin_status': 'failed',
				'last_error_message': 'Login failed',
			}
		)
	)

	summary = service.summary()

	assert summary.today.enabled_accounts == 1
	assert summary.today.today_pending == 0
	assert summary.recent_incidents[0].display_name == 'Alice'


def test_incidents_are_coalesced_for_user_review(tmp_path):
	service, storage, site, account = _service_with_account(tmp_path)
	first_seen_at = datetime(2026, 4, 24, 9, tzinfo=timezone.utc)
	last_seen_at = datetime(2026, 4, 25, 9, tzinfo=timezone.utc)
	storage.save_incident(
		IncidentRecord(
			id='incident-old',
			task_id='task-old',
			account_id=account.id,
			site_id=site.id,
			display_name='Alice',
			site_name='Primary Site',
			status='failed',
			last_error_message='Login failed',
			type='login_failed',
			first_seen_at=first_seen_at,
			last_seen_at=first_seen_at,
		)
	)
	storage.save_incident(
		IncidentRecord(
			id='incident-new',
			task_id='task-new',
			account_id=account.id,
			site_id=site.id,
			display_name='Alice',
			site_name='Primary Site',
			status='failed',
			last_error_message='Login failed',
			type='login_failed',
			first_seen_at=last_seen_at,
			last_seen_at=last_seen_at,
		)
	)

	incidents = service.incidents()

	assert len(incidents) == 1
	assert incidents[0].id == 'incident-old'
	assert incidents[0].task_id == 'task-new'
	assert incidents[0].first_seen_at == first_seen_at
	assert incidents[0].last_seen_at == last_seen_at
