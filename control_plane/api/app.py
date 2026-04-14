from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

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
from control_plane.security import hash_password, password_needs_rehash, verify_password
from control_plane.services.app_state import AppState, build_app_state
from control_plane.settings import settings
from control_plane.task_center_models import AccountRecord, SiteRecord

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
    if not settings.internal_token:
        raise HTTPException(status_code=503, detail="Internal token is not configured")
    if x_internal_token != settings.internal_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_state() -> AppState:
    return state_holder["app_state"]


AppStateDep = Annotated[AppState, Depends(get_state)]


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
    app_state.job_service.bind_loop(asyncio.get_running_loop())
    app_state.scheduler_service.start()
    try:
        yield
    finally:
        app_state.scheduler_service.shutdown()


app = FastAPI(title="newapi ai check-in control plane", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status", dependencies=[Depends(require_internal_token)])
async def status(app_state: AppStateDep):
    return app_state.status()


@app.post("/api/system/login")
async def login(body: AdminLoginRequest, app_state: AppStateDep):
    system_config = SystemConfig.model_validate(app_state.storage.load_config(ConfigDomain.SYSTEM))
    if system_config.admin_password_hash:
        if not verify_password(body.password, system_config.admin_password_hash):
            raise HTTPException(status_code=401, detail="Invalid password")
        if password_needs_rehash(system_config.admin_password_hash, settings.password_iterations):
            updated = system_config.model_copy(
                update={"admin_password_hash": hash_password(body.password, settings.password_iterations)}
            )
            app_state.storage.save_config(ConfigDomain.SYSTEM, updated.model_dump())
        return {"authenticated": True, "mode": "stored"}
    bootstrap_password = settings.bootstrap_admin_password
    if not bootstrap_password:
        raise HTTPException(status_code=503, detail="Admin password is not configured")
    if body.password != bootstrap_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"authenticated": True, "mode": "bootstrap"}


@app.get("/api/config/{domain}", dependencies=[Depends(require_internal_token)])
async def get_config(domain: ConfigDomain, app_state: AppStateDep) -> ConfigEnvelope:
    return ConfigEnvelope(domain=domain, payload=app_state.storage.load_config(domain))


@app.put("/api/config/{domain}", dependencies=[Depends(require_internal_token)])
async def put_config(domain: ConfigDomain, envelope: ConfigEnvelope, app_state: AppStateDep) -> ConfigEnvelope:
    if envelope.domain != domain:
        raise HTTPException(status_code=400, detail="Domain mismatch")
    current_payload = app_state.storage.load_config(domain)
    app_state.storage.save_config(domain, normalize_config(domain, envelope.payload, current_payload))
    return ConfigEnvelope(domain=domain, payload=app_state.storage.load_config(domain))


@app.post("/api/system/admin-password", dependencies=[Depends(require_internal_token)])
async def update_admin_password(body: AdminPasswordUpdateRequest, app_state: AppStateDep):
    system_config = SystemConfig.model_validate(app_state.storage.load_config(ConfigDomain.SYSTEM))
    updated = system_config.model_copy(update={"admin_password_hash": hash_password(body.password, settings.password_iterations)})
    app_state.storage.save_config(ConfigDomain.SYSTEM, updated.model_dump())
    return {"updated": True}


@app.get("/api/dashboard", dependencies=[Depends(require_internal_token)])
async def dashboard(app_state: AppStateDep):
    return app_state.dashboard()


@app.get("/api/task-center/summary", dependencies=[Depends(require_internal_token)])
async def task_center_summary(app_state: AppStateDep):
    return app_state.task_center_service.summary()


@app.get("/api/task-center/today", dependencies=[Depends(require_internal_token)])
async def task_center_today(app_state: AppStateDep, task_date: date | None = None):
    return app_state.task_center_service.today(task_date)


@app.get("/api/task-center/incidents", dependencies=[Depends(require_internal_token)])
async def task_center_incidents(app_state: AppStateDep, resolved: bool | None = None):
    return app_state.task_center_service.incidents(resolved)


@app.get("/api/task-center/reports", dependencies=[Depends(require_internal_token)])
async def task_center_reports(app_state: AppStateDep, date_from: date | None = None, date_to: date | None = None):
    return app_state.task_center_service.reports(date_from, date_to)


@app.post("/api/task-center/imports/main-checkin", dependencies=[Depends(require_internal_token)])
async def import_main_checkin(app_state: AppStateDep):
    return app_state.task_center_service.import_from_main_checkin_config()


