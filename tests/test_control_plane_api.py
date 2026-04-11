from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from control_plane.api.app import app
from control_plane.security import hash_password
from control_plane.settings import resolve_deploy_mode, settings


def test_control_plane_api_roundtrip(tmp_path):
    settings.storage_mode = "memory"
    settings.base_dir = tmp_path
    settings.db_path = tmp_path / "control_plane.db"
    settings.artifacts_dir = tmp_path / "artifacts"
    settings.storage_states_dir = tmp_path / "storage-states"
    settings.logs_dir = tmp_path / "logs"
    settings.screenshots_dir = tmp_path / "screenshots"
    settings.internal_token = "test-token"
    settings.bootstrap_admin_password = "bootstrap-pass"
    settings.password_iterations = 120000
    settings.deploy_mode = "control_plane"
    settings.scheduler_enabled = True
    settings.default_debug = False
    settings.default_browser_strategy = "legacy"
    settings.default_browser_enabled = False

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        headers = {"x-internal-token": "test-token"}
        status_response = client.get("/api/status", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["storage_mode"] == "memory"
        assert status_response.json()["deploy_mode"] == "control_plane"
        assert status_response.json()["scheduler_enabled"] is True
        assert status_response.json()["admin_password_configured"] is False
        assert status_response.json()["bootstrap_password_enabled"] is True

        bootstrap_login = client.post("/api/system/login", json={"password": "bootstrap-pass"})
        assert bootstrap_login.status_code == 200
        assert bootstrap_login.json()["mode"] == "bootstrap"

        payload = {
            "domain": "system",
            "payload": {
                "debug": True,
                "browser_strategy": "legacy",
                "browser_enabled": False,
                "admin_password_hash": "",
            },
        }
        config_response = client.put("/api/config/system", json=payload, headers=headers)
        assert config_response.status_code == 200
        assert config_response.json()["payload"]["debug"] is True

        config_996 = client.put(
            "/api/config/checkin_996",
            json={"domain": "checkin_996", "payload": {"accounts": ["token-1"], "proxy": {"server": "http://proxy"}}},
            headers=headers,
        )
        assert config_996.status_code == 200
        assert config_996.json()["payload"]["accounts"] == ["token-1"]

        config_qaq = client.put(
            "/api/config/checkin_qaq_al",
            json={"domain": "checkin_qaq_al", "payload": {"accounts": ["sid-1"], "tier": 3}},
            headers=headers,
        )
        assert config_qaq.status_code == 200
        assert config_qaq.json()["payload"]["tier"] == 3

        config_linuxdo = client.put(
            "/api/config/linuxdo_read",
            json={
                "domain": "linuxdo_read",
                "payload": {
                    "accounts": [{"username": "alice", "password": "secret-pass"}],
                    "base_topic_id": 100001,
                    "max_posts": 120,
                },
            },
            headers=headers,
        )
        assert config_linuxdo.status_code == 200
        assert config_linuxdo.json()["payload"]["accounts"][0]["username"] == "alice"

        run_response = client.post("/api/jobs/linuxdo_read/run", headers=headers)
        assert run_response.status_code == 200
        run_id = run_response.json()["id"]
        assert run_response.json()["status"] == "queued"

        final_run = None
        for _ in range(100):
            current = client.get(f"/api/jobs/{run_id}", headers=headers)
            assert current.status_code == 200
            run_payload = current.json()
            if run_payload["finished_at"] is not None:
                final_run = run_payload
                break
            time.sleep(0.05)

        assert final_run is not None
        assert final_run["status"] == "failed"
        assert final_run["error_message"] == "Linux.do read requires browser support. Enable browser execution first."

        limited_jobs = client.get("/api/jobs?limit=1", headers=headers)
        assert limited_jobs.status_code == 200
        assert len(limited_jobs.json()) == 1
        assert limited_jobs.json()[0]["id"] == run_id

        schedules_response = client.get("/api/schedules", headers=headers)
        assert schedules_response.status_code == 200
        assert {item["job_type"] for item in schedules_response.json()} == {
            "main_checkin",
            "checkin_996",
            "checkin_qaq_al",
            "linuxdo_read",
        }

        schedule_payload = {
            "job_type": "main_checkin",
            "enabled": True,
            "cron": "*/10 * * * *",
            "timezone": "Asia/Shanghai",
            "cooldown_seconds": 300,
        }
        schedule_update = client.put("/api/schedules/main_checkin", json=schedule_payload, headers=headers)
        assert schedule_update.status_code == 200
        assert schedule_update.json()["cron"] == "*/10 * * * *"

        dashboard_response = client.get("/api/dashboard", headers=headers)
        assert dashboard_response.status_code == 200
        dashboard_payload = dashboard_response.json()
        assert dashboard_payload["status"]["storage_mode"] == "memory"
        assert dashboard_payload["total_runs"] == 1
        assert dashboard_payload["recent_runs"][0]["id"] == run_id
        assert dashboard_payload["metrics"]["enabled_schedule_count"] == 1
        assert dashboard_payload["metrics"]["last_failure_at"] is not None
        assert dashboard_payload["metrics"]["last_success_at"] is None
        assert dashboard_payload["metrics"]["consecutive_failures"] == 1
        assert dashboard_payload["next_runs"]["main_checkin"] is not None

        invalid_cron = client.put(
            "/api/schedules/main_checkin",
            json={**schedule_payload, "cron": "invalid-cron"},
            headers=headers,
        )
        assert invalid_cron.status_code == 422

        invalid_timezone = client.put(
            "/api/schedules/main_checkin",
            json={**schedule_payload, "timezone": "Mars/Olympus"},
            headers=headers,
        )
        assert invalid_timezone.status_code == 422

        stored_schedule = client.get("/api/schedules/main_checkin", headers=headers)
        assert stored_schedule.status_code == 200
        assert stored_schedule.json()["cron"] == "*/10 * * * *"
        assert stored_schedule.json()["timezone"] == "Asia/Shanghai"

        password_response = client.post("/api/system/admin-password", json={"password": "new-password-123"}, headers=headers)
        assert password_response.status_code == 200

        config_resave = client.put("/api/config/system", json=payload, headers=headers)
        assert config_resave.status_code == 200

        stored_login = client.post("/api/system/login", json={"password": "new-password-123"})
        assert stored_login.status_code == 200
        assert stored_login.json()["mode"] == "stored"

        old_login = client.post("/api/system/login", json={"password": "bootstrap-pass"})
        assert old_login.status_code == 401

        updated_status = client.get("/api/status", headers=headers)
        assert updated_status.status_code == 200
        assert updated_status.json()["admin_password_configured"] is True
        assert updated_status.json()["bootstrap_password_enabled"] is False


def test_login_rehashes_legacy_password_hash(tmp_path):
    settings.storage_mode = "memory"
    settings.base_dir = tmp_path
    settings.db_path = tmp_path / "control_plane.db"
    settings.artifacts_dir = tmp_path / "artifacts"
    settings.storage_states_dir = tmp_path / "storage-states"
    settings.logs_dir = tmp_path / "logs"
    settings.screenshots_dir = tmp_path / "screenshots"
    settings.internal_token = "test-token"
    settings.bootstrap_admin_password = ""
    settings.password_iterations = 120000
    settings.deploy_mode = "control_plane"
    settings.scheduler_enabled = True
    settings.default_debug = False
    settings.default_browser_strategy = "legacy"
    settings.default_browser_enabled = False

    with TestClient(app) as client:
        headers = {"x-internal-token": "test-token"}
        legacy_hash = hash_password("legacy-password", 390000)
        config_response = client.put(
            "/api/config/system",
            json={
                "domain": "system",
                "payload": {
                    "debug": False,
                    "browser_strategy": "legacy",
                    "browser_enabled": False,
                    "admin_password_hash": legacy_hash,
                },
            },
            headers=headers,
        )
        assert config_response.status_code == 200

        login_response = client.post("/api/system/login", json={"password": "legacy-password"})
        assert login_response.status_code == 200
        assert login_response.json()["mode"] == "stored"

        system_response = client.get("/api/config/system", headers=headers)
        assert system_response.status_code == 200
        stored_hash = system_response.json()["payload"]["admin_password_hash"]
        assert "$120000$" in stored_hash


def test_system_config_bootstrap_defaults_follow_environment(tmp_path):
    settings.storage_mode = "memory"
    settings.base_dir = tmp_path
    settings.db_path = tmp_path / "control_plane.db"
    settings.artifacts_dir = tmp_path / "artifacts"
    settings.storage_states_dir = tmp_path / "storage-states"
    settings.logs_dir = tmp_path / "logs"
    settings.screenshots_dir = tmp_path / "screenshots"
    settings.internal_token = "test-token"
    settings.bootstrap_admin_password = "bootstrap-pass"
    settings.password_iterations = 120000
    settings.deploy_mode = "control_plane"
    settings.scheduler_enabled = True
    settings.default_debug = True
    settings.default_browser_strategy = "http_only"
    settings.default_browser_enabled = True

    with TestClient(app) as client:
        headers = {"x-internal-token": "test-token"}
        response = client.get("/api/config/system", headers=headers)
        assert response.status_code == 200
        assert response.json()["payload"] == {
            "debug": True,
            "browser_strategy": "http_only",
            "browser_enabled": True,
            "admin_password_hash": "",
        }


def test_scheduler_can_be_disabled_from_environment(tmp_path):
    settings.storage_mode = "memory"
    settings.base_dir = tmp_path
    settings.db_path = tmp_path / "control_plane.db"
    settings.artifacts_dir = tmp_path / "artifacts"
    settings.storage_states_dir = tmp_path / "storage-states"
    settings.logs_dir = tmp_path / "logs"
    settings.screenshots_dir = tmp_path / "screenshots"
    settings.internal_token = "test-token"
    settings.bootstrap_admin_password = "bootstrap-pass"
    settings.password_iterations = 120000
    settings.deploy_mode = "github_actions"
    settings.scheduler_enabled = False
    settings.default_debug = False
    settings.default_browser_strategy = "legacy"
    settings.default_browser_enabled = False

    with TestClient(app) as client:
        headers = {"x-internal-token": "test-token"}
        schedule_update = client.put(
            "/api/schedules/main_checkin",
            json={
                "job_type": "main_checkin",
                "enabled": True,
                "cron": "*/10 * * * *",
                "timezone": "Asia/Shanghai",
                "cooldown_seconds": 0,
            },
            headers=headers,
        )
        assert schedule_update.status_code == 200

        status_response = client.get("/api/status", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["deploy_mode"] == "github_actions"
        assert status_response.json()["scheduler_enabled"] is False

        dashboard_response = client.get("/api/dashboard", headers=headers)
        assert dashboard_response.status_code == 200
        assert dashboard_response.json()["status"]["deploy_mode"] == "github_actions"
        assert dashboard_response.json()["next_runs"]["main_checkin"] is None


def test_resolve_deploy_mode_supports_both_modes():
    assert resolve_deploy_mode(None, None) == ("control_plane", True)
    assert resolve_deploy_mode("control_plane", None) == ("control_plane", True)
    assert resolve_deploy_mode("github_actions", None) == ("github_actions", False)
    assert resolve_deploy_mode(None, "false") == ("github_actions", False)


def test_resolve_deploy_mode_rejects_conflicting_values():
    with pytest.raises(ValueError, match="conflicts"):
        resolve_deploy_mode("github_actions", "true")

    with pytest.raises(ValueError, match="must be"):
        resolve_deploy_mode("invalid-mode", None)
