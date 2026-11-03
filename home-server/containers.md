# Artemis — Containers

All services on Artemis are defined across five compose files, included from the root `docker-compose.yml`. Every service except `cloudflare-ddns-home` and `qbittorrent` attaches to the shared `olympus_internal` bridge network (name kept from before the Olympus → Artemis rename).

```
docker-compose.yml
├── docker-compose.infra.yml       # Networking, DNS, VPN, file sharing
├── docker-compose.apps.yml        # Self-hosted applications
├── docker-compose.monitoring.yml  # Observability + dashboard
├── docker-compose.media.yml       # Media automation + streaming
└── docker-compose.sparky.yml      # SparkyFitness stack (env: .env.sparky)
```

Conventions used across the stack:

- `PUID=1000` / `PGID=1000` (user `zeus`), `TZ=Europe/Helsinki`
- Persistent state lives under `./containers/<service>/` relative to the compose project; media and books live on Cornucopia (`/mnt/cornucopia`)
- `restart: unless-stopped`, except the SparkyFitness stack which uses `restart: always`
- Every service carries `dynacat.*` labels so it shows up on the Dynacat dashboard (`home.vathzen.in`), grouped by `dynacat.category`
- Secrets come from `.env` (see `.env.example`) and `.env.sparky` (see `.env.sparky.example`); neither is committed

---

## Network

| Network            | Driver | Declared in                                                          |
|--------------------|--------|----------------------------------------------------------------------|
| `olympus_internal` | bridge | Root `docker-compose.yml` (managed) and every included file (`external: true`) |

Services reach each other by container name over this network; Caddy proxies to `container_name:container_port`, never to host ports. Host ports listed below are for direct LAN / tailnet access and debugging.

> If `docker compose down` removes the network and `up` then fails with *"declared as external, but could not be found"*, recreate it:
> ```bash
> docker network create --driver bridge olympus_internal
> ```

---

## Reverse Proxy Map — `configs/Caddyfile`

TLS for `*.vathzen.in` is issued by Caddy via the Cloudflare DNS-01 challenge.

| Subdomain                | Upstream                     | Notes                                 |
|--------------------------|------------------------------|---------------------------------------|
| `vault.vathzen.in`       | `vaultwarden:80`             |                                       |
| `calibre.vathzen.in`     | `calibre-web:8083`           | Also served over plain `http://`      |
| `shelfmark.vathzen.in`   | `shelfmark:8084`             |                                       |
| `pdf.vathzen.in`         | `stirling-pdf:8080`          |                                       |
| `loan.vathzen.in`        | `claude-loan-tracker:8080`   |                                       |
| `prom.vathzen.in`        | `prometheus:9090`            |                                       |
| `grafana.vathzen.in`     | `grafana:3000`               |                                       |
| `home.vathzen.in`        | `dynacat:8080`               |                                       |
| `pi.vathzen.in`          | `pihole:80`                  |                                       |
| `sonarr.vathzen.in`      | `sonarr:8989`                |                                       |
| `radarr.vathzen.in`      | `radarr:7878`                |                                       |
| `bazarr.vathzen.in`      | `bazarr:6767`                |                                       |
| `prowlarr.vathzen.in`    | `prowlarr:9696`              |                                       |
| `qbit.vathzen.in`        | `gluetun:8082`               | qBittorrent lives in gluetun's netns  |
| `tv.vathzen.in`          | `jellyfin:8096`              |                                       |
| `sparky.vathzen.in`      | `sparkyfitness-frontend:80`  |                                       |
| `kite-mcp.vathzen.in`    | `localhost:7070`             | Host process, not a container — see Known Issues |

Adding a service: add a `<name>.vathzen.in { reverse_proxy <container>:<port> }` block to `configs/Caddyfile`, copy it to `./containers/caddy/Caddyfile`, then reload:

