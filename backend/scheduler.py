"""High-resolution scheduler for CyanPing.

- One dedicated async loop per target (honors fractional intervals down to 0.25s).
- Each tick = ONE probe packet. Loss%, jitter, min/med/max are derived from a
  rolling window (live stats) and from time buckets (graphs).
- 7-day retention cleanup.
"""
import asyncio
import math
import random
import statistics
import time
import uuid
from collections import deque
from datetime import datetime, timezone, timedelta

from probes import run_probe_single
from auth import hash_password

MIN_INTERVAL = 0.25
RETENTION_DAYS = 7
STATUS_WRITE_EVERY = 2.0   # seconds between target-doc stat updates
ALERT_EVAL_EVERY = 5.0     # seconds between alert evaluations

# runtime state
_tasks = {}       # target_id -> asyncio.Task
_windows = {}     # target_id -> deque of {"rtt","up"}
_db = None

DEFAULT_GROUPS = [
    ("Core Network", [
        ("Edge Gateway", "10.0.0.1", "ICMP", 1.0, 1.8, 0.6),
        ("Core Switch", "10.0.0.2", "ICMP", 1.0, 0.9, 0.3),
    ]),
    ("Internet Uplinks", [
        ("Google DNS", "8.8.8.8", "ICMP", 0.5, 12.4, 3.2),
        ("Cloudflare DNS", "1.1.1.1", "ICMP", 0.5, 9.7, 2.1),
        ("Quad9 DNS", "9.9.9.9", "ICMP", 1.0, 15.0, 4.0),
    ]),
    ("Web Services", [
        ("Google", "https://www.google.com", "HTTP", 2.0, 84.0, 22.0),
        ("GitHub", "https://github.com", "HTTP", 2.0, 120.0, 30.0),
        ("Cloudflare Name", "one.one.one.one", "DNS", 2.0, 18.0, 5.0),
    ]),
    ("Remote Sites", [
        ("HTTPS Reachability", "1.1.1.1:443", "TCP", 1.0, 20.0, 6.0),
        ("Google 443", "www.google.com:443", "TCP", 1.0, 40.0, 12.0),
    ]),
]


def now_ts():
    return datetime.now(timezone.utc)


def _window_len(interval):
    # keep ~60s of samples, clamped to [20, 400]
    return max(20, min(400, int(60 / max(interval, MIN_INTERVAL))))


# ---------------- Seeding ----------------
async def seed_defaults(db):
    if not await db.users.find_one({"username": "admin"}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "username": "admin",
            "password_hash": hash_password("admin"),
            "role": "Administrator", "created_at": now_ts(),
        })

    if await db.alert_rules.count_documents({}) == 0:
        for r in [
            {"name": "Host Down", "condition": "loss", "operator": ">", "value": 50, "severity": "critical", "enabled": True},
            {"name": "High Latency", "condition": "latency", "operator": ">", "value": 150, "severity": "warning", "enabled": True},
            {"name": "Packet Loss", "condition": "loss", "operator": ">", "value": 15, "severity": "warning", "enabled": True},
            {"name": "High Jitter", "condition": "jitter", "operator": ">", "value": 30, "severity": "warning", "enabled": False},
        ]:
            r["id"] = str(uuid.uuid4())
            await db.alert_rules.insert_one(r)

    if await db.groups.count_documents({}) == 0:
        for order, (gname, targets) in enumerate(DEFAULT_GROUPS):
            gid = str(uuid.uuid4())
            await db.groups.insert_one({"id": gid, "name": gname, "order": order,
                                        "created_at": now_ts()})
            for tname, host, probe, interval, base, jitter in targets:
                await db.targets.insert_one({
                    "id": str(uuid.uuid4()), "group_id": gid, "name": tname,
                    "host": host, "probe": probe, "interval": float(interval),
                    "enabled": True, "base": base, "jitter": jitter,
                    "status": "up", "last_check": None, "created_at": now_ts(),
                })
        await backfill_history(db)

    await db.measurements.create_index([("target_id", 1), ("timestamp", 1)])


async def backfill_history(db):
    """Synthetic BOOTSTRAP history (~7 days, single-rtt samples) so graphs are
    populated on first run. Real probes append going forward."""
    targets = await db.targets.find().to_list(1000)
    now = now_ts().timestamp()
    span = RETENTION_DAYS * 86400
    step = 180  # 3-minute synthetic samples
    n = int(span / step)
    docs = []
    for t in targets:
        base = t.get("base", 15.0)
        jitter = t.get("jitter", 4.0)
        reliability = 0.985
        for i in range(n):
            ts = now - (n - i) * step
            spike = base * 2.2 if random.random() > 0.97 else 0
            wobble = math.sin(i / 9) * jitter * 0.6
            rtt = max(0.2, base + wobble + (random.random() - 0.5) * jitter + spike)
            up = random.random() <= reliability
            docs.append({
                "id": str(uuid.uuid4()), "target_id": t["id"],
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc),
                "rtt": round(rtt, 3) if up else None, "up": up,
                "synthetic": True,
            })
        if len(docs) > 5000:
            await db.measurements.insert_many(docs)
            docs = []
    if docs:
        await db.measurements.insert_many(docs)


