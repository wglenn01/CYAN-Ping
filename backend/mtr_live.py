"""Live continuous MTR sessions for CyanPing.

Runs repeated short mtr batches (0.25s interval) per target, accumulating
per-hop stats + a rolling latency time-series for live graphs. Sessions run in
the background until stopped or until the client stops polling (auto-stop).
Uses the `mtr` binary when available, else icmplib traceroute fallback.
Requires raw-socket / NET_RAW privileges (works on self-hosted deployment).
"""
import asyncio
import json
import time
from collections import deque
from statistics import pstdev

import mtr as mtr_engine

MAX_SERIES = 120       # points kept per hop for the graph
POLL_TIMEOUT = 20      # auto-stop session if no client poll within N seconds
BATCH_COUNT = 2        # pings per hop per batch
INTERVAL = 0.25        # seconds between pings
MAX_HOPS = 30

_sessions = {}         # target_id -> Session


class HopStat:
    def __init__(self, host):
        self.host = host
        self.sent = 0
        self.recv = 0
        self.best = None
        self.worst = None
        self.sum = 0.0
        self.last = None
        self.series = deque(maxlen=MAX_SERIES)

    def update(self, snt, recv, last, avg, best, worst, t_ms):
        self.sent += snt
        self.recv += recv
        if last is not None:
            self.last = last
        if avg is not None and recv > 0:
            self.sum += avg * recv
        if best is not None:
            self.best = best if self.best is None else min(self.best, best)
        if worst is not None:
            self.worst = worst if self.worst is None else max(self.worst, worst)
        v = avg if avg is not None else last
        batch_loss = round((snt - recv) / snt * 100, 1) if snt else 0.0
        self.series.append({
            "t": t_ms,
            "v": round(v, 3) if v is not None else None,
            "loss": batch_loss,
        })

    def to_dict(self, idx):
        loss = round((self.sent - self.recv) / self.sent * 100, 1) if self.sent else 0.0
        avg = round(self.sum / self.recv, 3) if self.recv else None
        vals = [p["v"] for p in self.series if p["v"] is not None]
        stdev = round(pstdev(vals), 3) if len(vals) > 1 else 0.0
        return {
            "hop": idx, "host": self.host, "loss": loss, "sent": self.sent,
            "recv": self.recv, "last": self.last, "avg": avg, "best": self.best,
            "worst": self.worst, "stdev": stdev, "series": list(self.series),
        }


class Session:
    def __init__(self, target_id, host):
        self.target_id = target_id
        self.host = host
        self.hops = {}
        self.task = None
        self.running = False
        self.started = time.time()
        self.cycles = 0
        self.last_poll = time.time()
        self.error = None

    async def _run_batch(self):
        if mtr_engine.HAS_MTR:
            return await self._batch_mtr()
        return await self._batch_icmplib()

    async def _batch_mtr(self):
        proc = await asyncio.create_subprocess_exec(
            "mtr", "--json", "-c", str(BATCH_COUNT), "-i", str(INTERVAL),
            "-m", str(MAX_HOPS), self.host,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=20)
        data = json.loads(out.decode())
        res = []
        for h in data["report"]["hubs"]:
            snt = h.get("Snt", BATCH_COUNT)
            lossp = float(h.get("Loss%", 0))
            recv = round(snt * (1 - lossp / 100))
            res.append({
                "hop": h.get("count"), "host": h.get("host", "???"),
                "snt": snt, "recv": recv, "last": h.get("Last"),
                "avg": h.get("Avg"), "best": h.get("Best"), "worst": h.get("Wrst"),
            })
        return res

    async def _batch_icmplib(self):
        hops_raw = await asyncio.to_thread(
            mtr_engine._run_traceroute_sync, self.host, BATCH_COUNT, MAX_HOPS)
        res = []
        for h in hops_raw:
            recv = len(h.rtts)
            res.append({
                "hop": h.distance, "host": h.address or "???",
                "snt": BATCH_COUNT, "recv": recv,
                "last": round(h.rtts[-1], 2) if h.rtts else None,
                "avg": round(h.avg_rtt, 2) if recv else None,
                "best": round(h.min_rtt, 2) if recv else None,
                "worst": round(h.max_rtt, 2) if recv else None,
            })
        return res

    async def _loop(self):
        self.running = True
        try:
            while self.running:
                if time.time() - self.last_poll > POLL_TIMEOUT:
                    break
                try:
                    batch = await self._run_batch()
                    t_ms = int(time.time() * 1000)
                    for h in batch:
                        idx = h["hop"]
                        st = self.hops.get(idx)
                        if st is None:
                            st = HopStat(h["host"])
                            self.hops[idx] = st
                        elif h["host"] not in (None, "???"):
                            st.host = h["host"]
                        st.update(h["snt"], h["recv"], h["last"], h["avg"],
                                  h["best"], h["worst"], t_ms)
                    self.cycles += 1
                    self.error = None
                except Exception as e:
                    self.error = str(e)[:200]
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False

    def state(self, touch=True):
        if touch:
            self.last_poll = time.time()
        hops = [self.hops[i].to_dict(i) for i in sorted(self.hops)]
        return {
            "running": self.running, "cycles": self.cycles,
            "elapsed": round(time.time() - self.started, 1),
            "error": self.error, "hops": hops, "host": self.host,
        }


def available():
    return mtr_engine.mtr_available()


async def start(target_id, host):
    s = _sessions.get(target_id)
    if s and s.running:
        s.last_poll = time.time()
        return s
    s = Session(target_id, mtr_engine._extract_host(host))
    _sessions[target_id] = s
    s.task = asyncio.create_task(s._loop())
    return s


def stop(target_id):
    s = _sessions.get(target_id)
    if s:
        s.running = False
        if s.task:
            s.task.cancel()
    return s


def get(target_id):
    return _sessions.get(target_id)