```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

---

## Port Reference

| Service                  | Host Port | Container Port | Description                         |
|--------------------------|-----------|----------------|-------------------------------------|
| caddy                    | 80, 443   | 80, 443        | Reverse proxy (HTTP/HTTPS)          |
| pihole                   | 53        | 53             | DNS (TCP + UDP)                     |
| pihole                   | 8075      | 80             | Admin UI                            |
| pihole                   | 4431      | 443            | Admin HTTPS                         |
| samba                    | 139, 445  | 139, 445       | SMB file sharing                    |
| gluetun                  | 8082      | 8082           | qBittorrent WebUI (via gluetun)     |
| gluetun                  | 8000      | 8000           | Gluetun control server              |
| vaultwarden              | 8080      | 80             | Password manager                    |
| calibre-web              | 8083      | 8083           | E-book library                      |
| shelfmark                | 8084      | 8084           | Book search / ingest UI             |
| stirling-pdf             | 8090      | 8080           | PDF toolkit                         |
| cadvisor                 | 8070      | 8080           | Container metrics                   |
| prometheus               | 9090      | 9090           | Metrics collector                   |
| grafana                  | 3000      | 3000           | Metrics dashboards                  |
| dynacat                  | 8050      | 8080           | Homepage dashboard                  |
| sonarr                   | 8989      | 8989           | TV show manager                     |
| radarr                   | 7878      | 7878           | Movie manager                       |
| bazarr                   | 6767      | 6767           | Subtitle manager                    |
| prowlarr                 | 9696      | 9696           | Indexer manager                     |
| byparr                   | 8191      | 8191           | Cloudflare bypass proxy             |
| jellyfin                 | 8096      | 8096           | Media server (HTTP)                 |
| jellyfin                 | 7359/udp  | 7359/udp       | Client auto-discovery               |
| sparkyfitness-frontend   | 3004      | 80             | SparkyFitness web UI                |

Not published on the host: `cloudflare-ddns-home`, `node_exporter`, `claude-loan-tracker`, `sparkyfitness-db`, `sparkyfitness-server`, `qbittorrent` (reached through gluetun).

> Docker writes its own iptables rules for published ports, so these ports are reachable from the LAN regardless of UFW's default-deny policy.

---

## Infrastructure — `docker-compose.infra.yml`

### cloudflare-ddns-home
Keeps a Cloudflare DNS record pointed at the home public IP, for SSH into Artemis over the Internet. Not attached to `olympus_internal` (it only talks to Cloudflare).

- Image: `oznu/cloudflare-ddns:latest`

| Variable    | Source                    | Description                   |
|-------------|---------------------------|-------------------------------|
| `API_KEY`   | `${CLOUDFLARE_API_KEY}`   | Cloudflare API token          |
| `ZONE`      | `${ZONE}`                 | DNS zone (e.g. `vathzen.in`)  |
| `SUBDOMAIN` | `${SUBDOMAIN}`            | Record to update              |
| `PROXIED`   | `false`                   | Direct DNS, not proxied       |

### caddy
Reverse proxy and TLS terminator for every `*.vathzen.in` service (see the map above).

- Image: `caddybuilds/caddy-cloudflare:latest` (Caddy with the Cloudflare DNS module)
- Ports: `80`, `443`

| Mount                            | Purpose                          |
|----------------------------------|----------------------------------|
| `./containers/caddy/Caddyfile`   | Config (tracked at `configs/Caddyfile`) |
| `./containers/caddy/caddy_data`  | Certificates, ACME state         |
| `./containers/caddy/caddy_config`| Autosaved config                 |

| Variable               | Source                   | Description                  |
|------------------------|--------------------------|------------------------------|
| `CLOUDFLARE_API_TOKEN` | `${CLOUDFLARE_API_KEY}`  | ACME DNS-01 challenge        |
| `TAILNET_IP`           | `${TAILNET_IP}`          | Tailscale IP (currently not referenced in the Caddyfile) |

### pihole
DNS ad blocker and local resolver. All tailnet devices use it as their DNS server, so connecting to Tailscale removes ads (at a battery cost on mobile).

- Image: `pihole/pihole:latest`
- Data: `./containers/pihole → /etc/pihole`
- Ports: `53/tcp`, `53/udp`, `8075 → 80`, `4431 → 443`

| Variable                          | Source                    | Description           |
|-----------------------------------|---------------------------|-----------------------|
| `FTLCONF_webserver_api_password`  | `${PIHOLE_API_PASSWORD}`  | Web UI admin password |
| `FTLCONF_dns_listeningMode`       | `ALL`                     | Answer on all interfaces |

### samba
SMB file server exposing both drives to the network.

- Image: `crazymax/samba:latest`
- Config: `./containers/samba/config → /data` (tracked at `configs/samba_config.yml`, deployed as `config.yml`)
- Ports: `139`, `445`
- Global: `force user/group = zeus`, minimum protocol SMB2; shares are writable by `zeus` only, no guest access

| Variable          | Source               | Description                 |
|-------------------|----------------------|-----------------------------|
| `SAMBA_PASSWORD`  | `${SAMBA_PASSWORD}`  | Password for user `zeus`    |
| `SAMBA_LOG_LEVEL` | `1`                  | Log verbosity               |

| Share        | Host Path          | Device                                   |
|--------------|--------------------|------------------------------------------|
| `Cornucopia` | `/mnt/cornucopia`  | 4 TB Seagate HDD                         |
| `pandora`    | `/mnt/pandora`     | Data partition of the 512 GB NVMe (the same drive Artemis boots from) |

### gluetun
VPN client (ProtonVPN, WireGuard) that owns qBittorrent's network namespace. qBittorrent's WebUI port is therefore published on gluetun.

- Image: `qmcgaw/gluetun:v3` (pinned major)
- Requires `cap_add: NET_ADMIN` and `/dev/net/tun`
- Data: `./containers/gluetun → /gluetun`
- Ports: `8082` (qBittorrent WebUI), `8000` (control server)

| Variable                          | Value / Source               | Description                     |
|-----------------------------------|------------------------------|---------------------------------|
| `VPN_SERVICE_PROVIDER`            | `protonvpn`                  |                                 |
| `VPN_TYPE`                        | `wireguard`                  |                                 |
| `WIREGUARD_PRIVATE_KEY`           | `${WIREGUARD_PRIVATE_KEY}`   | WireGuard client key            |
| `WIREGUARD_ADDRESSES`             | `${WIREGUARD_ADDRESS}`       | Tunnel interface address        |
| `SERVER_COUNTRIES`                | `${VPN_SERVER_COUNTRY}`      | Exit country                    |
| `VPN_PORT_FORWARDING`             | `on`                         |                                 |
| `VPN_PORT_FORWARDING_PROVIDER`    | `protonvpn`                  |                                 |
| `PORT_FORWARD_ONLY`               | `yes`                        | Only use P2P / port-forwarding servers |
| `VPN_PORT_FORWARDING_UP_COMMAND`  | see below                    | Pushes the forwarded port to qBittorrent |

When the forwarded port is assigned, gluetun POSTs it to qBittorrent's API:

```bash
wget -O- -nv --retry-connrefused \
  --post-data 'json={"listen_port":{{PORT}}}' \
  http://127.0.0.1:8082/api/v2/app/setPreferences
