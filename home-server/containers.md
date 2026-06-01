# Home Server Containers

All services are defined across compose files, included from the root `docker-compose.yml`. All services attach to the external `olympus_internal` bridge network.

```
docker-compose.yml
├── docker-compose.infra.yml       # Networking & file sharing
├── docker-compose.apps.yml        # Self-hosted applications
├── docker-compose.monitoring.yml  # Observability stack
├── docker-compose.media.yml       # Media automation
└── docker-compose.sparky.yml      # SparkyFitness stack
```

---

## Port Reference

| Service         | Host Port | Container Port | Description                        |
|-----------------|-----------|----------------|------------------------------------|
| caddy           | 80, 443   | 80, 443        | Reverse proxy (HTTP/HTTPS)         |
| pihole          | 53        | 53             | DNS (TCP + UDP)                    |
| pihole          | 8075      | 80             | Admin UI                           |
| pihole          | 4431      | 443            | Admin HTTPS                        |
| samba           | 139, 445  | 139, 445       | SMB file sharing                   |
| vaultwarden     | 8080      | 80             | Password manager                   |
| calibre-web     | 8083      | 8083           | E-book library                     |
| shelfmark       | 8084      | 8084           | Book ingestion UI                  |
| qbittorrent     | 8082      | 8082           | Torrent client WebUI (via gluetun) |
| sonarr          | 8989      | 8989           | TV show manager                    |
| radarr          | 7878      | 7878           | Movie manager                      |
| bazarr          | 6767      | 6767           | Subtitle manager                   |
| prowlarr        | 9696      | 9696           | Indexer manager                    |
| byparr          | 8191      | 8191           | Cloudflare bypass proxy            |
| jellyfin        | 8096      | 8096           | Media server (HTTP)                |
| jellyfin        | 7359/udp  | 7359/udp       | Client auto-discovery              |
| cadvisor        | 8070      | 8080           | Container metrics                  |
| prometheus      | 9090      | 9090           | Metrics collector                  |
| grafana         | 3000      | 3000           | Metrics dashboards                 |
| gluetun         | 8000      | 8000           | VPN control server                 |
| sparkyfitness-frontend | 3004 | 80           | SparkyFitness web UI               |
| sparkyfitness-mcp | 3001    | 3001           | SparkyFitness MCP server           |

---

## Infrastructure — `docker-compose.infra.yml`

### cloudflare-ddns-home
Updates a Cloudflare DNS record with the current public IP. Useful to SSH to the RPi via Internet.

| Variable             | Description                       |
|----------------------|-----------------------------------|
| `CLOUDFLARE_API_KEY` | Cloudflare API key                |
| `ZONE`               | DNS zone (e.g. `example.com`)     |
| `SUBDOMAIN`          | Subdomain to update               |
| `PROXIED`            | Set to `false` (direct DNS)       |

### caddy
Reverse proxy with automatic HTTPS via Cloudflare DNS challenge. Entry point for all internal services exposed over Tailscale.

- Config: `./containers/caddy/Caddyfile`

| Variable               | Description                    |
|------------------------|--------------------------------|
| `CLOUDFLARE_API_TOKEN` | Used for ACME DNS challenge    |
| `TAILNET_IP`           | Tailscale IP to bind to        |

