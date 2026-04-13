from __future__ import annotations

import asyncio

from control_plane.models import ConfigDomain, JobStatus, JobSummary, JobType, ScheduleSpec, TriggerType
from control_plane.services.job_service import JobService
from control_plane.settings import settings
from control_plane.storage.memory import MemoryStorage


def _system_config(browser_enabled: bool) -> dict:
    return {
        'debug': False,
        'browser_strategy': 'legacy',
        'browser_enabled': browser_enabled,
        'main_checkin_engine': 'legacy',
        'admin_password_hash': '',
    }


async def _wait_for_run(storage: MemoryStorage, run_id: str):
    for _ in range(200):
        current = storage.get_job_run(run_id)
        if current is not None and current.finished_at is not None:
            return current
        await asyncio.sleep(0.01)
    raise AssertionError(f'job {run_id} did not finish in time')


async def _run_job(tmp_path, job_type: JobType, payload: dict, *, browser_enabled: bool = False):
    settings.storage_states_dir = tmp_path / 'storage-states'
    settings.storage_states_dir.mkdir(parents=True, exist_ok=True)

    storage = MemoryStorage(tmp_path / 'artifacts')
    storage.save_config(ConfigDomain.SYSTEM, _system_config(browser_enabled))
    storage.save_config(ConfigDomain.NOTIFICATIONS, {})

    domain_map = {
        JobType.MAIN_CHECKIN: ConfigDomain.MAIN_CHECKIN,
        JobType.CHECKIN_996: ConfigDomain.CHECKIN_996,
        JobType.CHECKIN_QAQ_AL: ConfigDomain.CHECKIN_QAQ_AL,
        JobType.LINUXDO_READ: ConfigDomain.LINUXDO_READ,
    }
    storage.save_config(domain_map[job_type], payload)

    service = JobService(storage)
    run = service.start_job(job_type, TriggerType.MANUAL)
    finished = await _wait_for_run(storage, run.id)
    logs = storage.get_job_logs(run.id)
    return finished, logs


def test_job_service_failure_paths(tmp_path):
    async def scenario():
        main_run, main_logs = await _run_job(tmp_path / 'main', JobType.MAIN_CHECKIN, {})
        assert main_run.status == JobStatus.FAILED
        assert main_run.error_message == 'No account configuration available'
        assert any('Execution failed: No account configuration available' in item.message for item in main_logs)

        hub996_run, hub996_logs = await _run_job(tmp_path / '996', JobType.CHECKIN_996, {})
        assert hub996_run.status == JobStatus.FAILED
        assert hub996_run.error_message == 'No 996 accounts configured'
        assert any('Execution failed: No 996 accounts configured' in item.message for item in hub996_logs)

        qaq_run, qaq_logs = await _run_job(
            tmp_path / 'qaq',
            JobType.CHECKIN_QAQ_AL,
            {'accounts': ['sid-1'], 'tier': 3},
            browser_enabled=False,
        )
        assert qaq_run.status == JobStatus.FAILED
        assert qaq_run.error_message == 'qaq.al check-in requires browser support. Enable browser execution first.'
        assert any('browser support' in item.message for item in qaq_logs)

        linuxdo_run, linuxdo_logs = await _run_job(
            tmp_path / 'linuxdo',
            JobType.LINUXDO_READ,
            {'accounts': [{'username': 'alice', 'password': 'secret-pass'}], 'max_posts': 20},
            browser_enabled=False,
        )
        assert linuxdo_run.status == JobStatus.FAILED
        assert linuxdo_run.error_message == 'Linux.do read requires browser support. Enable browser execution first.'
        assert any('browser support' in item.message for item in linuxdo_logs)

    asyncio.run(scenario())


def test_job_service_can_start_scheduled_job_from_worker_thread(tmp_path):
    async def scenario():
        settings.storage_states_dir = tmp_path / 'storage-states'
        settings.storage_states_dir.mkdir(parents=True, exist_ok=True)

        storage = MemoryStorage(tmp_path / 'artifacts')
        storage.save_config(ConfigDomain.SYSTEM, _system_config(browser_enabled=False))
        storage.save_config(ConfigDomain.NOTIFICATIONS, {})
        storage.save_config(ConfigDomain.CHECKIN_996, {})
        storage.save_schedule(
            ScheduleSpec(
                job_type=JobType.CHECKIN_996,
                enabled=True,
                cron='*/10 * * * *',
                timezone='Asia/Shanghai',
                cooldown_seconds=0,
            )
        )

        service = JobService(storage)
        service.bind_loop(asyncio.get_running_loop())

        run = await asyncio.to_thread(service.start_job, JobType.CHECKIN_996, TriggerType.SCHEDULED)
        finished = await _wait_for_run(storage, run.id)

        assert finished.status == JobStatus.FAILED
        assert finished.error_message == 'No 996 accounts configured'

    asyncio.run(scenario())