```

---

## Applications — `docker-compose.apps.yml`

### vaultwarden
Self-hosted Bitwarden-compatible password manager.

- Image: `vaultwarden/server:latest`
- Data: `./containers/vaultwarden → /data`
- Port: `8080 → 80`
- URL: `https://vault.vathzen.in`

| Variable               | Value  | Description                                   |
|------------------------|--------|-----------------------------------------------|
| `DISABLE_ADMIN_TOKEN`  | `true` | `/admin` is reachable **without** a token     |

### calibre-web-automated
Calibre web UI with automatic ingest/conversion and Hardcover metadata sync. Proxied externally via Delphi so others can access the library.

- Image: `crocodilestick/calibre-web-automated:latest`
- Container name: `calibre-web`
- Port: `8083`
- URL: `https://calibre.vathzen.in` (plus plain HTTP)

| Mount                                   | Container Path      | Purpose                   |
|-----------------------------------------|---------------------|---------------------------|
| `./containers/calibre/calibre-config`   | `/config`           | App config                |
| `./containers/calibre/ingest`           | `/cwa-book-ingest`  | Drop folder for new books |
| `/mnt/cornucopia/books`                 | `/calibre-library`  | Calibre library           |

| Variable              | Value                 |
|-----------------------|-----------------------|
| `HARDCOVER_TOKEN`     | `${HARDCOVER_TOKEN}`  |
| `NETWORK_SHARE_MODE`  | `false`               |
| `PUID` / `PGID` / `TZ`| `1000` / `1000` / `Europe/Helsinki` |

### shelfmark
UI for finding new books; downloads land in the shared ingest folder, which calibre-web-automated picks up.

- Image: `ghcr.io/calibrain/shelfmark:latest`
- Port: `8084`
- URL: `https://shelfmark.vathzen.in`

| Mount                           | Container Path | Purpose                       |
|---------------------------------|----------------|-------------------------------|
| `./containers/calibre/ingest`   | `/books`       | Shared with calibre ingest    |
| `./containers/shelfmark`        | `/config`      | App config                    |

### loan-tracker
Personal education-loan payoff tracker. A stdlib-only Python server (`app.py`) that serves `index.html` and persists a single JSON ledger; all loan maths runs in the browser. Built locally — there is no published image.

