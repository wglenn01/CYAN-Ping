"""Network probe implementations for CyanPing.

Primary mode: SINGLE-PACKET probes (run_probe_single) -> {"rtt": float|None, "up": bool}
Loss %, jitter and min/med/max are derived by aggregating many single samples
into time buckets (classic SmokePing model). RTT is in milliseconds.
"""
import asyncio
import time
import socket
from urllib.parse import urlparse

try:
    from icmplib import async_ping
except Exception:  # pragma: no cover
    async_ping = None

import httpx

DEFAULT_TIMEOUT = 2.0  # seconds


async def _icmp_single(host, timeout=DEFAULT_TIMEOUT):
    if async_ping is None:
        return {"rtt": None, "up": False}
    try:
        h = await async_ping(host, count=1, timeout=timeout, privileged=False)
        if h.rtts:
            return {"rtt": round(h.rtts[0], 3), "up": True}
        return {"rtt": None, "up": False}
    except Exception:
        try:
            h = await async_ping(host, count=1, timeout=timeout, privileged=True)
            if h.rtts:
                return {"rtt": round(h.rtts[0], 3), "up": True}
        except Exception:
            pass
        return {"rtt": None, "up": False}


async def _http_single(url, timeout=DEFAULT_TIMEOUT):
    if not url.startswith("http"):
        url = "https://" + url
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False,
                                     follow_redirects=True) as client:
            r = await client.get(url)
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code < 500:
                return {"rtt": round(ms, 3), "up": True}
    except Exception:
        pass
    return {"rtt": None, "up": False}


def _dns_once(hostname):
    t0 = time.perf_counter()
    socket.getaddrinfo(hostname, None)
    return (time.perf_counter() - t0) * 1000


async def _dns_single(hostname, timeout=DEFAULT_TIMEOUT):
    if "://" in hostname:
        hostname = urlparse(hostname).hostname or hostname
    try:
        ms = await asyncio.wait_for(asyncio.to_thread(_dns_once, hostname),
                                    timeout=timeout)
        return {"rtt": round(ms, 3), "up": True}
    except Exception:
        return {"rtt": None, "up": False}


async def _tcp_single(target, timeout=DEFAULT_TIMEOUT):
    host, port = target, 80
    if "://" in target:
        u = urlparse(target)
        host = u.hostname
        port = u.port or (443 if u.scheme == "https" else 80)
    elif ":" in target:
        host, p = target.rsplit(":", 1)
        try:
            port = int(p)
        except ValueError:
            port = 80
    t0 = time.perf_counter()
    try:
        fut = asyncio.open_connection(host, int(port))
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        ms = (time.perf_counter() - t0) * 1000
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return {"rtt": round(ms, 3), "up": True}
    except Exception:
        return {"rtt": None, "up": False}


_SINGLE = {
    "ICMP": _icmp_single,
    "HTTP": _http_single,
    "DNS": _dns_single,
    "TCP": _tcp_single,
}


async def run_probe_single(probe_type, host, timeout=DEFAULT_TIMEOUT):
    func = _SINGLE.get(probe_type, _icmp_single)
    try:
        return await func(host, timeout=timeout)
    except Exception:
        return {"rtt": None, "up": False}
