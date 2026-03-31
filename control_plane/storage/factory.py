from __future__ import annotations

from control_plane.settings import settings
from control_plane.storage.base import StorageBackend
from control_plane.storage.memory import MemoryStorage
from control_plane.storage.sqlite import SqliteStorage


def create_storage() -> StorageBackend:
    settings.ensure_directories()
    if settings.storage_mode == "memory":
        return MemoryStorage(settings.artifacts_dir)
    return SqliteStorage(settings.db_path, settings.artifacts_dir)