- Build context: `./containers/loan-tracker` (source tracked in `loan-tracker/`: `Dockerfile`, `app.py`, `index.html`)
- Base image: `python:3.12-slim`
- Container name: `claude-loan-tracker`
- Runs as `1000:1000`
- No host port; reached only through Caddy
- URL: `https://loan.vathzen.in`

| Mount                                | Container Path | Purpose                          |
|--------------------------------------|----------------|----------------------------------|
| `./containers/loan-tracker/data`     | `/data`        | `loan.json` ledger (atomic writes) |

| Variable    | Value              |
|-------------|--------------------|
| `PORT`      | `8080`             |
| `DATA_FILE` | `/data/loan.json`  |
| `TZ`        | `Europe/Helsinki`  |

Endpoints: `GET /` (UI), `GET /api/state`, `PUT /api/state`, `GET /healthz`.

Rebuild after changing the source:

```bash
docker compose up -d --build loan-tracker
```

### stirling-pdf
Self-hosted PDF toolkit (merge, split, OCR, convert).

- Image: `stirlingtools/stirling-pdf:latest-fat`
- Port: `8090 → 8080`
- URL: `https://pdf.vathzen.in`

| Mount                                               | Container Path          |
|-----------------------------------------------------|-------------------------|
| `./containers/stirling-pdf/stirling-data/tessdata`  | `/usr/share/tessdata`   |
| `./containers/stirling-pdf/stirling-data/configs`   | `/configs`              |
| `./containers/stirling-pdf/stirling-data/logs`      | `/logs`                 |
| `./containers/stirling-pdf/stirling-data/pipeline`  | `/pipeline`             |

---

## Monitoring — `docker-compose.monitoring.yml`

### node_exporter
Host-level metrics (CPU, memory, disk, network) for Prometheus. Runs with `pid: host` and the host root mounted read-only at `/host` (`--path.rootfs=/host`). No published ports; scraped at `node_exporter:9100`.

- Image: `quay.io/prometheus/node-exporter:latest`

### cadvisor
Per-container resource metrics for Prometheus.

- Image: `gcr.io/cadvisor/cadvisor:latest`
- Port: `8070 → 8080`
- Mounts: `/` (ro), `/var/run` (rw), `/sys` (ro), `/var/lib/docker` (ro)

### prometheus
Scrapes and stores metrics every 15 s.

- Image: `prom/prometheus:latest`
- Config: `./containers/prometheus/config/prometheus.yml` (tracked at `configs/prometheus.yml`)
- Data: `./containers/prometheus/data → /prometheus`
- Port: `9090`
- URL: `https://prom.vathzen.in`

| Job             | Target                |
|-----------------|-----------------------|
| `prometheus`    | `localhost:9090`      |
| `node_exporter` | `node_exporter:9100`  |
| `cadvisor`      | `cadvisor:8080`       |

### grafana
Dashboards on top of Prometheus.

- Image: `grafana/grafana:latest`
- Data: `./containers/grafana → /var/lib/grafana`
- Port: `3000`
- URL: `https://grafana.vathzen.in`

### dynacat
Homepage dashboard. Discovers containers through the Docker socket and lists them by their `dynacat.*` labels.

- Image: `panonim/dynacat`
- Port: `8050 → 8080`
- URL: `https://home.vathzen.in`
- Env file: `./containers/dynacat/.env`

| Mount                            | Container Path          | Purpose                                     |
|----------------------------------|-------------------------|---------------------------------------------|
| `./containers/dynacat/config`    | `/app/config`           | Layout (tracked at `configs/dynacat_config.yml`) |
| `./containers/dynacat/assets`    | `/app/assets`           | Static assets                               |
| `/var/run/docker.sock`           | `/var/run/docker.sock`  | Container discovery (`:ro`)                 |
| `/etc/localtime`                 | `/etc/localtime`        | Host timezone (`:ro`)                       |

Dashboard layout: clock (Helsinki + Chennai), speedtest, container groups per `dynacat.category`, weather (Espoo), NIFTY 50 market widget, and server stats for Artemis.

Label schema used by every service:

```yaml
labels:
  dynacat.name: <Display Name>
  dynacat.icon: si:<simple-icons slug> | sh:<selfh.st slug>
  dynacat.url: https://<sub>.vathzen.in      # optional
  dynacat.category: Infrastructure | Applications | Monitoring | Media | SparkyFitness
```

---

## Media — `docker-compose.media.yml`

