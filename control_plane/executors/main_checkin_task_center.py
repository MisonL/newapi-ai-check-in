from __future__ import annotations

from control_plane.models import JobSummary
from control_plane.services.task_center_service import TaskCenterService
from control_plane.storage.base import StorageBackend


async def execute_main_checkin_task_center(storage: StorageBackend, emit_log) -> JobSummary:
    service = TaskCenterService(storage)
    enabled_sites = [site for site in service.list_sites() if site.enabled]
    enabled_accounts = [account for account in service.list_accounts() if account.enabled]
    if not enabled_sites:
        raise ValueError('Task center engine requires at least one enabled site')
    if not enabled_accounts:
        raise ValueError('Task center engine requires at least one enabled account')
    generation = service.generate_today_tasks()
    emit_log(
        'Generated today tasks: '
        f'total_accounts={generation.total_accounts} created={generation.created_count} existing={generation.existing_count}'
    )
    batch = await service.execute_today_tasks(generation.task_date)
    emit_log(
        'Executed today tasks: '
        f'selected={batch.total_selected} success={batch.success_count} skipped={batch.skipped_count} '
        f'blocked={batch.blocked_count} failed={batch.failed_count}'
    )
    return JobSummary(
        success_count=batch.success_count + batch.skipped_count,
        total_count=batch.total_selected,
        notification_sent=False,
        extra={
            'engine': 'task_center',
            'generated_created_count': generation.created_count,
            'generated_existing_count': generation.existing_count,
            'executed_count': batch.executed_count,
            'blocked_count': batch.blocked_count,
            'failed_count': batch.failed_count,
            'task_ids': batch.task_ids,
        },
    )