# ---------------- Live stats from rolling window ----------------
def _window_stats(win):
    total = len(win)
    rtts = [s["rtt"] for s in win if s["up"] and s["rtt"] is not None]
    if total == 0:
        return None
    lost = total - len(rtts)
    loss = round((lost / total) * 100, 1)
    if rtts:
        median = round(statistics.median(rtts), 3)
        jit = round(statistics.pstdev(rtts), 3) if len(rtts) > 1 else 0.0
    else:
        median, jit = None, 0.0
    return {"median": median, "loss": loss, "jitter": jit, "up": loss < 100}


def _status_from(stats, rules):
    if stats is None or stats["loss"] >= 100 or not stats["up"]:
        return "down"
    warn = False
    for r in rules:
        if not r.get("enabled"):
            continue
        if r["condition"] == "loss" and stats["loss"] > r["value"]:
            if r["severity"] == "critical":
                return "down"
            warn = True
        if r["condition"] == "latency" and stats["median"] is not None and stats["median"] > r["value"]:
            warn = True
        if r["condition"] == "jitter" and stats["jitter"] > r["value"]:
            warn = True
    return "warn" if warn else "up"


async def _update_target_stats(db, target, win, rules):
    stats = _window_stats(win)
    if stats is None:
        return
    status = _status_from(stats, rules)
    await db.targets.update_one(
        {"id": target["id"]},
        {"$set": {"last_check": now_ts(), "status": status,
                  "last_latency": stats["median"], "last_loss": stats["loss"],
                  "last_jitter": stats["jitter"]}})


async def _evaluate_alerts(db, target, win, rules):
    stats = _window_stats(win)
    if stats is None:
        return
    loss, latency, jitter = stats["loss"], stats["median"], stats["jitter"]
    for r in rules:
        if not r.get("enabled"):
            continue
        triggered, msg = False, None
        if r["condition"] == "loss" and loss > r["value"]:
            triggered, msg = True, f"Packet loss {loss}% exceeds {r['value']}%"
        elif r["condition"] == "latency" and latency is not None and latency > r["value"]:
            triggered, msg = True, f"Median latency {latency}ms exceeds {r['value']}ms"
        elif r["condition"] == "jitter" and jitter > r["value"]:
            triggered, msg = True, f"Jitter {jitter}ms exceeds {r['value']}ms"

        existing = await db.alerts.find_one({
            "target_id": target["id"], "rule_id": r["id"], "status": "active"})
        if triggered:
            if not existing:
                await db.alerts.insert_one({
                    "id": str(uuid.uuid4()), "target_id": target["id"],
                    "target": target["name"], "rule_id": r["id"],
                    "rule": f"{r['condition']} {r['operator']} {r['value']}",
                    "severity": r["severity"], "status": "active",
                    "message": msg, "since": now_ts()})
        elif existing:
            await db.alerts.update_one(
                {"_id": existing["_id"]},
                {"$set": {"status": "resolved", "message": "Recovered",
                          "resolved_at": now_ts()}})


# ---------------- Per-target loop ----------------
async def _target_loop(db, target):
    tid = target["id"]
    interval = max(MIN_INTERVAL, float(target.get("interval", 60)))
    win = deque(maxlen=_window_len(interval))
    _windows[tid] = win
    loop = asyncio.get_event_loop()
    next_t = loop.time()
    last_status = 0.0
    last_alert = 0.0
    try:
        while True:
            try:
                res = await run_probe_single(target["probe"], target["host"])
                await db.measurements.insert_one({
                    "id": str(uuid.uuid4()), "target_id": tid,
                    "timestamp": now_ts(), "rtt": res["rtt"], "up": res["up"]})
                win.append(res)
                now = loop.time()
                if now - last_status >= STATUS_WRITE_EVERY:
                    rules = await db.alert_rules.find().to_list(100)
                    await _update_target_stats(db, target, win, rules)
                    last_status = now
                if now - last_alert >= ALERT_EVAL_EVERY:
                    rules = await db.alert_rules.find().to_list(100)
                    await _evaluate_alerts(db, target, win, rules)
                    last_alert = now
            except Exception as e:
                print(f"[probe {tid}] error:", e)
            next_t += interval
            delay = next_t - loop.time()
            if delay < 0:
                next_t = loop.time()
                delay = 0
            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        _windows.pop(tid, None)
        raise


# ---------------- Manager ----------------
async def start_target(db, target):
    stop_target(target["id"])
    if not target.get("enabled", True):
        return
    _tasks[target["id"]] = asyncio.create_task(_target_loop(db, target))


def stop_target(tid):
    task = _tasks.pop(tid, None)
    if task:
        task.cancel()
    _windows.pop(tid, None)


async def restart_target(db, target):
    await start_target(db, target)


async def start_all(db):
    global _db
    _db = db
    targets = await db.targets.find({"enabled": True}).to_list(1000)
    for t in targets:
        await start_target(db, t)


async def retention_loop(db):
    while True:
        try:
            cutoff = now_ts() - timedelta(days=RETENTION_DAYS)
            await db.measurements.delete_many({"timestamp": {"$lt": cutoff}})
            # resolve stale active alerts whose targets vanished
        except Exception as e:
            print("retention error:", e)
        await asyncio.sleep(3600)
