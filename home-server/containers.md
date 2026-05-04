# Home Server Containers

All services are defined across four compose files, included from the root `docker-compose.yml`.

```
docker-compose.yml
├── docker-compose.infra.yml       # Networking & file sharing
├── docker-compose.apps.yml        # Self-hosted applications
├── docker-compose.monitoring.yml  # Observability stack
└── docker-compose.media.yml       # Media automation
```

---

## Port Reference

| Service         | Host Port | Container Port | Description              |
|-----------------|-----------|----------------|--------------------------|
| caddy           | 80, 443   | 80, 443        | Reverse proxy (HTTP/HTTPS) |
| pihole          | 53        | 53             | DNS (TCP + UDP)          |
| pihole          | 8075      | 80             | Admin UI                 |
| pihole          | 4431      | 443            | Admin HTTPS              |
| samba           | 139, 445  | 139, 445       | SMB file sharing         |
| vaultwarden     | 8080      | 80             | Password manager         |
| calibre-web     | 8083      | 8083           | E-book library           |
| shelfmark       | 8084      | 8084           | Book ingestion UI        |
| qbittorrent     | 8082      | 8082           | Torrent client WebUI     |
| qbittorrent     | 6881      | 6881           | BitTorrent (TCP + UDP)   |
| sonarr          | 8989      | 8989           | TV show manager          |
| radarr          | 8990      | 8990           | Movie manager            |
| prowlarr        | 9696      | 9696           | Indexer manager          |
| cadvisor        | 8070      | 8080           | Container metrics        |
| prometheus      | 9090      | 9090           | Metrics collector        |
| grafana         | 3000      | 3000           | Metrics dashboards       |
| gluetun         | 8000      | 8000           | VPN Client for QBit      |

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

All media services share `/mnt/cornucopia` on the host for downloads and library storage.

### sonarr
Monitors and manages TV show downloads.

- Port: `8989`
- Config: `./containers/sonarr/config`

| Mount                          | Purpose          |
|--------------------------------|------------------|
| `/mnt/cornucopia/media/tv`     | TV library       |
| `/mnt/cornucopia/downloads`    | Download staging |

### radarr
Monitors and manages movie downloads.

- Port: `8990`
- Config: `./containers/radarr/config`

| Mount                          | Purpose          |
|--------------------------------|------------------|
| `/mnt/cornucopia/media/movies` | Movie library    |
| `/mnt/cornucopia/downloads`    | Download staging |

### prowlarr
Centralized indexer manager that syncs indexers to Sonarr and Radarr.

- Config: `./containers/prowlarr/config`
- Port: `9696`

### qbittorrent
Torrent client used by Sonarr and Radarr for downloads.

- Config: `./containers/qbittorrent/config`
- WebUI port: `8082`
- BitTorrent port: Set from Gluetun Startup Config

| Mount                       | Purpose        |
|-----------------------------|----------------|
| `/mnt/cornucopia/downloads` | Download folder |