@app.post("/api/task-center/tasks/generate-today", dependencies=[Depends(require_internal_token)])
async def generate_today_tasks(app_state: AppStateDep, task_date: date | None = None):
    return app_state.task_center_service.generate_today_tasks(task_date)


@app.post("/api/task-center/tasks/{task_id}/retry", dependencies=[Depends(require_internal_token)])
async def retry_task(task_id: str, app_state: AppStateDep):
    try:
        return app_state.task_center_service.retry_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@app.post("/api/task-center/tasks/execute-today", dependencies=[Depends(require_internal_token)])
async def execute_today_tasks(app_state: AppStateDep, task_date: date | None = None):
    return await app_state.task_center_service.execute_today_tasks(task_date)


@app.post("/api/task-center/tasks/{task_id}/execute", dependencies=[Depends(require_internal_token)])
async def execute_task(task_id: str, app_state: AppStateDep):
    try:
        return await app_state.task_center_service.execute_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@app.get("/api/sites", dependencies=[Depends(require_internal_token)])
async def list_sites(app_state: AppStateDep):
    return app_state.task_center_service.list_sites()


@app.post("/api/sites", dependencies=[Depends(require_internal_token)])
async def create_site(site: SiteRecord, app_state: AppStateDep):
    try:
        return app_state.task_center_service.save_site(site)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.put("/api/sites/{site_id}", dependencies=[Depends(require_internal_token)])
async def update_site(site_id: str, site: SiteRecord, app_state: AppStateDep):
    if site.id != site_id:
        raise HTTPException(status_code=400, detail="Site id mismatch")
    try:
        return app_state.task_center_service.save_site(site)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/accounts", dependencies=[Depends(require_internal_token)])
async def list_accounts(app_state: AppStateDep, site_id: str | None = None):
    return app_state.task_center_service.list_accounts(site_id)


@app.post("/api/accounts", dependencies=[Depends(require_internal_token)])
async def create_account(account: AccountRecord, app_state: AppStateDep):
    if app_state.storage.get_site(account.site_id) is None:
        raise HTTPException(status_code=400, detail="Site not found")
    try:
        return app_state.task_center_service.save_account(account)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.put("/api/accounts/{account_id}", dependencies=[Depends(require_internal_token)])
async def update_account(account_id: str, account: AccountRecord, app_state: AppStateDep):
    if account.id != account_id:
        raise HTTPException(status_code=400, detail="Account id mismatch")
    if app_state.storage.get_site(account.site_id) is None:
        raise HTTPException(status_code=400, detail="Site not found")
    try:
        return app_state.task_center_service.save_account(account)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/jobs", dependencies=[Depends(require_internal_token)])
async def list_jobs(app_state: AppStateDep, job_type: JobType | None = None, limit: int | None = None):
    normalized_limit = max(limit, 1) if limit is not None else None
    return app_state.storage.list_job_runs(job_type, normalized_limit)


@app.get("/api/jobs/{run_id}", dependencies=[Depends(require_internal_token)])
async def get_job(run_id: str, app_state: AppStateDep):
    run = app_state.storage.get_job_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Job run not found")
    return run


@app.get("/api/jobs/{run_id}/logs", dependencies=[Depends(require_internal_token)])
async def get_job_logs(run_id: str, app_state: AppStateDep):
    return app_state.storage.get_job_logs(run_id)


@app.post("/api/jobs/{job_type}/run", dependencies=[Depends(require_internal_token)])
async def run_job(job_type: JobType, app_state: AppStateDep):
    return app_state.job_service.start_job(job_type, TriggerType.MANUAL)


@app.get("/api/schedules", dependencies=[Depends(require_internal_token)])
async def list_schedules(app_state: AppStateDep):
    return app_state.storage.list_schedules()


@app.get("/api/schedules/{job_type}", dependencies=[Depends(require_internal_token)])
async def get_schedule(job_type: JobType, app_state: AppStateDep):
    return app_state.storage.load_schedule(job_type)


@app.put("/api/schedules/{job_type}", dependencies=[Depends(require_internal_token)])
async def put_schedule(job_type: JobType, schedule: ScheduleSpec, app_state: AppStateDep):
    if schedule.job_type != job_type:
        raise HTTPException(status_code=400, detail="Job type mismatch")
    app_state.storage.save_schedule(schedule)
    app_state.scheduler_service.sync()
    return app_state.storage.load_schedule(job_type)
