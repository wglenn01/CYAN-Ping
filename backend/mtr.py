"""MTR (My TraceRoute) engine for CyanPing.

Uses the system `mtr` binary (JSON output) when available, else falls back to
icmplib.traceroute. Both need raw-socket / NET_RAW privileges (works on the
self-hosted server; blocked in the cloud preview sandbox).

Returns a list of hops:
  {hop, host, loss, sent, last, avg, best, worst, stdev}
Latency values in milliseconds.
"""
import asyncio
import json
import shutil
import socket
from urllib.parse import urlparse

HAS_MTR = shutil.which("mtr") is not None


def _extract_host(target):
    h = target.strip()
    if "://" in h:
        h = urlparse(h).hostname or h
    elif h.count(":") == 1:
        left, right = h.rsplit(":", 1)
        if right.isdigit():
            h = left
    return h


def _raw_socket_ok():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        s.close()
        return True
    except Exception:
        return False


def mtr_available():
    """True if a real traceroute can run in this environment."""
    return HAS_MTR or _raw_socket_ok()


async def _run_mtr_binary(host, count):
    proc = await asyncio.create_subprocess_exec(
        "mtr", "-j", "-c", str(count), "-Z", "1", host,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await asyncio.wait_for(proc.communicate(), timeout=90)
    if proc.returncode != 0 and not out:
        raise RuntimeError((err or b"").decode()[:200] or "mtr failed")
    data = json.loads(out.decode())
    hubs = data["report"]["hubs"]
    hops = []
    for h in hubs:
        hops.append({
            "hop": h.get("count"),
            "host": h.get("host", "???"),
            "loss": round(float(h.get("Loss%", 0)), 1),
            "sent": h.get("Snt"),
            "last": h.get("Last"),
            "avg": h.get("Avg"),
            "best": h.get("Best"),
            "worst": h.get("Wrst"),
            "stdev": h.get("StDev"),
        })
    return hops


def _run_traceroute_sync(host, count, max_hops):
    from icmplib import traceroute
    return traceroute(host, count=count, interval=0.05, timeout=1,
                      max_hops=max_hops, privileged=True)


async def _run_mtr_icmplib(host, count, max_hops):
    hops_raw = await asyncio.to_thread(_run_traceroute_sync, host, count, max_hops)
    hops = []
    for h in hops_raw:
        loss = h.packet_loss
        loss = round(loss * 100, 1) if loss <= 1 else round(loss, 1)
        hops.append({
            "hop": h.distance,
            "host": h.address,
            "loss": loss,
            "sent": count,
            "last": round(h.rtts[-1], 2) if h.rtts else None,
            "avg": round(h.avg_rtt, 2),
            "best": round(h.min_rtt, 2),
            "worst": round(h.max_rtt, 2),
            "stdev": round(getattr(h, "jitter", 0.0), 2),
        })
    return hops


async def run_mtr(target_host, count=5, max_hops=30):
    host = _extract_host(target_host)
    if HAS_MTR:
        return await _run_mtr_binary(host, count)
    return await _run_mtr_icmplib(host, count, max_hops)
