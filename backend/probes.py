"""Network probe implementations for CyanPing. All return a dict:
{min, avg, median, max, loss, up}  (latency in ms)
"""
import asyncio
import statistics
import time
import socket
from urllib.parse import urlparse

try:
    from icmplib import async_ping
except Exception:  # pragma: no cover
    async_ping = None

import httpx


def _summarize(samples, attempts):
    """samples: list of successful latencies (ms). attempts: total tries."""
    lost = attempts - len(samples)
    loss = round((lost / attempts) * 100, 1) if attempts else 100.0
    if not samples:
        return {"min": None, "avg": None, "median": None, "max": None,
                "loss": 100.0, "up": False}
    return {
        "min": round(min(samples), 2),
        "avg": round(sum(samples) / len(samples), 2),
        "median": round(statistics.median(samples), 2),
        "max": round(max(samples), 2),
        "loss": loss,
        "up": loss < 100,
    }


async def probe_icmp(host, count=15):
    if async_ping is None:
        return _summarize([], count)
    try:
        h = await async_ping(host, count=count, interval=0.05, timeout=1,
                             privileged=False)
        rtts = list(h.rtts)
        return _summarize(rtts, count)
    except Exception:
        # fallback to privileged (works on servers with CAP_NET_RAW)
        try:
            h = await async_ping(host, count=count, interval=0.05, timeout=1,
                                 privileged=True)
            return _summarize(list(h.rtts), count)
        except Exception:
            return _summarize([], count)


async def probe_http(url, attempts=3):
    if not url.startswith("http"):
        url = "https://" + url
    samples = []
    async with httpx.AsyncClient(timeout=5, verify=False, follow_redirects=True) as client:
        for _ in range(attempts):
            t0 = time.perf_counter()
            try:
                r = await client.get(url)
                if r.status_code < 500:
                    samples.append((time.perf_counter() - t0) * 1000)
            except Exception:
                pass
            await asyncio.sleep(0.05)
    return _summarize(samples, attempts)


def _dns_once(hostname):
    t0 = time.perf_counter()
    socket.getaddrinfo(hostname, None)
    return (time.perf_counter() - t0) * 1000


async def probe_dns(hostname, attempts=3):
    # strip scheme if a URL was given
    if "://" in hostname:
        hostname = urlparse(hostname).hostname or hostname
    samples = []
    for _ in range(attempts):
        try:
            ms = await asyncio.to_thread(_dns_once, hostname)
            samples.append(ms)
        except Exception:
            pass
        await asyncio.sleep(0.05)
    return _summarize(samples, attempts)


async def _tcp_once(host, port):
    t0 = time.perf_counter()
    fut = asyncio.open_connection(host, port)
    reader, writer = await asyncio.wait_for(fut, timeout=5)
    ms = (time.perf_counter() - t0) * 1000
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass
    return ms


async def probe_tcp(target, attempts=3):
    # target formats: host:port  |  https://host  (defaults 443/80)
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
    samples = []
    for _ in range(attempts):
        try:
            ms = await _tcp_once(host, int(port))
            samples.append(ms)
        except Exception:
            pass
        await asyncio.sleep(0.05)
    return _summarize(samples, attempts)


PROBE_FUNCS = {
    "ICMP": probe_icmp,
    "HTTP": probe_http,
    "DNS": probe_dns,
    "TCP": probe_tcp,
}


async def run_probe(probe_type, host):
    func = PROBE_FUNCS.get(probe_type, probe_icmp)
    try:
        return await func(host)
    except Exception:
        return {"min": None, "avg": None, "median": None, "max": None,
                "loss": 100.0, "up": False}
