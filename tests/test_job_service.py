from __future__ import annotations

import asyncio

from control_plane.models import ConfigDomain, JobStatus, JobType, TriggerType
from control_plane.services.job_service import JobService
from control_plane.settings import settings
from control_plane.storage.memory import MemoryStorage


def _system_config(browser_enabled: bool) -> dict:
    return {
        'debug': False,
        'browser_strategy': 'legacy',
        'browser_enabled': browser_enabled,
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
