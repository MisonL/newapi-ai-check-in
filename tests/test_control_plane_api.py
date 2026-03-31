from __future__ import annotations

import time

from fastapi.testclient import TestClient

from control_plane.api.app import app
from control_plane.settings import settings


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

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        headers = {"x-internal-token": "test-token"}
        status_response = client.get("/api/status", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["storage_mode"] == "memory"
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