def test_job_service_marks_aux_job_failed_when_summary_contains_failed_accounts(tmp_path, monkeypatch):
    async def scenario():
        settings.storage_states_dir = tmp_path / 'storage-states'
        settings.storage_states_dir.mkdir(parents=True, exist_ok=True)

        storage = MemoryStorage(tmp_path / 'artifacts')
        storage.save_config(ConfigDomain.SYSTEM, _system_config(browser_enabled=True))
        storage.save_config(ConfigDomain.NOTIFICATIONS, {})
        storage.save_config(
            ConfigDomain.LINUXDO_READ,
            {'accounts': [{'username': 'alice', 'password': 'secret-pass'}], 'max_posts': 20},
        )

        async def fake_execute_linuxdo_read(*args, **kwargs):
            return JobSummary(
                success_count=0,
                total_count=1,
                notification_sent=False,
                extra={'results': [{'username': 'alice', 'success': False, 'result': {'error': 'Login failed'}}]},
            )

        monkeypatch.setattr(
            'control_plane.services.job_service.execute_linuxdo_read',
            fake_execute_linuxdo_read,
        )

        service = JobService(storage)
        run = service.start_job(JobType.LINUXDO_READ, TriggerType.MANUAL)
        finished = await _wait_for_run(storage, run.id)
        logs = storage.get_job_logs(run.id)

        assert finished.status == JobStatus.FAILED
        assert finished.error_code == 'partial_failure'
        assert finished.error_message == 'linuxdo_read completed with failures: 0/1 succeeded'
        assert finished.summary is not None
        assert finished.summary.success_count == 0
        assert any('0/1 succeeded' in item.message for item in logs)

    asyncio.run(scenario())


def test_job_service_marks_main_checkin_failed_when_summary_contains_failed_methods(tmp_path, monkeypatch):
    async def scenario():
        settings.storage_states_dir = tmp_path / 'storage-states'
        settings.storage_states_dir.mkdir(parents=True, exist_ok=True)

        storage = MemoryStorage(tmp_path / 'artifacts')
        storage.save_config(ConfigDomain.SYSTEM, _system_config(browser_enabled=True))
        storage.save_config(ConfigDomain.NOTIFICATIONS, {})
        storage.save_config(ConfigDomain.MAIN_CHECKIN, {'accounts': [{'provider': 'anyrouter'}]})

        async def fake_execute_main_checkin(*args, **kwargs):
            return JobSummary(
                success_count=0,
                total_count=1,
                notification_sent=False,
                extra={'balance_hash': ''},
            )

        monkeypatch.setattr(
            'control_plane.services.job_service.execute_main_checkin',
            fake_execute_main_checkin,
        )

        service = JobService(storage)
        run = service.start_job(JobType.MAIN_CHECKIN, TriggerType.MANUAL)
        finished = await _wait_for_run(storage, run.id)
        logs = storage.get_job_logs(run.id)

        assert finished.status == JobStatus.FAILED
        assert finished.error_code == 'partial_failure'
        assert finished.error_message == 'main_checkin completed with failures: 0/1 succeeded'
        assert finished.summary is not None
        assert any('0/1 succeeded' in item.message for item in logs)

    asyncio.run(scenario())


def test_job_service_can_run_main_checkin_via_task_center_engine(tmp_path, monkeypatch):
    async def scenario():
        settings.storage_states_dir = tmp_path / 'storage-states'
        settings.storage_states_dir.mkdir(parents=True, exist_ok=True)

        storage = MemoryStorage(tmp_path / 'artifacts')
        system_config = _system_config(browser_enabled=False)
        system_config['main_checkin_engine'] = 'task_center'
        storage.save_config(ConfigDomain.SYSTEM, system_config)
        storage.save_config(ConfigDomain.NOTIFICATIONS, {})
        storage.save_config(ConfigDomain.MAIN_CHECKIN, {})

        async def fake_execute_main_checkin_task_center(storage_backend, emit_log):
            emit_log('task center engine invoked')
            return JobSummary(
                success_count=2,
                total_count=2,
                notification_sent=False,
                extra={'engine': 'task_center'},
            )

        monkeypatch.setattr(
            'control_plane.services.job_service.execute_main_checkin_task_center',
            fake_execute_main_checkin_task_center,
        )

        service = JobService(storage)
        run = service.start_job(JobType.MAIN_CHECKIN, TriggerType.MANUAL)
        finished = await _wait_for_run(storage, run.id)
        logs = storage.get_job_logs(run.id)

        assert finished.status == JobStatus.SUCCESS
        assert finished.summary is not None
        assert finished.summary.extra['engine'] == 'task_center'
        assert any('task center engine invoked' in item.message for item in logs)

    asyncio.run(scenario())


def test_job_service_task_center_engine_fails_without_sites(tmp_path):
    async def scenario():
        settings.storage_states_dir = tmp_path / 'storage-states'
        settings.storage_states_dir.mkdir(parents=True, exist_ok=True)

        storage = MemoryStorage(tmp_path / 'artifacts')
        system_config = _system_config(browser_enabled=False)
        system_config['main_checkin_engine'] = 'task_center'
        storage.save_config(ConfigDomain.SYSTEM, system_config)
        storage.save_config(ConfigDomain.NOTIFICATIONS, {})
        storage.save_config(ConfigDomain.MAIN_CHECKIN, {})

        service = JobService(storage)
        run = service.start_job(JobType.MAIN_CHECKIN, TriggerType.MANUAL)
        finished = await _wait_for_run(storage, run.id)
        logs = storage.get_job_logs(run.id)

        assert finished.status == JobStatus.FAILED
        assert finished.error_message == 'Task center engine requires at least one enabled site'
        assert any('enabled site' in item.message for item in logs)

    asyncio.run(scenario())
