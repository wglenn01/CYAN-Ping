# CyanPing — API Contracts & Integration Plan

## Auth (JWT)
- POST /api/auth/login {username,password} -> {access_token, user}
- GET /api/auth/me (Bearer) -> user
- Seed default admin/admin on startup. Password hashed (bcrypt).

## Tree / Targets / Groups
- GET /api/tree -> [{id,name,children:[target+liveStats]}]
- GET /api/targets -> flat list with liveStats (current, loss, avg3h, status)
- GET /api/targets/{id} -> single target + liveStats
- POST /api/targets {name,host,probe,interval,group_id} -> target
- PUT /api/targets/{id} -> updated target
- DELETE /api/targets/{id}
- GET /api/groups ; POST /api/groups {name}
- GET /api/overview -> {up,warn,down,total,avg_latency}

## Series (smoke graph)
- GET /api/targets/{id}/series?range=3h|30h|10d|360d
  -> {points:[{time,median,min,max,band,loss}], stats:{current,currentLoss,avg,min,max,avgLoss}}
  Buckets raw measurements into ~N points for the range.

## Alerts (in-app only, no email/webhook)
- GET /api/alerts -> [{id,target,targetId,rule,severity,status,message,since}]
- GET /api/alert-rules ; PUT /api/alert-rules/{id} {enabled}
- Rules evaluated by scheduler after each probe -> active/resolved alerts.

## Probes (real measurements)
- ICMP: icmplib async_ping (unprivileged; privileged fallback), 15 packets
- HTTP: httpx GET response time, 3 samples
- DNS: dns.resolver resolution time, 3 samples
- TCP: asyncio connect time to host:port, 3 samples
- Each run -> Measurement {target_id,timestamp,min,avg,median,max,loss,up}

## Scheduler
- Startup: seed admin, seed default groups/targets (if empty), backfill ~10d
  synthetic history for seeded targets (BOOTSTRAP demo history so graphs aren't
  empty), start background loop.
- Loop: every 15s probe due targets (now-last_check>=interval) concurrently,
  store measurement, update target status, evaluate alert rules.
- NOTE: Backfilled history for the 4 default groups is synthetic bootstrap.
  All new probes + user-added targets are 100% real measurements.

## Status logic
- loss>=100 -> down; (loss>15 or latency>2x baseline/threshold) -> warn; else up.

## Frontend integration
- Replace mock.js usage with api.js (axios, REACT_APP_BACKEND_URL + /api).
- AuthContext -> real login storing JWT; axios interceptor adds Bearer.
- Dashboard/TargetDetail/Alerts/Settings fetch from API. Keep LOSS_COLORS,
  TIME_RANGES, lossColor helpers (pure UI) in a constants module.
- Poll dashboard/detail every ~30s for live updates.
