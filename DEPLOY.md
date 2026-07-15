# CyanPing — Self-Hosting on Proxmox / Ubuntu

A modern SmokePing-style network latency & reachability monitor.
React + FastAPI + MongoDB. Real ICMP / HTTP / DNS / TCP probes.

---

## 1. Create the host (Proxmox)

Use **either** an Ubuntu VM (recommended — best ICMP support) **or** an LXC container.

### Option A — Ubuntu 22.04/24.04 VM (recommended)
1. Proxmox → Create VM → attach Ubuntu Server ISO.
2. 2 vCPU / 2 GB RAM / 16 GB disk is plenty.
3. Install Ubuntu, enable SSH.

### Option B — LXC container
- Use an **unprivileged** container is fine. To allow ICMP, the app uses
  unprivileged ICMP sockets (`net.ipv4.ping_group_range`). If ping fails,
  switch the backend to `NET_RAW` (see docker-compose notes).

---

## 2. Install Docker + Compose

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # re-login after this
```

---

## 3. Get the code

Copy this project to the server (git clone your repo, or scp the folder), then:

```bash
cd /opt
sudo git clone <your-repo-url> cyanping   # or copy the /app folder here
cd cyanping/deploy
```

---

## 4. Configure

Edit `deploy/docker-compose.yml`:

- **`JWT_SECRET`** → set a long random string:
  ```bash
  openssl rand -hex 32
  ```
- **`REACT_APP_BACKEND_URL`** (frontend build arg) → the URL the *browser* uses
  to reach the backend. Set it to your server, e.g. `http://192.168.1.50:8001`.
- Publish the backend port. Add to the `backend` service in compose:
  ```yaml
      ports:
        - "8001:8001"
  ```

> The frontend (browser) talks to the backend over the network, so
> `REACT_APP_BACKEND_URL` must be an address reachable from your PC/phone,
> not the internal docker hostname.

---

## 5. Build & run

```bash
docker compose up -d --build
```

- Web UI:   `http://<server-ip>:8080`
- API:      `http://<server-ip>:8001/api`
- Login:    **admin / admin**  (change the password in Settings)

Check logs:
```bash
docker compose logs -f backend
```

---

## 6. ICMP (ping) permissions

Real ICMP needs one of:
- **Unprivileged ICMP** (default): the compose file sets
  `net.ipv4.ping_group_range=0 2147483647`. Works on most hosts.
- **Raw sockets**: if the sysctl is blocked, uncomment in compose:
  ```yaml
      cap_add:
        - NET_RAW
  ```
  and the code automatically falls back to privileged pings.

HTTP / DNS / TCP probes need no special privileges.

---

## 7. Add your own targets

Open the UI → **Add Target** → choose a probe (ICMP/HTTP/DNS/TCP), a host, a
group and a poll interval. Live probing starts immediately and graphs fill in
over time. The 4 seeded demo groups ship with bootstrap history so the UI
isn't empty on first run — delete them if you don't need them.

---

## 8. Updating

```bash
cd /opt/cyanping
git pull
cd deploy
docker compose up -d --build
```

Data (targets + history) is persisted in the `mongo_data` volume.

---

## 9. Reverse proxy + HTTPS (optional)

Put Nginx Proxy Manager / Caddy / Traefik in front and point:
- `cyanping.yourdomain` → frontend `:8080`
- `cyanping-api.yourdomain` → backend `:8001`

Then set `REACT_APP_BACKEND_URL=https://cyanping-api.yourdomain` and rebuild the
frontend.
