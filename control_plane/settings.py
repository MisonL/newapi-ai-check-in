from __future__ import annotations

import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        base_dir = Path(os.getenv("CONTROL_PLANE_DATA_DIR", "runtime_data"))
        self.storage_mode = os.getenv("CONTROL_PLANE_STORAGE_MODE", "persistent")
        self.host = os.getenv("CONTROL_PLANE_HOST", "127.0.0.1")
        self.port = int(os.getenv("CONTROL_PLANE_PORT", "18080"))
        self.internal_token = os.getenv("CONTROL_PLANE_INTERNAL_TOKEN", "change-me")
        self.bootstrap_admin_password = os.getenv("CONTROL_PLANE_ADMIN_PASSWORD", "")
        self.timezone = os.getenv("CONTROL_PLANE_TIMEZONE", "Asia/Shanghai")
        self.base_dir = base_dir
        self.db_path = base_dir / "control_plane.db"
        self.artifacts_dir = base_dir / "artifacts"
        self.storage_states_dir = base_dir / "storage-states"
        self.logs_dir = base_dir / "logs"
        self.screenshots_dir = base_dir / "screenshots"

    def ensure_directories(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.storage_states_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
