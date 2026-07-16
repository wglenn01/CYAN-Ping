import os
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from auth import (verify_password, create_token, get_current_user)
import scheduler
import mtr as mtr_engine
import mtr_live

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="CyanPing API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("cyanping")

RANGES = {
    "3h": (3 * 3600, 108),
    "30h": (30 * 3600, 180),
    "10d": (10 * 86400, 240),
    "360d": (360 * 86400, 360),
}


# ---------- Models ----------
class LoginIn(BaseModel):
    username: str
    password: str


class TargetIn(BaseModel):
    name: str
    host: str
    probe: str = "ICMP"
    interval: float = 60
    group_id: str


class TargetUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    probe: Optional[str] = None
    interval: Optional[float] = None
    group_id: Optional[str] = None
    enabled: Optional[bool] = None


MIN_INTERVAL = 0.25


class GroupIn(BaseModel):
    name: str


class RuleUpdate(BaseModel):
    enabled: bool


class MtrToolIn(BaseModel):
    host: str


# ---------- Helpers ----------
def clean(doc):
    if doc and "_id" in doc:
        doc.pop("_id")
    return doc


async def target_live(t):
    return {
        "id": t["id"], "group_id": t["group_id"], "name": t["name"],
        "host": t["host"], "probe": t["probe"], "interval": t["interval"],
        "status": t.get("status", "up"),
        "current": t.get("last_latency"),
        "currentLoss": t.get("last_loss", 0),
        "jitter": t.get("last_jitter", 0),
        "last_check": t.get("last_check"),
    }


# ---------- Auth ----------
@api.post("/auth/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"username": body.username})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["username"])
    return {"access_token": token,
            "user": {"username": user["username"], "role": user["role"]}}


@api.get("/auth/me")
async def me(username: str = Depends(get_current_user)):
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user["username"], "role": user["role"]}


# ---------- Overview ----------
@api.get("/overview")
async def overview(username: str = Depends(get_current_user)):
    targets = await db.targets.find().to_list(1000)
    up = sum(1 for t in targets if t.get("status") == "up")
    warn = sum(1 for t in targets if t.get("status") == "warn")
    down = sum(1 for t in targets if t.get("status") == "down")
    lats = [t.get("last_latency") for t in targets if t.get("last_latency")]
    avg = round(sum(lats) / len(lats), 2) if lats else 0
    return {"up": up, "warn": warn, "down": down, "total": len(targets),
            "avg_latency": avg}


# ---------- Tree / Groups / Targets ----------
@api.get("/tree")
async def tree(username: str = Depends(get_current_user)):
    groups = await db.groups.find().sort("order", 1).to_list(100)
    out = []
    for g in groups:
        targets = await db.targets.find({"group_id": g["id"]}).to_list(1000)
        children = [await target_live(t) for t in targets]
        out.append({"id": g["id"], "name": g["name"], "children": children})
    return out


@api.get("/groups")
async def get_groups(username: str = Depends(get_current_user)):
    groups = await db.groups.find().sort("order", 1).to_list(100)
    return [{"id": g["id"], "name": g["name"]} for g in groups]


@api.post("/groups")
async def create_group(body: GroupIn, username: str = Depends(get_current_user)):
    count = await db.groups.count_documents({})
    g = {"id": str(uuid.uuid4()), "name": body.name, "order": count,
         "created_at": datetime.now(timezone.utc)}
    await db.groups.insert_one(g)
    return {"id": g["id"], "name": g["name"]}


@api.get("/targets")
async def list_targets(username: str = Depends(get_current_user)):
    targets = await db.targets.find().to_list(1000)
    return [await target_live(t) for t in targets]


@api.get("/targets/{tid}")
async def get_target(tid: str, username: str = Depends(get_current_user)):
    t = await db.targets.find_one({"id": tid})
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    live = await target_live(t)
    grp = await db.groups.find_one({"id": t["group_id"]})
    live["groupName"] = grp["name"] if grp else ""
    return live


@api.post("/targets")
async def create_target(body: TargetIn, username: str = Depends(get_current_user)):
    grp = await db.groups.find_one({"id": body.group_id})
    if not grp:
        raise HTTPException(status_code=400, detail="Invalid group")
    t = {"id": str(uuid.uuid4()), "group_id": body.group_id, "name": body.name,
         "host": body.host, "probe": body.probe,
         "interval": max(MIN_INTERVAL, float(body.interval)),
         "enabled": True, "base": 15.0, "jitter": 4.0, "status": "up",
         "last_check": None, "created_at": datetime.now(timezone.utc)}
    await db.targets.insert_one(t)
    await scheduler.start_target(db, t)
    return await target_live(t)


