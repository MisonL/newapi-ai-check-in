from __future__ import annotations

from control_plane.services.legacy_oauth_executor import LegacyOAuthExecutor
from control_plane.services.newapi_checkin_service import NewApiCheckinService
from control_plane.services.newapi_client import NewApiClient
from control_plane.services.task_center_executor import TaskCenterTaskExecutor
from control_plane.storage.base import StorageBackend


def build_newapi_checkin_service(storage: StorageBackend) -> NewApiCheckinService:
	return NewApiCheckinService(
		lambda site: NewApiClient(site.base_url),
		oauth_executor=LegacyOAuthExecutor(storage).run,
	)


def build_task_center_executor(storage: StorageBackend) -> TaskCenterTaskExecutor:
	return TaskCenterTaskExecutor(storage, build_newapi_checkin_service(storage))
