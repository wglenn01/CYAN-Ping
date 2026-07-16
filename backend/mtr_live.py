"""Live continuous MTR sessions for CyanPing (high-speed).

Discovers the hop path once (traceroute), then pings every hop CONCURRENTLY
every 0.25s using icmplib (no per-cycle subprocess spawn) for smooth real-time
updates. Rediscovers the path periodically. Keeps ~90s of per-hop history.
Requires raw-socket / NET_RAW privileges (works on self-hosted deployment).
"""
import asyncio
import json
import time
from collections import deque
from statistics import pstdev

import mtr as mtr_engine

try:
    from icmplib import async_ping
except Exception:  # pragma: no cover
    async_ping = None

MAX_SERIES = 400       # ~100s of points at 0.25s
POLL_TIMEOUT = 15      # auto-stop if no client poll within N seconds
INTERVAL = 0.25        # seconds between ping cycles
PING_TIMEOUT = 0.6     # per-hop ping timeout
MAX_HOPS = 30
DISCOVER_EVERY = 60    # rediscover path every N cycles (~15s)

_sessions = {}


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

    def update(self, up, rtt, t_ms):
        self.sent += 1
        if up and rtt is not None:
            self.recv += 1
            self.last = rtt
            self.sum += rtt
            self.best = rtt if self.best is None else min(self.best, rtt)
            self.worst = rtt if self.worst is None else max(self.worst, rtt)
        self.series.append({
            "t": t_ms,
            "v": round(rtt, 3) if (up and rtt is not None) else None,
            "loss": 0 if up else 100,
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
        self.hops = {}          # idx -> HopStat
        self.hop_list = []      # [{"idx","addr"}]
        self.task = None
        self.running = False
        self.started = time.time()
        self.cycles = 0
        self.last_poll = time.time()
        self.error = None

    async def _discover(self):
        lst = None
        try:
            hops_raw = await asyncio.wait_for(
                asyncio.to_thread(mtr_engine._run_traceroute_sync, self.host, 1, MAX_HOPS),
                timeout=10)
            lst = [{"idx": h.distance, "addr": h.address} for h in hops_raw]
        except Exception:
            lst = await self._discover_mtr()
        if lst:
            self.hop_list = lst
            for h in lst:
                if h["idx"] not in self.hops:
                    self.hops[h["idx"]] = HopStat(h["addr"] or "???")
                elif h["addr"]:
                    self.hops[h["idx"]].host = h["addr"]

    async def _discover_mtr(self):
        try:
            proc = await asyncio.create_subprocess_exec(
                "mtr", "--json", "-c", "1", "-m", str(MAX_HOPS), self.host,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            data = json.loads(out.decode())
            return [{"idx": h.get("count"), "addr": h.get("host")}
                    for h in data["report"]["hubs"]]
        except Exception:
            return []

    async def _ping_hop(self, addr):
        if not addr or addr == "???" or async_ping is None:
            return (False, None)
        try:
            h = await async_ping(addr, count=1, timeout=PING_TIMEOUT, privileged=True)
            if h.rtts:
                return (True, round(h.rtts[0], 3))
        except Exception:
            pass
        return (False, None)

    async def _loop(self):
        self.running = True
        try:
            await self._discover()
            if not self.hop_list:
                self.error = "Could not resolve any hops"
            loop = asyncio.get_event_loop()
            next_t = loop.time()
            since_disc = 0
            while self.running:
                if time.time() - self.last_poll > POLL_TIMEOUT:
                    break
                addrs = [(h["idx"], h["addr"]) for h in self.hop_list]
                if addrs:
                    results = await asyncio.gather(*[self._ping_hop(a) for _, a in addrs])
                    t_ms = int(time.time() * 1000)
                    for (idx, addr), (up, rtt) in zip(addrs, results):
                        st = self.hops.get(idx)
                        if st is None:
                            st = HopStat(addr or "???")
                            self.hops[idx] = st
                        st.update(up, rtt, t_ms)
                    self.cycles += 1
                since_disc += 1
                if since_disc >= DISCOVER_EVERY:
                    since_disc = 0
                    try:
                        await self._discover()
                    except Exception:
                        pass
                next_t += INTERVAL
                delay = next_t - loop.time()
                if delay < 0:
                    next_t = loop.time()
                    delay = 0
                await asyncio.sleep(delay)
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
