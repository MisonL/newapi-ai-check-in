from __future__ import annotations

import os
from pathlib import Path
from typing import Literal


DeployMode = Literal["control_plane", "github_actions"]


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _parse_bool(value: str | None, default: bool = False) -> bool:
    normalized = _normalize_optional(value)
    if normalized is None:
        return default
    return normalized.lower() in {'1', 'true', 'yes', 'on'}


def resolve_deploy_mode(
    raw_mode: str | None,
    raw_scheduler_enabled: str | None,
) -> tuple[DeployMode, bool]:
    normalized_mode = _normalize_optional(raw_mode)
    normalized_scheduler = _normalize_optional(raw_scheduler_enabled)

    if normalized_mode is not None and normalized_mode not in {"control_plane", "github_actions"}:
        raise ValueError("CONTROL_PLANE_DEPLOY_MODE must be 'control_plane' or 'github_actions'")

    if normalized_mode is None:
        scheduler_enabled = _parse_bool(normalized_scheduler, True)
        deploy_mode: DeployMode = "control_plane" if scheduler_enabled else "github_actions"
        return deploy_mode, scheduler_enabled

    expected_scheduler = normalized_mode == "control_plane"
    if normalized_scheduler is not None:
        scheduler_enabled = _parse_bool(normalized_scheduler, expected_scheduler)
        if scheduler_enabled != expected_scheduler:
            raise ValueError("CONTROL_PLANE_DEPLOY_MODE conflicts with CONTROL_PLANE_SCHEDULER_ENABLED")

    return normalized_mode, expected_scheduler


class Settings:
    def __init__(self) -> None:
        base_dir = Path(os.getenv("CONTROL_PLANE_DATA_DIR", "runtime_data"))
        self.storage_mode = os.getenv("CONTROL_PLANE_STORAGE_MODE", "persistent")
        self.host = os.getenv("CONTROL_PLANE_HOST", "127.0.0.1")
        self.port = int(os.getenv("CONTROL_PLANE_PORT", "18080"))
        self.internal_token = os.getenv("CONTROL_PLANE_INTERNAL_TOKEN", "")
        self.bootstrap_admin_password = os.getenv("CONTROL_PLANE_ADMIN_PASSWORD", "")
        self.password_iterations = int(os.getenv("CONTROL_PLANE_PASSWORD_ITERATIONS", "120000"))
        self.timezone = os.getenv("CONTROL_PLANE_TIMEZONE", "Asia/Shanghai")
        self.deploy_mode, self.scheduler_enabled = resolve_deploy_mode(
            os.getenv("CONTROL_PLANE_DEPLOY_MODE"),
            os.getenv("CONTROL_PLANE_SCHEDULER_ENABLED"),
        )
        self.default_debug = _parse_bool(os.getenv("CONTROL_PLANE_DEBUG"), False)
        self.default_browser_strategy = os.getenv("CONTROL_PLANE_BROWSER_STRATEGY", "legacy")
        self.default_browser_enabled = _parse_bool(os.getenv("CONTROL_PLANE_BROWSER_ENABLED"), False)
        self.base_dir = base_dir
        self.db_path = base_dir / "control_plane.db"
        self.artifacts_dir = base_dir / "artifacts"
        self.storage_states_dir = base_dir / "storage-states"
        self.logs_dir = base_dir / "logs"
        self.screenshots_dir = base_dir / "screenshots"

    def default_system_config(self) -> dict[str, object]:
        return {
            "debug": self.default_debug,
            "browser_strategy": self.default_browser_strategy,
            "browser_enabled": self.default_browser_enabled,
            "admin_password_hash": "",
        }

    def ensure_directories(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.storage_states_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