All download-handling services mount `/mnt/cornucopia` as `/data` — a single shared root, so imports from `/data/downloads` into `/data/media` are hardlinks rather than copies (hardlinks cannot cross filesystem or bind-mount boundaries).

Flow: Sonarr/Radarr → Prowlarr (+ Byparr) → qBittorrent (via gluetun) → hardlink import → Jellyfin scan; Bazarr fetches subtitles.

| Service      | Image                                  | Port         | Config                            | Media Mount                          | URL                          |
|--------------|----------------------------------------|--------------|-----------------------------------|--------------------------------------|------------------------------|
| sonarr       | `lscr.io/linuxserver/sonarr:latest`    | `8989`       | `./containers/sonarr/config`      | `/mnt/cornucopia → /data`            | `https://sonarr.vathzen.in`  |
| radarr       | `lscr.io/linuxserver/radarr:latest`    | `7878`       | `./containers/radarr/config`      | `/mnt/cornucopia → /data`            | `https://radarr.vathzen.in`  |
| bazarr       | `lscr.io/linuxserver/bazarr:latest`    | `6767`       | `./containers/bazarr/config`      | `/mnt/cornucopia → /data`            | `https://bazarr.vathzen.in`  |
| prowlarr     | `lscr.io/linuxserver/prowlarr:latest`  | `9696`       | `./containers/prowlarr/config`    | —                                    | `https://prowlarr.vathzen.in`|
| byparr       | `ghcr.io/thephaseless/byparr:latest`   | `8191`       | —                                 | —                                    | —                            |
| qbittorrent  | `lscr.io/linuxserver/qbittorrent:latest` | via gluetun `8082` | `./containers/qbittorrent/config` | `/mnt/cornucopia → /data`      | `https://qbit.vathzen.in`    |
| jellyfin     | `lscr.io/linuxserver/jellyfin:latest`  | `8096`, `7359/udp` | `./containers/jellyfin/config` | `/mnt/cornucopia/media → /data/media` (ro) | `https://tv.vathzen.in` |

### prowlarr
Central indexer manager; syncs indexers to Sonarr and Radarr. Deliberately **not** routed through the VPN.

### byparr
FlareSolverr-compatible proxy used by Prowlarr to get past Cloudflare challenges on indexers. `LOG_LEVEL=info`.

### qbittorrent
Torrent client for Sonarr and Radarr.

- `network_mode: service:gluetun` — all traffic, including the WebUI, goes through the VPN container; Sonarr/Radarr reach it at `gluetun:8082`
- Starts after gluetun (`depends_on: condition: service_started`)
- `WEBUI_PORT=8082`
- Listening port set dynamically by gluetun's port-forward hook
- Categories `sonarr` / `radarr` save to `/data/downloads/complete/{sonarr,radarr}/`

### jellyfin
Media server for the Sonarr/Radarr library. `/dev/dri` is passed through with the host `video` (`44`) and `render` (`992`) groups added. The Pi 5 has no hardware video encoder, so transcodes are CPU-bound.

| Variable                       | Value                    |
|--------------------------------|--------------------------|
| `JELLYFIN_PublishedServerUrl`  | `https://tv.vathzen.in`  |
| `PUID` / `PGID` / `TZ`         | `1000` / `1000` / `Europe/Helsinki` |

---

## SparkyFitness — `docker-compose.sparky.yml`

Self-hosted fitness and nutrition tracker. Variables come from `.env.sparky` (passed via `env_file` in the root `include`). All three services use `restart: always`.

### sparkyfitness-db
Postgres database for the backend.

- Image: `postgres:18.3-alpine`
- Data: `./containers/sparky/postgresql → /var/lib/postgresql`
- Not published on the host

| Variable            | Source                           |
|---------------------|----------------------------------|
| `POSTGRES_DB`       | `${SPARKY_FITNESS_DB_NAME}`      |
| `POSTGRES_USER`     | `${SPARKY_FITNESS_DB_USER}`      |
| `POSTGRES_PASSWORD` | `${SPARKY_FITNESS_DB_PASSWORD}`  |

### sparkyfitness-server
Backend API. Depends on `sparkyfitness-db`; listens on `3010` inside the network, not published on the host.

- Image: `codewithcj/sparkyfitness_server:latest`

| Mount                          | Container Path                        | Purpose                     |
|--------------------------------|---------------------------------------|-----------------------------|
| `./containers/sparky/backup`   | `/app/SparkyFitnessServer/backup`     | Backups                     |
| `./containers/sparky/uploads`  | `/app/SparkyFitnessServer/uploads`    | Profile and exercise images |