@api.put("/targets/{tid}")
async def update_target(tid: str, body: TargetUpdate,
                        username: str = Depends(get_current_user)):
    t = await db.targets.find_one({"id": tid})
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if "interval" in updates:
        updates["interval"] = max(MIN_INTERVAL, float(updates["interval"]))
    if updates:
        await db.targets.update_one({"id": tid}, {"$set": updates})
    t = await db.targets.find_one({"id": tid})
    await scheduler.restart_target(db, t)
    return await target_live(t)


@api.delete("/targets/{tid}")
async def delete_target(tid: str, username: str = Depends(get_current_user)):
    scheduler.stop_target(tid)
    mtr_live.stop(tid)
    res = await db.targets.delete_one({"id": tid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Target not found")
    await db.measurements.delete_many({"target_id": tid})
    await db.alerts.delete_many({"target_id": tid})
    return {"ok": True}


# ---------- Series (smoke graph) ----------
@api.get("/targets/{tid}/series")
async def series(tid: str, range: str = "30h",
                 username: str = Depends(get_current_user)):
    t = await db.targets.find_one({"id": tid})
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    seconds, npoints = RANGES.get(range, RANGES["30h"])
    now = datetime.now(timezone.utc)
    start = now - timedelta(seconds=seconds)
    rows = await db.measurements.find(
        {"target_id": tid, "timestamp": {"$gte": start}}
    ).sort("timestamp", 1).to_list(200000)

    bucket_ms = (seconds * 1000) / npoints
    buckets = {}
    for r in rows:
        ts = r["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        idx = int((ts.timestamp() * 1000) // bucket_ms)
        b = buckets.setdefault(idx, {"rtts": [], "total": 0, "lost": 0})
        b["total"] += 1
        if r.get("up") and r.get("rtt") is not None:
            b["rtts"].append(r["rtt"])
        else:
            b["lost"] += 1

    import statistics as _st
    points = []
    for idx in sorted(buckets.keys()):
        b = buckets[idx]
        t_center = (idx * bucket_ms) + bucket_ms / 2
        rtts = b["rtts"]
        if rtts:
            med = _st.median(rtts)
            mn = min(rtts)
            mx = max(rtts)
            jit = _st.pstdev(rtts) if len(rtts) > 1 else 0.0
        else:
            med = mn = mx = jit = 0
        loss = (b["lost"] / b["total"]) * 100 if b["total"] else 0
        points.append({
            "time": int(t_center),
            "median": round(med, 3), "min": round(mn, 3), "max": round(mx, 3),
            "band": round(mx - mn, 3), "jitter": round(jit, 3),
            "loss": round(loss, 1),
        })

    if points:
        meds = [p["median"] for p in points if p["median"] > 0]
        losses = [p["loss"] for p in points]
        jits = [p["jitter"] for p in points if p["median"] > 0]
        stats = {
            "current": points[-1]["median"],
            "currentLoss": points[-1]["loss"],
            "avg": round(sum(meds) / len(meds), 2) if meds else 0,
            "min": round(min(meds), 2) if meds else 0,
            "max": round(max(meds), 2) if meds else 0,
            "avgLoss": round(sum(losses) / len(losses), 1) if losses else 0,
            "jitter": round(sum(jits) / len(jits), 2) if jits else 0,
        }
    else:
        stats = {"current": 0, "currentLoss": 0, "avg": 0, "min": 0,
                 "max": 0, "avgLoss": 0, "jitter": 0}
    return {"points": points, "stats": stats}


# ---------- MTR (traceroute) ----------
@api.post("/targets/{tid}/mtr/run")
async def run_target_mtr(tid: str, username: str = Depends(get_current_user)):
    t = await db.targets.find_one({"id": tid})
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    try:
        hops = await mtr_engine.run_mtr(t["host"], count=5)
    except Exception as e:
        logger.warning("MTR failed for %s: %s", t["host"], e)
        raise HTTPException(
            status_code=503,
            detail="Traceroute requires elevated privileges (raw sockets / "
                   "NET_RAW). This works on your self-hosted deployment.",
        )
    ts = datetime.now(timezone.utc)
    doc = {"id": str(uuid.uuid4()), "target_id": tid, "timestamp": ts,
           "hops": hops, "source": "ondemand"}
    await db.mtr_results.insert_one(doc)
    return {"timestamp": int(ts.timestamp() * 1000), "hops": hops,
            "source": "ondemand"}


@api.get("/targets/{tid}/mtr")
async def get_target_mtr(tid: str, username: str = Depends(get_current_user)):
    t = await db.targets.find_one({"id": tid})
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    latest = await db.mtr_results.find({"target_id": tid}).sort(
        "timestamp", -1).limit(1).to_list(1)
    result = None
    if latest:
        r = latest[0]
        ts = r["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        result = {"timestamp": int(ts.timestamp() * 1000), "hops": r["hops"],
                  "source": r.get("source", "scheduled")}
    return {"available": mtr_engine.mtr_available(), "latest": result}


@api.post("/targets/{tid}/mtr/start")
async def start_live_mtr(tid: str, username: str = Depends(get_current_user)):
    t = await db.targets.find_one({"id": tid})
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    if not mtr_live.available():
        raise HTTPException(
            status_code=503,
            detail="Traceroute requires elevated privileges (raw sockets / "
                   "NET_RAW). This works on your self-hosted deployment.",
        )
    s = await mtr_live.start(tid, t["host"])
    return s.state()


@api.post("/targets/{tid}/mtr/stop")
async def stop_live_mtr(tid: str, username: str = Depends(get_current_user)):
    mtr_live.stop(tid)
    return {"ok": True}


@api.get("/targets/{tid}/mtr/live")
async def get_live_mtr(tid: str, username: str = Depends(get_current_user)):
    s = mtr_live.get(tid)
    if not s:
        return {"running": False, "hops": [], "cycles": 0, "elapsed": 0,
                "available": mtr_engine.mtr_available()}
    st = s.state()
    st["available"] = mtr_engine.mtr_available()
    return st


# ---------- Ad-hoc MTR tool (any host) ----------
@api.post("/mtr/tool/start")
async def mtr_tool_start(body: MtrToolIn, username: str = Depends(get_current_user)):
    host = (body.host or "").strip()
    if not host:
        raise HTTPException(status_code=400, detail="Host is required")
    if not mtr_live.available():
        raise HTTPException(
            status_code=503,
            detail="Traceroute requires elevated privileges (raw sockets / "
                   "NET_RAW). This works on your self-hosted deployment.",
        )
    s = await mtr_live.start(f"tool:{host}", host)
    st = s.state()
    st["available"] = True
    return st


@api.post("/mtr/tool/stop")
async def mtr_tool_stop(body: MtrToolIn, username: str = Depends(get_current_user)):
    mtr_live.stop(f"tool:{(body.host or '').strip()}")
    return {"ok": True}


@api.get("/mtr/tool/live")
async def mtr_tool_live(host: str, username: str = Depends(get_current_user)):
    s = mtr_live.get(f"tool:{host.strip()}")
    if not s:
        return {"running": False, "hops": [], "cycles": 0, "elapsed": 0,
                "available": mtr_engine.mtr_available()}
    st = s.state()
    st["available"] = mtr_engine.mtr_available()
    return st


# ---------- Alerts ----------
@api.get("/alerts")
async def get_alerts(username: str = Depends(get_current_user)):
    alerts = await db.alerts.find().sort("since", -1).to_list(200)
    out = []
    for a in alerts:
        out.append({
            "id": a["id"], "target": a["target"], "targetId": a["target_id"],
            "rule": a["rule"], "severity": a["severity"], "status": a["status"],
            "message": a["message"],
            "since": int(a["since"].replace(tzinfo=timezone.utc).timestamp() * 1000)
            if a.get("since") else None,
        })
    return out


@api.get("/alert-rules")
async def get_rules(username: str = Depends(get_current_user)):
    rules = await db.alert_rules.find().to_list(100)
    return [{"id": r["id"], "name": r["name"], "condition": r["condition"],
             "operator": r["operator"], "value": r["value"],
             "severity": r["severity"], "enabled": r["enabled"]} for r in rules]


@api.put("/alert-rules/{rid}")
async def update_rule(rid: str, body: RuleUpdate,
                      username: str = Depends(get_current_user)):
    res = await db.alert_rules.update_one({"id": rid}, {"$set": {"enabled": body.enabled}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"ok": True}


@api.get("/")
async def root():
    return {"message": "CyanPing API"}


app.include_router(api)
app.add_middleware(
    CORSMiddleware, allow_credentials=True, allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await scheduler.seed_defaults(db)
    await scheduler.start_all(db)
    asyncio.create_task(scheduler.retention_loop(db))
    asyncio.create_task(scheduler.mtr_loop(db))
    logger.info("CyanPing started, per-target probe loops running")


@app.on_event("shutdown")
async def shutdown():
    client.close()
