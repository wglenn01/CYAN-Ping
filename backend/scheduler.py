"""Background scheduler: seeding, synthetic bootstrap history, and live polling."""
import asyncio
import math
import random
import uuid
from datetime import datetime, timezone

from probes import run_probe
from auth import hash_password

# ---- Default seed data (4 groups / 10 targets) ----
DEFAULT_GROUPS = [
    ("Core Network", [
        ("Edge Gateway", "10.0.0.1", "ICMP", 60, 1.8, 0.6),
        ("Core Switch", "10.0.0.2", "ICMP", 60, 0.9, 0.3),
    ]),
    ("Internet Uplinks", [
        ("Google DNS", "8.8.8.8", "ICMP", 60, 12.4, 3.2),
        ("Cloudflare DNS", "1.1.1.1", "ICMP", 60, 9.7, 2.1),
        ("Quad9 DNS", "9.9.9.9", "ICMP", 120, 15.0, 4.0),
    ]),
    ("Web Services", [
        ("Google", "https://www.google.com", "HTTP", 120, 84.0, 22.0),
        ("GitHub", "https://github.com", "HTTP", 120, 120.0, 30.0),
        ("Cloudflare DNS Name", "one.one.one.one", "DNS", 300, 18.0, 5.0),
    ]),
    ("Remote Sites", [
        ("HTTPS Reachability", "1.1.1.1:443", "TCP", 60, 20.0, 6.0),
        ("Google 443", "www.google.com:443", "TCP", 60, 40.0, 12.0),
    ]),
]


def now_ts():
    return datetime.now(timezone.utc)


async def seed_defaults(db):
    # Seed admin user
    if not await db.users.find_one({"username": "admin"}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "username": "admin",
            "password_hash": hash_password("admin"),
            "role": "Administrator",
            "created_at": now_ts(),
        })

    # Seed alert rules
    if await db.alert_rules.count_documents({}) == 0:
        rules = [
            {"name": "Host Down", "condition": "loss", "operator": ">", "value": 50, "severity": "critical", "enabled": True},
            {"name": "High Latency", "condition": "latency", "operator": ">", "value": 150, "severity": "warning", "enabled": True},
            {"name": "Packet Loss", "condition": "loss", "operator": ">", "value": 15, "severity": "warning", "enabled": True},
        ]
        for r in rules:
            r["id"] = str(uuid.uuid4())
            await db.alert_rules.insert_one(r)

    # Seed groups + targets
    if await db.groups.count_documents({}) == 0:
        for order, (gname, targets) in enumerate(DEFAULT_GROUPS):
            gid = str(uuid.uuid4())
            await db.groups.insert_one({"id": gid, "name": gname, "order": order,
                                        "created_at": now_ts()})
            for tname, host, probe, interval, base, jitter in targets:
                tid = str(uuid.uuid4())
                await db.targets.insert_one({
                    "id": tid, "group_id": gid, "name": tname, "host": host,
                    "probe": probe, "interval": interval, "enabled": True,
                    "base": base, "jitter": jitter,
                    "status": "up", "last_check": None,
                    "created_at": now_ts(),
                })
        await backfill_history(db)