| Variable                                          | Description                                   |
|---------------------------------------------------|-----------------------------------------------|
| `SPARKY_FITNESS_LOG_LEVEL`                        | Server log level                              |
| `ALLOW_PRIVATE_NETWORK_CORS`                      | Allow CORS from private networks (default `false`) |
| `SPARKY_FITNESS_EXTRA_TRUSTED_ORIGINS`            | Extra trusted origins (default empty)         |
| `SPARKY_FITNESS_DB_HOST` / `SPARKY_FITNESS_DB_PORT` | DB host / `5432`                            |
| `SPARKY_FITNESS_DB_USER` / `_PASSWORD` / `_NAME`  | DB superuser credentials                      |
| `SPARKY_FITNESS_APP_DB_USER` / `_PASSWORD`        | Application-level DB role                     |
| `SPARKY_FITNESS_API_ENCRYPTION_KEY`               | API payload encryption key                    |
| `BETTER_AUTH_SECRET`                              | Auth signing secret                           |
| `SPARKY_FITNESS_FRONTEND_URL`                     | Public frontend URL                           |
| `SPARKY_FITNESS_DISABLE_SIGNUP`                   | Disable public sign-ups                       |
| `SPARKY_FITNESS_ADMIN_EMAIL`                      | This user gets the admin panel                |

### sparkyfitness-frontend
Web UI; talks to the backend over `olympus_internal`. Depends on `sparkyfitness-server`.

- Image: `codewithcj/sparkyfitness:latest`
- Port: `3004 → 80`
- URL: `https://sparky.vathzen.in`

| Variable                       | Value                             |
|--------------------------------|-----------------------------------|
| `SPARKY_FITNESS_FRONTEND_URL`  | `${SPARKY_FITNESS_FRONTEND_URL}`  |
| `SPARKY_FITNESS_SERVER_HOST`   | `sparkyfitness-server`            |
| `SPARKY_FITNESS_SERVER_PORT`   | `3010`                            |

---

## Outside Docker

### kite-mcp
Host-level process on Artemis listening on `7070`; files in `/mnt/pandora/kite-mcp-server`. Proxied by Caddy at `kite-mcp.vathzen.in`.

---

## Known Issues / TODO

- [ ] **`olympus_internal` declared twice.** The root file declares it as a managed bridge while every included file marks it `external: true`, so `docker compose down` deletes it and the next `up` fails. Make it external everywhere and create it once out-of-band.
- [ ] **Network name** still `olympus_internal` after the rename to Artemis. Renaming means editing all six compose files and recreating the network (full stack restart).
- [ ] **kite-mcp upstream.** `reverse_proxy localhost:7070` inside the Caddy container resolves to Caddy itself, not the host. Use `host.docker.internal:7070` with `extra_hosts: ["host.docker.internal:host-gateway"]` on caddy, or containerise kite-mcp.
- [ ] **Vaultwarden admin panel** is unauthenticated (`DISABLE_ADMIN_TOKEN=true`) and reachable from LAN, tailnet and port `8080`. Set an `ADMIN_TOKEN` (argon2 hash) and drop `DISABLE_ADMIN_TOKEN`.
- [ ] **Prometheus label typo:** `dyncat.url` → `dynacat.url` (no link on the dashboard).
- [ ] **Byparr** has `dynacat.url: https://byparr.vathzen.in` but no Caddyfile block. Either add one or drop the label (Byparr has no UI worth exposing).
- [ ] **SparkyFitness** sets `GUID` instead of `PGID` (ignored by all three images). Remove or correct.
- [ ] **SparkyFitness MCP** was removed from the stack, but `SPARKY_FITNESS_MCP_PORT=3001` is still in `.env.sparky.example`.
- [ ] **Caddy `TAILNET_IP`** is passed in but unused; Caddy binds `0.0.0.0:80/443`. Either bind to it in the Caddyfile or remove the variable.
- [ ] **loan-tracker build context** points at `./containers/loan-tracker` while the source is tracked in `loan-tracker/`. Point `build:` at `./loan-tracker` so the repo is the single source of truth.
- [ ] **Dynacat Docker socket** is mounted `:ro`, which does not restrict the Docker API — the container effectively has root on Artemis. Consider a socket proxy (e.g. `tecnativa/docker-socket-proxy` with `CONTAINERS=1` only).
- [ ] **`:latest` tags** on most images. Pin versions where regressions are known (gluetun already pinned to `v3`).