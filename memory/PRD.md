# CyanPing — SmokePing Clone (PRD)

## Original Problem Statement
Build a full clone of the SmokePing app with all its features, but with a modern, beautiful UI
using Cyan Wireless brand colors (cyan + purple, dark mode). Must run on Ubuntu on a Proxmox
server. Add continuous sub-second ICMP ping and Live MTR features.

## User Preferences
- Language: English
- Theme: Dark mode, cyan/purple (Cyan Wireless branding)
- Deployment: Self-hosted via Docker (Ubuntu on Proxmox), Nginx reverse proxy
- Ping: sub-second (0.25s / 0.5s), 1 packet/probe, up to 20 targets, track jitter, keep ~1 week of data
- MTR: continuous 0.25s pings until Stop pressed, live per-hop graphs, 30s window

## Architecture
- Backend: FastAPI + MongoDB (motor), icmplib for ICMP/MTR, per-target async probe loops
- Frontend: React + Tailwind + Shadcn UI, inline-SVG charts for live MTR (Recharts only on Target Detail)
- Auth: JWT (admin/admin seeded on startup)
- Deploy: docker-compose, Nginx in frontend.Dockerfile proxies /api -> backend:8001

## Key Files
- backend/mtr_live.py — concurrent 0.25s live MTR sessions
- frontend/src/components/MtrHops.jsx — inline-SVG strip charts + MTR metrics grid
- frontend/src/components/MtrPanel.jsx, pages/MtrTool.jsx — live MTR UIs

## Changelog
- 2026-06: Fixed Live MTR "hang at 60 cycles" — periodic path rediscovery was awaited
  inline (blocking up to 10s), freezing all pinging. Now runs as a non-blocking background
  task (`_safe_discover`) so pinging stays smooth.
- 2026-06: Reworked MtrHops metrics grid to clearly show the standard MTR columns:
  Loss%, Snt, Avg, Best, Wrst, StDev (6-col labeled grid with color coding).

## Environment Constraint
Live MTR uses raw sockets (NET_RAW). Blocked in the Emergent sandbox — pages gracefully show
an "elevated privileges" warning. Real MTR data only renders on the self-hosted deployment.

## Backlog
- P1: UI tweaks on MTR pages per user feedback
- P2: "recent hosts" dropdown on MTR Tool page