### pihole
DNS-based ad blocker and local DNS resolver. All Devices in Tailscale use the Pihole as the DNS server; thus connecting to Tailscale removes ads. But the battery drain is painful ;(

- Data: `./containers/pihole`

| Variable                          | Description              |
|-----------------------------------|--------------------------|
| `FTLCONF_webserver_api_password`  | Web UI admin password    |
| `FTLCONF_dns_listeningMode`       | Set to `ALL`             |

### samba
SMB file server exposing Seagate and NVMe drives to the network.

- Config: `./containers/samba/config`

| Variable          | Description                   |
|-------------------|-------------------------------|
| `SAMBA_PASSWORD`  | Share password                |
| `SAMBA_LOG_LEVEL` | Log verbosity (default `1`)   |

| Host Path           | Shared As           |
|---------------------|---------------------|
| `/mnt/cornucopia`   | `/mnt/cornucopia`   |
| `/mnt/pandora`      | `/mnt/pandora`      |

### gluetun
VPN Client that QBittorent uses to acquire content. Connected to ProtonVPN Wireguard client.

| Variable                      | Description                    |
|-------------------------------|--------------------------------|
| `WIREGUARD_PRIVATE_KEY`       | Wireguard Client Identifier    |
| `WIREGUARD_ADDRESS`           | VPN Server IP to bind to       |
| `VPN_SERVER_COUNTRY`          | Country to tunnel to           |

Sends a POST Request to QBittorrent with the data
```python
{"listen_port":{{PORTS}}
``` 
to set the port which qbittorrent should use.

---

## Applications — `docker-compose.apps.yml`

### vaultwarden
Self-hosted Bitwarden-compatible password manager.

- Data: `./containers/vaultwarden`
- Port: `8080`

| Variable               | Description                     |
|------------------------|---------------------------------|
| `DISABLE_ADMIN_TOKEN`  | `true` — admin panel enabled    |

### calibre-web-automated
Calibre web interface with automatic book processing and Hardcover sync. This is proxied to my website to allow access for externals.

- Port: `8083`

| Variable          | Description                   |
|-------------------|-------------------------------|
| `HARDCOVER_TOKEN` | API token for Hardcover sync  |
| `PUID` / `PGID`   | `1000` / `1000`               |
| `TZ`              | `Europe/Helsinki`             |

| Mount                                 | Purpose                  |
|---------------------------------------|--------------------------|
| `./containers/calibre/calibre-config` | App config               |
| `./containers/calibre/ingest`         | Drop folder for new books |
| `./containers/calibre/books`          | Calibre library          |

### shelfmark
UI for "browsing" new books. Shares the ingest directory with calibre-web.

- Config: `./containers/shelfmark`
- Ingest: `./containers/calibre/ingest`
- Port: `8084`

---

## Monitoring — `docker-compose.monitoring.yml`

### node_exporter
Exports host-level system metrics (CPU, memory, disk, network) for Prometheus. Runs in `pid: host` mode with the host root mounted read-only. No exposed ports.

### cadvisor
Exports per-container resource metrics for Prometheus.

- Port: `8070`

### prometheus
Scrapes and stores metrics from node_exporter and cadvisor.

- Config: `./containers/prometheus/config/prometheus.yml`
- Data: `./containers/prometheus/data`
- Port: `9090`

### grafana
Visualization layer for Prometheus metrics.

- Data: `./containers/grafana`
- Port: `3000`

---

## Media — `docker-compose.media.yml`

All media services mount `/mnt/cornucopia` on the host as `/data` for downloads and library storage (single shared root so hardlinks work across staging and libraries).

### sonarr
Monitors and manages TV show downloads.

- Port: `8989`
- Config: `./containers/sonarr/config`
- Mount: `/mnt/cornucopia → /data`

### radarr
Monitors and manages movie downloads.

- Port: `7878`
- Config: `./containers/radarr/config`
- Mount: `/mnt/cornucopia → /data`

### bazarr
Subtitle manager that pairs with Sonarr and Radarr.

- Port: `6767`
- Config: `./containers/bazarr/config`
- Mount: `/mnt/cornucopia → /data`

### prowlarr
Centralized indexer manager that syncs indexers to Sonarr and Radarr.

- Config: `./containers/prowlarr/config`
- Port: `9696`

### byparr
FlareSolverr-compatible proxy used by Prowlarr to bypass Cloudflare challenges on indexers.

- Port: `8191`
- Env: `LOG_LEVEL=info`

### qbittorrent
Torrent client used by Sonarr and Radarr for downloads. Runs inside the Gluetun network namespace, so all traffic and its WebUI are routed via the VPN container.

- Config: `./containers/qbittorrent/config`
- Network: `network_mode: service:gluetun` (WebUI reachable on host port `8082` via gluetun)
- BitTorrent port: set dynamically from Gluetun's forwarded port
- Mount: `/mnt/cornucopia → /data`

### jellyfin
Media server for streaming the Sonarr/Radarr library. Hardware-accelerated transcoding via `/dev/dri`, with the host `video` (`44`) and `render` (`992`) groups added.

- Ports: `8096` (HTTP), `7359/udp` (client discovery)
- Config: `./containers/jellyfin/config`
- Library mount: `/mnt/cornucopia/media → /data/media` (read-only)

| Variable                         | Description                          |
|----------------------------------|--------------------------------------|
| `JELLYFIN_PublishedServerUrl`    | `https://tv.vathzen.in`              |
| `PUID` / `PGID`                  | `1000` / `1000`                      |
| `TZ`                             | `Europe/Helsinki`                    |

---

## SparkyFitness — `docker-compose.sparky.yml`

Self-hosted fitness/nutrition tracking stack. Loaded with its own env file (`.env.sparky`) from the root compose file. All four services attach to the shared `olympus_internal` network.

### sparkyfitness-db
Postgres 18.3 (alpine) database backing the SparkyFitness server and MCP.

- Image: `postgres:18.3-alpine`
- Data: `${DB_PATH:-./postgresql} → /var/lib/postgresql`
- Not exposed on the host (commented-out `5432` mapping).

| Variable                      | Description                  |
|-------------------------------|------------------------------|
| `SPARKY_FITNESS_DB_NAME`      | Postgres database name       |
| `SPARKY_FITNESS_DB_USER`      | Postgres superuser           |
| `SPARKY_FITNESS_DB_PASSWORD`  | Postgres password            |

### sparkyfitness-server
Backend API (container name `sparkyfitness-backend`). Depends on `sparkyfitness-db`.

- Image: `codewithcj/sparkyfitness_server:latest`
- Mounts: `${SERVER_BACKUP_PATH:-./backup} → /app/SparkyFitnessServer/backup`, `${SERVER_UPLOADS_PATH:-./uploads} → /app/SparkyFitnessServer/uploads`
- Internal only (no host port)

| Variable                                  | Description                                  |
|-------------------------------------------|----------------------------------------------|
| `SPARKY_FITNESS_LOG_LEVEL`                | Server log level                             |
| `ALLOW_PRIVATE_NETWORK_CORS`              | Allow CORS from private networks (default `false`) |
| `SPARKY_FITNESS_EXTRA_TRUSTED_ORIGINS`    | Extra trusted CORS origins                   |
| `SPARKY_FITNESS_DB_HOST` / `_PORT`        | DB host / port (`5432`)                      |
| `SPARKY_FITNESS_DB_USER` / `_PASSWORD` / `_NAME` | DB credentials                        |
| `SPARKY_FITNESS_APP_DB_USER` / `_PASSWORD`| Application-level DB role                    |
| `SPARKY_FITNESS_API_ENCRYPTION_KEY`       | API payload encryption key                   |
| `BETTER_AUTH_SECRET`                      | Auth signing secret                          |
| `SPARKY_FITNESS_FRONTEND_URL`             | Public frontend URL                          |
| `SPARKY_FITNESS_DISABLE_SIGNUP`           | Disable public signups                       |
| `SPARKY_FITNESS_ADMIN_EMAIL`              | Admin user email                             |

### sparkyfitness-frontend
Web UI for SparkyFitness. Talks to the backend over the internal network.

- Image: `codewithcj/sparkyfitness:latest`
- Port: `3004 → 80`

| Variable                        | Description                           |
|---------------------------------|---------------------------------------|
| `SPARKY_FITNESS_FRONTEND_URL`   | Public frontend URL                   |
| `SPARKY_FITNESS_SERVER_HOST`    | `sparkyfitness-server`                |
| `SPARKY_FITNESS_SERVER_PORT`    | `3010`                                |

### sparkyfitness-mcp
MCP server exposing SparkyFitness over HTTP transport for AI assistants.

- Image: `codewithcj/sparkyfitness_mcp:latest`
- Port: `3001`
- Env: same DB credentials as the server, plus `BETTER_AUTH_SECRET` and `MCP_TRANSPORT=http`