async def backfill_history(db):
    """Synthetic BOOTSTRAP history (~10 days) so graphs are populated instantly.
    Real measurements are appended by the live loop going forward."""
    targets = await db.targets.find().to_list(1000)
    now = now_ts().timestamp()
    span = 10 * 86400
    step = 20 * 60  # 20 minutes
    n = int(span / step)
    docs = []
    for t in targets:
        base = t.get("base", 15.0)
        jitter = t.get("jitter", 4.0)
        reliability = 0.985
        for i in range(n):
            ts = now - (n - i) * step
            spike = random.random()
            spike_val = base * 2.2 if spike > 0.96 else 0
            wobble = math.sin(i / 9) * jitter * 0.6
            median = max(0.3, base + wobble + (random.random() - 0.5) * jitter + spike_val)
            spread = jitter * (0.4 + random.random())
            mn = max(0.2, median - spread * (0.5 + random.random()))
            mx = median + spread * (0.6 + random.random())
            loss = 0
            roll = random.random()
            if roll > reliability:
                loss = min(100, round((roll - reliability) * 400))
            docs.append({
                "id": str(uuid.uuid4()),
                "target_id": t["id"],
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc),
                "min": round(mn, 2), "avg": round(median, 2),
                "median": round(median, 2), "max": round(mx, 2),
                "loss": float(loss), "up": loss < 100, "synthetic": True,
            })
        if len(docs) > 3000:
            await db.measurements.insert_many(docs)
            docs = []
    if docs:
        await db.measurements.insert_many(docs)
    # ensure index for fast range queries
    await db.measurements.create_index([("target_id", 1), ("timestamp", 1)])


def _status_from(measurement, rules):
    loss = measurement.get("loss", 100)
    latency = measurement.get("median")
    if loss >= 100 or not measurement.get("up", False):
        return "down"
    warn = False
    for r in rules:
        if not r.get("enabled"):
            continue
        if r["condition"] == "loss" and loss > r["value"]:
            if r["severity"] == "critical":
                return "down"
            warn = True
        if r["condition"] == "latency" and latency is not None and latency > r["value"]:
            warn = True
    return "warn" if warn else "up"


async def _evaluate_alerts(db, target, measurement, rules):
    loss = measurement.get("loss", 0)
    latency = measurement.get("median")
    for r in rules:
        if not r.get("enabled"):
            continue
        triggered = False
        if r["condition"] == "loss" and loss > r["value"]:
            triggered = True
            msg = f"Packet loss {loss}% exceeds {r['value']}%"
        elif r["condition"] == "latency" and latency is not None and latency > r["value"]:
            triggered = True
            msg = f"Median latency {latency}ms exceeds {r['value']}ms"
        else:
            msg = None

        existing = await db.alerts.find_one({
            "target_id": target["id"], "rule_id": r["id"], "status": "active"})

        if triggered:
            if not existing:
                await db.alerts.insert_one({
                    "id": str(uuid.uuid4()),
                    "target_id": target["id"], "target": target["name"],
                    "rule_id": r["id"], "rule": f"{r['condition']} {r['operator']} {r['value']}",
                    "severity": r["severity"], "status": "active",
                    "message": msg, "since": now_ts(),
                })
        else:
            if existing:
                await db.alerts.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"status": "resolved", "message": "Recovered",
                              "resolved_at": now_ts()}})


async def probe_target(db, target, rules):
    result = await run_probe(target["probe"], target["host"])
    ts = now_ts()
    await db.measurements.insert_one({
        "id": str(uuid.uuid4()),
        "target_id": target["id"],
        "timestamp": ts,
        "min": result["min"], "avg": result["avg"],
        "median": result["median"], "max": result["max"],
        "loss": result["loss"], "up": result["up"],
    })
    status = _status_from(result, rules)
    await db.targets.update_one(
        {"id": target["id"]},
        {"$set": {"last_check": ts, "status": status,
                  "last_latency": result["median"], "last_loss": result["loss"]}})
    await _evaluate_alerts(db, target, result, rules)


async def poll_loop(db):
    # initial probe for all targets so live values appear quickly
    await asyncio.sleep(3)
    while True:
        try:
            rules = await db.alert_rules.find().to_list(100)
            targets = await db.targets.find({"enabled": True}).to_list(1000)
            now = now_ts()
            due = []
            for t in targets:
                last = t.get("last_check")
                if last is None:
                    due.append(t)
                else:
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    if (now - last).total_seconds() >= t.get("interval", 60):
                        due.append(t)
            if due:
                await asyncio.gather(*[probe_target(db, t, rules) for t in due])
        except Exception as e:
            print("poll_loop error:", e)
        await asyncio.sleep(15)
