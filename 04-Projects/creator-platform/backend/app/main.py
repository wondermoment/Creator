"""Local-only Creator MVP. No live patient data or production authentication yet."""
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from . import commerce, book_chat, coach_chat, shop_experience, art_studio, courses

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get("CREATOR_RUNTIME", str(ROOT.parent / ".runtime")))
WEB = ROOT.parent / "frontend"
METRICS = {
    "hrv": {"label": "心率变异性", "unit": "ms", "min": 1, "max": 300},
    "sleep": {"label": "睡眠时长", "unit": "h", "min": 0, "max": 24},
    "weight": {"label": "体重", "unit": "kg", "min": 10, "max": 400},
    "body_fat": {"label": "体脂率", "unit": "%", "min": 1, "max": 80},
    "heart_rate": {"label": "静息心率", "unit": "bpm", "min": 20, "max": 250},
    "spo2": {"label": "血氧饱和度", "unit": "%", "min": 50, "max": 100},
}


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def db():
    conn = sqlite3.connect(RUNTIME / "creator.db", timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def event(conn, patient_id, kind, payload):
    conn.execute("INSERT INTO events VALUES (?,?,?,?,?)", (str(uuid.uuid4()), patient_id, kind, json.dumps(payload, ensure_ascii=False), now()))


def initialize():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS patients(id TEXT PRIMARY KEY,name TEXT NOT NULL,age INTEGER,source TEXT,channel TEXT,consultant TEXT,goal TEXT);
        CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY,patient_id TEXT REFERENCES patients(id),metric TEXT,value REAL,unit TEXT,source TEXT,observed_at TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS recommendations(id TEXT PRIMARY KEY,patient_id TEXT REFERENCES patients(id),title TEXT,evidence TEXT,status TEXT DEFAULT 'pending',reason TEXT,created_at TEXT, UNIQUE(patient_id,evidence));
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,patient_id TEXT REFERENCES patients(id),recommendation_id TEXT UNIQUE REFERENCES recommendations(id),title TEXT,status TEXT DEFAULT 'open',review TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,patient_id TEXT REFERENCES patients(id),name TEXT,mime TEXT,data BLOB,status TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,patient_id TEXT REFERENCES patients(id),kind TEXT,payload TEXT,created_at TEXT);
        CREATE INDEX IF NOT EXISTS observation_timeline ON observations(patient_id,metric,observed_at);
        ''')
        if c.execute("SELECT count(*) FROM patients").fetchone()[0]:
            return
        c.executemany("INSERT INTO patients VALUES (?,?,?,?,?,?,?)", [
            ("p1", "林女士", 38, "视频号 · 睡眠专题直播", "企业微信", "陈悦", "改善睡眠，建立稳定的生活节律"),
            ("p2", "周先生", 45, "小红书 · 体重管理图文", "个人微信", "陈悦", "持续记录体重与活动情况"),
            ("p3", "许女士", 32, "知识课程 · 老客转介绍", "飞书", "李晴", "建立个人健康基线"),
        ])
        for p in range(1, 4):
            for day in range(14):
                values = {"hrv": 52 + ((day * 7 + p) % 13) - (16 if day > 10 and p == 1 else 0), "sleep": round(7.1 + ((day + p) % 4) * .2 - (1.3 if day > 10 and p == 1 else 0), 1), "weight": round(64 + p * 3 - day * .08, 1), "body_fat": round(25 + p - day * .06, 1), "heart_rate": 61 + (day + p) % 5, "spo2": 97 + day % 3}
                at = (datetime.now(timezone.utc) - timedelta(days=13-day, hours=1)).isoformat()
                for metric, value in values.items():
                    source = "体脂秤 · 示例" if metric in ("weight", "body_fat") else "智能戒指 · 示例"
                    c.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), f"p{p}", metric, value, METRICS[metric]["unit"], source, at, now()))
        c.execute("INSERT INTO recommendations VALUES (?,?,?,?,?,?,?)", ("r1", "p1", "了解近期睡眠与恢复情况", "示例数据中最近三晚睡眠均不足 7 小时；请先确认佩戴完整性和主观感受。", "pending", "", now()))
        c.execute("INSERT INTO recommendations VALUES (?,?,?,?,?,?,?)", ("r2", "p2", "安排本周健康数据复盘", "已积累 14 天体重记录，可与客户一起核对目标和测量条件。", "pending", "", now()))


@asynccontextmanager
async def lifespan(app):
    initialize()
    commerce.initialize(db)
    shop_experience.initialize()
    courses.initialize()
    art_studio.initialize()
    yield


app = FastAPI(title="Creator 智能流 · 本地演示 API", version="0.1.0", lifespan=lifespan, dependencies=[Depends(commerce.local_only)])
@app.middleware("http")
async def private_api_responses(request, call_next):
    response = await call_next(request)
    if request.url.path == "/api" or request.url.path.startswith("/api/"):
        # API payloads can contain health records, conversations or uploaded reports.
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
    return response


app.include_router(commerce.router)
app.include_router(shop_experience.router)
app.include_router(courses.router)
app.include_router(art_studio.router)
app.include_router(book_chat.router)
app.include_router(coach_chat.router)


def patient(c, patient_id):
    row = c.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    if not row:
        raise HTTPException(404, "客户不存在")
    return dict(row)


@app.get("/api/overview")
def overview():
    with db() as c:
        return {"mode": "local_demo", "patients": [dict(r) for r in c.execute("SELECT * FROM patients")], "recommendations": [dict(r) for r in c.execute("SELECT * FROM recommendations ORDER BY created_at DESC")], "tasks": [dict(r) for r in c.execute("SELECT * FROM tasks ORDER BY created_at DESC")], "metrics": METRICS}


@app.get("/api/patients/{patient_id}")
def detail(patient_id: str):
    with db() as c:
        return {"patient": patient(c, patient_id), "observations": [dict(r) for r in c.execute("SELECT * FROM observations WHERE patient_id=? ORDER BY observed_at", (patient_id,))], "reports": [dict(r) for r in c.execute("SELECT id,name,status,created_at FROM reports WHERE patient_id=? ORDER BY created_at DESC", (patient_id,))], "events": [dict(r) for r in c.execute("SELECT * FROM events WHERE patient_id=? ORDER BY created_at DESC LIMIT 30", (patient_id,))]}


class Observation(BaseModel):
    metric: Literal["hrv", "sleep", "weight", "body_fat", "heart_rate", "spo2"]
    value: float = Field(allow_inf_nan=False)
    source: Literal["手动录入", "智能戒指", "智能手表", "体脂秤", "体检报告"]
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def valid_time(cls, v):
        if v.tzinfo is None:
            raise ValueError("请提供带时区的测量时间")
        if v > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("测量时间不能在未来")
        return v.astimezone(timezone.utc)


@app.post("/api/patients/{patient_id}/observations", status_code=201)
def add_observation(patient_id: str, body: Observation):
    meta = METRICS[body.metric]
    if not meta["min"] <= body.value <= meta["max"]:
        raise HTTPException(422, f"{meta['label']}应在 {meta['min']}–{meta['max']} {meta['unit']} 之间，请核对单位")
    oid = str(uuid.uuid4())
    with db() as c:
        patient(c, patient_id)
        c.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?)", (oid, patient_id, body.metric, body.value, meta["unit"], body.source, body.observed_at.isoformat(), now()))
        event(c, patient_id, "observation.recorded", {"observation_id": oid, **body.model_dump(mode="json")})
    return {"id": oid}


@app.post("/api/patients/{patient_id}/review")
def propose_review(patient_id: str):
    with db() as c:
        patient(c, patient_id)
        latest = c.execute("SELECT * FROM observations WHERE patient_id=? ORDER BY observed_at DESC,created_at DESC LIMIT 1", (patient_id,)).fetchone()
        if not latest:
            raise HTTPException(409, "先录入一条健康数据")
        evidence = f"数据记录 {latest['id']}：{METRICS[latest['metric']]['label']} {latest['value']} {latest['unit']}，来源 {latest['source']}，时间 {latest['observed_at']}。请结合基线、测量条件和客户反馈复核。"
        existing = c.execute("SELECT id FROM recommendations WHERE patient_id=? AND evidence=?", (patient_id, evidence)).fetchone()
        if existing:
            return {"id": existing[0], "created": False}
        rid = str(uuid.uuid4())
        c.execute("INSERT INTO recommendations VALUES (?,?,?,?,?,?,?)", (rid, patient_id, "复核最新健康记录", evidence, "pending", "", now()))
        event(c, patient_id, "recommendation.proposed", {"id": rid, "engine": "rule-v1"})
    return {"id": rid, "created": True}


class Decision(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=2, max_length=1000)

    @field_validator("reason")
    @classmethod
    def not_blank(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("请填写至少两个字的复核说明")
        return v.strip()


@app.post("/api/recommendations/{recommendation_id}/decision")
def decide(recommendation_id: str, body: Decision):
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        r = c.execute("SELECT * FROM recommendations WHERE id=?", (recommendation_id,)).fetchone()
        if not r:
            raise HTTPException(404, "建议不存在")
        if r["status"] != "pending":
            raise HTTPException(409, "该建议已处理，请刷新")
        c.execute("UPDATE recommendations SET status=?,reason=? WHERE id=?", (body.decision, body.reason, recommendation_id))
        if body.decision == "approved":
            c.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), r["patient_id"], recommendation_id, r["title"], "open", "", now()))
        event(c, r["patient_id"], "recommendation." + body.decision, {"id": recommendation_id, "reason": body.reason, "actor": "demo-consultant"})
    return {"status": body.decision}


class Review(BaseModel):
    review: str = Field(min_length=2, max_length=2000)

    @field_validator("review")
    @classmethod
    def not_blank(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("请填写至少两个字的复盘记录")
        return v.strip()


@app.post("/api/tasks/{task_id}/complete")
def complete(task_id: str, body: Review):
    with db() as c:
        c.execute("BEGIN IMMEDIATE")
        task = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not task:
            raise HTTPException(404, "任务不存在")
        if task["status"] != "open":
            raise HTTPException(409, "任务已完成")
        c.execute("UPDATE tasks SET status='done',review=? WHERE id=?", (body.review, task_id))
        event(c, task["patient_id"], "task.completed", {"id": task_id, "review": body.review})
    return {"status": "done"}


@app.post("/api/patients/{patient_id}/reports", status_code=201)
async def upload_report(patient_id: str, file: UploadFile = File(...)):
    data = await file.read(10 * 1024 * 1024 + 1)
    await file.close()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "文件请控制在 10 MB 内")
    mime = "application/pdf" if data.startswith(b"%PDF-") else "image/png" if data.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg" if data.startswith(b"\xff\xd8\xff") else None
    if not mime:
        raise HTTPException(422, "仅支持 PDF、PNG、JPEG 文件")
    rid = str(uuid.uuid4())
    name = (file.filename or "健康报告").replace("\\", "/").split("/")[-1][:150]
    with db() as c:
        patient(c, patient_id)
        c.execute("INSERT INTO reports VALUES (?,?,?,?,?,?,?)", (rid, patient_id, name, mime, data, "待人工解读", now()))
        event(c, patient_id, "report.uploaded", {"id": rid, "name": name})
    return {"id": rid, "status": "待人工解读"}


@app.get("/api/reports/{report_id}")
def download_report(report_id: str):
    from fastapi.responses import Response
    with db() as c:
        r = c.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        if not r:
            raise HTTPException(404, "报告不存在")
        return Response(r["data"], media_type=r["mime"], headers={"Content-Disposition": "attachment; filename=report." + {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}[r["mime"]], "X-Content-Type-Options": "nosniff"})


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
