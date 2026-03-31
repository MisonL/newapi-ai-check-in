from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException

from control_plane.models import (
    AdminLoginRequest,
    AdminPasswordUpdateRequest,
    Checkin996Config,
    CheckinQaqAlConfig,
    ConfigDomain,
    ConfigEnvelope,
    JobType,
    LinuxDoReadConfig,
    MainCheckinConfig,
    NotificationConfig,
    ScheduleSpec,
    SystemConfig,
    TriggerType,
)
from control_plane.security import hash_password, verify_password
from control_plane.services.app_state import AppState, build_app_state
from control_plane.settings import settings


state_holder: dict[str, AppState] = {}
CONFIG_MODELS = {
    ConfigDomain.SYSTEM: SystemConfig,
    ConfigDomain.MAIN_CHECKIN: MainCheckinConfig,
    ConfigDomain.CHECKIN_996: Checkin996Config,
    ConfigDomain.CHECKIN_QAQ_AL: CheckinQaqAlConfig,
    ConfigDomain.LINUXDO_READ: LinuxDoReadConfig,
    ConfigDomain.NOTIFICATIONS: NotificationConfig,
}


def require_internal_token(x_internal_token: str = Header(default="")) -> None:
    if x_internal_token != settings.internal_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_state() -> AppState:
    return state_holder["app_state"]


def normalize_config(domain: ConfigDomain, payload: dict, current_payload: dict) -> dict:
    merged_payload = {**current_payload, **payload}
    if domain == ConfigDomain.SYSTEM:
        if current_payload.get("admin_password_hash") and not payload.get("admin_password_hash"):
            merged_payload["admin_password_hash"] = current_payload["admin_password_hash"]
    return CONFIG_MODELS[domain].model_validate(merged_payload).model_dump()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_state = build_app_state()
    state_holder["app_state"] = app_state
    app_state.scheduler_service.start()
    try:
        yield
    finally:
        app_state.scheduler_service.shutdown()


app = FastAPI(title="newapi ai check-in control plane", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status", dependencies=[Depends(require_internal_token)])
def status(app_state: AppState = Depends(get_state)):
    return app_state.status()


@app.post("/api/system/login")
def login(body: AdminLoginRequest, app_state: AppState = Depends(get_state)):
    system_config = SystemConfig.model_validate(app_state.storage.load_config(ConfigDomain.SYSTEM))
    if system_config.admin_password_hash:
        if not verify_password(body.password, system_config.admin_password_hash):
            raise HTTPException(status_code=401, detail="Invalid password")
        return {"authenticated": True, "mode": "stored"}
    bootstrap_password = settings.bootstrap_admin_password
    if not bootstrap_password:
        raise HTTPException(status_code=503, detail="Admin password is not configured")
    if body.password != bootstrap_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"authenticated": True, "mode": "bootstrap"}


@app.get("/api/config/{domain}", dependencies=[Depends(require_internal_token)])
def get_config(domain: ConfigDomain, app_state: AppState = Depends(get_state)) -> ConfigEnvelope:
    return ConfigEnvelope(domain=domain, payload=app_state.storage.load_config(domain))


@app.put("/api/config/{domain}", dependencies=[Depends(require_internal_token)])
def put_config(domain: ConfigDomain, envelope: ConfigEnvelope, app_state: AppState = Depends(get_state)) -> ConfigEnvelope:
    if envelope.domain != domain:
        raise HTTPException(status_code=400, detail="Domain mismatch")
    current_payload = app_state.storage.load_config(domain)
    app_state.storage.save_config(domain, normalize_config(domain, envelope.payload, current_payload))
    return ConfigEnvelope(domain=domain, payload=app_state.storage.load_config(domain))


@app.post("/api/system/admin-password", dependencies=[Depends(require_internal_token)])
def update_admin_password(body: AdminPasswordUpdateRequest, app_state: AppState = Depends(get_state)):
    system_config = SystemConfig.model_validate(app_state.storage.load_config(ConfigDomain.SYSTEM))
    updated = system_config.model_copy(update={"admin_password_hash": hash_password(body.password)})
    app_state.storage.save_config(ConfigDomain.SYSTEM, updated.model_dump())
    return {"updated": True}


@app.get("/api/jobs", dependencies=[Depends(require_internal_token)])
def list_jobs(job_type: JobType | None = None, app_state: AppState = Depends(get_state)):
    return app_state.storage.list_job_runs(job_type)


@app.get("/api/jobs/{run_id}", dependencies=[Depends(require_internal_token)])
def get_job(run_id: str, app_state: AppState = Depends(get_state)):
    run = app_state.storage.get_job_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Job run not found")
    return run


@app.get("/api/jobs/{run_id}/logs", dependencies=[Depends(require_internal_token)])
def get_job_logs(run_id: str, app_state: AppState = Depends(get_state)):
    return app_state.storage.get_job_logs(run_id)


@app.post("/api/jobs/{job_type}/run", dependencies=[Depends(require_internal_token)])
def run_job(job_type: JobType, app_state: AppState = Depends(get_state)):
    return app_state.job_service.start_job(job_type, TriggerType.MANUAL)


@app.get("/api/schedules", dependencies=[Depends(require_internal_token)])
def list_schedules(app_state: AppState = Depends(get_state)):
    return app_state.storage.list_schedules()


@app.get("/api/schedules/{job_type}", dependencies=[Depends(require_internal_token)])
def get_schedule(job_type: JobType, app_state: AppState = Depends(get_state)):
    return app_state.storage.load_schedule(job_type)


@app.put("/api/schedules/{job_type}", dependencies=[Depends(require_internal_token)])
def put_schedule(job_type: JobType, schedule: ScheduleSpec, app_state: AppState = Depends(get_state)):
    if schedule.job_type != job_type:
        raise HTTPException(status_code=400, detail="Job type mismatch")
    app_state.storage.save_schedule(schedule)
    app_state.scheduler_service.sync()
    return app_state.storage.load_schedule(job_type)
