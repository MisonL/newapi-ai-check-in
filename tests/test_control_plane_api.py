from __future__ import annotations

import time
from datetime import date

import pytest
from fastapi.testclient import TestClient

from control_plane.api.app import app, state_holder
from control_plane.security import hash_password
from control_plane.settings import resolve_deploy_mode, settings
from control_plane.task_center_models import CheckinResultRecord, IncidentRecord


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

        site_response = client.post(
            "/api/sites",
            json={"name": "Primary Site", "base_url": "https://example.com", "enabled": True},
            headers=headers,
        )
        assert site_response.status_code == 200
        site_id = site_response.json()["id"]

        account_response = client.post(
            "/api/accounts",
            json={
                "site_id": site_id,
                "display_name": "Alice",
                "username": "alice",
                "password": "secret-pass",
                "enabled": True,
            },
            headers=headers,
        )
        assert account_response.status_code == 200
        account_id = account_response.json()["id"]

        account_update = client.put(
            f"/api/accounts/{account_id}",
            json={
                **account_response.json(),
                "last_checkin_status": "failed",
                "last_error_message": "Login failed",
            },
            headers=headers,
        )
        assert account_update.status_code == 200

        summary_response = client.get("/api/task-center/summary", headers=headers)
        assert summary_response.status_code == 200
        summary_payload = summary_response.json()
        assert summary_payload["today"]["total_sites"] == 1
        assert summary_payload["today"]["enabled_accounts"] == 1
        assert summary_payload["recent_incidents"][0]["display_name"] == "Alice"

        generation_response = client.post("/api/task-center/tasks/generate-today", headers=headers)
        assert generation_response.status_code == 200
        generated_payload = generation_response.json()
        assert generated_payload["total_accounts"] == 1
        assert generated_payload["created_count"] == 1

        today_response = client.get("/api/task-center/today", headers=headers)
        assert today_response.status_code == 200
        today_payload = today_response.json()
        assert today_payload["total_tasks"] == 1
        assert today_payload["tasks"][0]["auth_mode"] == "password"
        task_id = today_payload["tasks"][0]["id"]

        app_state = state_holder["app_state"]
        task = app_state.storage.get_daily_task(task_id)
        assert task is not None
        updated_task = task.model_copy(
            update={
                "status": "failed",
                "error_code": "login_failed",
                "error_message": "Login failed",
            }
        )
        app_state.storage.save_daily_task(updated_task)
        app_state.storage.save_checkin_result(
            CheckinResultRecord(
                task_id=task_id,
                site_id=site_id,
                account_id=account_id,
                checked_in_today_before_run=False,
                quota_awarded=888,
                checkin_date=date.today(),
                total_checkins=3,
                total_quota_awarded=1888,
            )
        )
        app_state.storage.save_incident(
            IncidentRecord(
                task_id=task_id,
                account_id=account_id,
                site_id=site_id,
                display_name="Alice",
                site_name="Primary Site",
                status="failed",
                last_error_message="Login failed",
                type="login_failed",
            )
        )

        incidents_response = client.get("/api/task-center/incidents", headers=headers)
        assert incidents_response.status_code == 200
        assert incidents_response.json()[0]["type"] == "login_failed"

        reports_response = client.get("/api/task-center/reports", headers=headers)
        assert reports_response.status_code == 200
        assert reports_response.json()["days"][-1]["total_tasks"] == 1
        assert reports_response.json()["sites"][0]["site_name"] == "Primary Site"

        retry_response = client.post(f"/api/task-center/tasks/{task_id}/retry", headers=headers)
        assert retry_response.status_code == 200
        assert retry_response.json()["status"] == "pending"
        assert retry_response.json()["attempt_count"] == 1

        payload = {
            "domain": "system",
            "payload": {
                "debug": True,
                "browser_strategy": "legacy",
                "browser_enabled": False,
                "main_checkin_engine": "legacy",
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
                    "main_checkin_engine": "legacy",
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
            "main_checkin_engine": "legacy",
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


def test_main_checkin_import_creates_sites_and_skips_non_password_accounts(tmp_path):
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
        headers = {"x-internal-token": "test-token"}
        config_response = client.put(
            "/api/config/main_checkin",
            json={
                "domain": "main_checkin",
                "payload": {
                    "providers": {
                        "custom-provider": {
                            "origin": "https://custom.example.com",
                            "check_in_path": "/api/user/checkin",
                            "check_in_status": True,
                        }
                    },
                    "accounts": [
                        {
                            "provider": "anyrouter",
                            "name": "Cookie Account",
                            "cookies": {"session": "abc"},
                            "api_user": "user-1",
                        },
                        {
                            "provider": "custom-provider",
                            "name": "OAuth Account",
                            "github": {"username": "oauth-user", "password": "oauth-pass"},
                        },
                        {
                            "provider": "custom-provider",
                            "name": "Global OAuth Account",
                            "linux.do": True,
                        },
                        {
                            "provider": "custom-provider",
                            "name": "Imported Account",
                            "username": "alice",
                            "password": "secret-pass",
                        },
                    ],
                    "accounts_linux_do": [
                        {"username": "linuxdo-user", "password": "linuxdo-pass"},
                    ],
                },
            },
            headers=headers,
        )
        assert config_response.status_code == 200

        import_response = client.post("/api/task-center/imports/main-checkin", headers=headers)
        assert import_response.status_code == 200
        payload = import_response.json()
        assert payload["created_sites"] == 2
        assert payload["created_accounts"] == 4
        assert payload["skipped_accounts"] == 0

        sites_response = client.get("/api/sites", headers=headers)
        assert sites_response.status_code == 200
        sites = {item["name"]: item for item in sites_response.json()}
        assert sites["anyrouter"]["base_url"] == "https://anyrouter.top"
        assert sites["custom-provider"]["base_url"] == "https://custom.example.com"
        assert sites["custom-provider"]["compatibility_level"] == "standard"

        accounts_response = client.get("/api/accounts", headers=headers)
        assert accounts_response.status_code == 200
        accounts = accounts_response.json()
        assert len(accounts) == 4
        imported_accounts = {item["display_name"]: item for item in accounts}
        assert imported_accounts["Imported Account"]["username"] == "alice"
        assert imported_accounts["Cookie Account"]["auth_mode"] == "cookies"
        assert imported_accounts["Cookie Account"]["api_user"] == "user-1"
        assert imported_accounts["OAuth Account [github:oauth-user]"]["auth_mode"] == "github_oauth"
        assert imported_accounts["Global OAuth Account [linux.do:linuxdo-user]"]["auth_mode"] == "linuxdo_oauth"


def test_account_api_supports_cookie_and_oauth_auth_modes(tmp_path):
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
        headers = {"x-internal-token": "test-token"}
        site_id = client.post(
            "/api/sites",
            json={"name": "Primary Site", "base_url": "https://example.com", "enabled": True},
            headers=headers,
        ).json()["id"]

        cookie_response = client.post(
            "/api/accounts",
            json={
                "site_id": site_id,
                "display_name": "Cookie Session",
                "username": "cookie-user-1",
                "auth_mode": "cookies",
                "api_user": "user-1",
                "session_cookies": {"session": "abc"},
                "enabled": True,
            },
            headers=headers,
        )
        assert cookie_response.status_code == 200

        oauth_response = client.post(
            "/api/accounts",
            json={
                "site_id": site_id,
                "display_name": "GitHub OAuth",
                "username": "oauth-user",
                "auth_mode": "github_oauth",
                "password": "oauth-pass",
                "enabled": True,
            },
            headers=headers,
        )
        assert oauth_response.status_code == 200

        accounts_response = client.get("/api/accounts", headers=headers)
        assert accounts_response.status_code == 200
        accounts = {item["display_name"]: item for item in accounts_response.json()}
        assert accounts["Cookie Session"]["auth_mode"] == "cookies"
        assert accounts["Cookie Session"]["api_user"] == "user-1"
        assert accounts["Cookie Session"]["session_cookies"]["session"] == "abc"
        assert accounts["GitHub OAuth"]["auth_mode"] == "github_oauth"
        assert accounts["GitHub OAuth"]["username"] == "oauth-user"


def test_task_execute_endpoint_runs_task(monkeypatch, tmp_path):
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

    class FakeExecutor:
        def __init__(self, storage) -> None:
            self._storage = storage

        async def execute_task(self, task_id: str):
            task = self._storage.get_daily_task(task_id)
            updated = task.model_copy(update={'status': 'success'}) if task is not None else None
            if updated is None:
                raise KeyError(task_id)
            self._storage.save_daily_task(updated)
            return updated

    monkeypatch.setattr(
        'control_plane.services.task_center_service.build_task_center_executor',
        lambda storage: FakeExecutor(storage),
    )

    with TestClient(app) as client:
        headers = {"x-internal-token": "test-token"}
        site_id = client.post(
            "/api/sites",
            json={"name": "Primary Site", "base_url": "https://example.com", "enabled": True},
            headers=headers,
        ).json()["id"]
        account_id = client.post(
            "/api/accounts",
            json={
                "site_id": site_id,
                "display_name": "Alice",
                "username": "alice",
                "password": "secret-pass",
                "enabled": True,
            },
            headers=headers,
        ).json()["id"]
        app_state = state_holder["app_state"]
        generation = app_state.task_center_service.generate_today_tasks()
        assert generation.created_count == 1
        today = app_state.task_center_service.today()
        task_id = today.tasks[0].id

        response = client.post(f"/api/task-center/tasks/{task_id}/execute", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert app_state.storage.get_account(account_id) is not None


def test_execute_today_tasks_endpoint_runs_pending_tasks(monkeypatch, tmp_path):
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

    class FakeExecutor:
        def __init__(self, storage) -> None:
            self._storage = storage

        async def execute_task(self, task_id: str):
            task = self._storage.get_daily_task(task_id)
            if task is None:
                raise KeyError(task_id)
            account = self._storage.get_account(task.account_id)
            status = 'success' if account is not None and account.username == 'u1' else 'blocked'
            updated = task.model_copy(update={'status': status})
            self._storage.save_daily_task(updated)
            return updated

    monkeypatch.setattr(
        'control_plane.services.task_center_service.build_task_center_executor',
        lambda storage: FakeExecutor(storage),
    )

    with TestClient(app) as client:
        headers = {"x-internal-token": "test-token"}
        first_site = client.post(
            "/api/sites",
            json={"name": "Site 1", "base_url": "https://one.example.com", "enabled": True},
            headers=headers,
        ).json()["id"]
        second_site = client.post(
            "/api/sites",
            json={"name": "Site 2", "base_url": "https://two.example.com", "enabled": True},
            headers=headers,
        ).json()["id"]
        client.post(
            "/api/accounts",
            json={"site_id": first_site, "display_name": "A1", "username": "u1", "password": "p1", "enabled": True},
            headers=headers,
        )
        client.post(
            "/api/accounts",
            json={"site_id": second_site, "display_name": "A2", "username": "u2", "password": "p2", "enabled": True},
            headers=headers,
        )
        generation = client.post("/api/task-center/tasks/generate-today", headers=headers)
        assert generation.status_code == 200

        response = client.post("/api/task-center/tasks/execute-today", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["total_selected"] == 2
        assert payload["executed_count"] == 2
        assert payload["success_count"] == 1
        assert payload["blocked_count"] == 1


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
