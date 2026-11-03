# Artemis
Home Server Setup Guide so that I don't forget what the fuck I did.

Artemis (formerly Olympus) — Raspberry Pi 5 (4 GB), Raspberry Pi OS on Debian 13 (trixie), user `zeus`. Container stack: see [`containers.md`](./containers.md).

### Tools installed:
```bash
build-essentials
btop
tree
smartmontools
hdparm
```

### SSH Setup
Edit /etc/ssh/sshd_config and change:

```bash
Port 22 # Change
PubkeyAuthentication yes
PasswordAuthentication no
```

### Install VIM
TinyVi had problems with the arrow keys.

### ZSH Setup
```bash
sudo apt install zsh
sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

Edit the theme to add:
```bash
PROMPT="%{$fg_bold[magenta]%}%n@%m %{$reset_color%}%(?:%{$fg_bold[green]%}%1{➜%} :%{$fg_bold[red]%}%1{➜%} ) %{$fg[cyan]%}%c%{$reset_color%} "
```

### Boot & Storage Layout
Artemis boots from the 512 GB NVMe (PCIe HAT). The SD card it used to boot from has been removed.

| Device | Partition | FS | Label | Mount | Purpose |
|--------|-----------|----|-------|-------|---------|
| 512 GB NVMe | p1 (512 MiB) | FAT32 | `nvme-boot` | `/boot/firmware` | Firmware / kernel |
| 512 GB NVMe | p2 (64 GiB) | ext4 | `nvme-root` | `/` | OS |
| 512 GB NVMe | p3 (~412 GiB) | ext4 (`-m 0`) | `pandora` | `/mnt/pandora` | Data, containerd root |
| 4 TB Seagate HDD (USB) | p1 | ext4 (`-m 0`) | `Cornucopia` | `/mnt/cornucopia` | Media, downloads, books |

- NVMe partition table is MBR (PTUUID `22f1b2fb`); `fstab` and `cmdline.txt` reference partitions as `PARTUUID=22f1b2fb-0N`.
- EEPROM `BOOT_ORDER=0xf461` (SD → NVMe → USB), kept deliberately: inserting a recovery SD card boots it without touching the EEPROM.
- PCIe Gen 3 enabled in `config.txt` with `dtparam=pciex1_gen=3` (link verified at 8 GT/s x1, no AER errors).
- HDD fstab options: `defaults,nofail,noatime,x-systemd.device-timeout=30`.
- HDD UAS quirk in `/boot/firmware/cmdline.txt`: `usb-storage.quirks=0bc2:203a:u`.
- containerd root is on `/mnt/pandora/containerd`; Docker's `data-root` stays at the default `/var/lib/docker`.
- `docker.service` has a systemd drop-in with `RequiresMountsFor=/mnt/cornucopia`, so Docker never bind-mounts the bare mountpoint before the HDD is mounted.

### Disk Setup
Set Drive standby to 30 mins - Drive stops spinning and parks after 30 mins if there is no activity:
```bash
zeus@artemis ➜  ~  sudo hdparm -S 241 /dev/disk/by-label/Cornucopia
/dev/disk/by-label/Cornucopia: setting standby to 241 (30 minutes)
```

Setup `smartd` for monitoring the disk:
```bash
sudo vi /etc/smartd.conf
# Add this line AFTER commenting DEVICESCAN
/dev/disk/by-label/Cornucopia -d sat -a -o on -S on -s (S/../.././02|L/../../6/03) -W 4,50,60 -m root -M exec /home/zeus/docker/containers/samba/smartd_warning.sh
sudo smartd -q onecheck
```

Explanation:
- `-d sat`: Use SAT bridge to translate SATA commands (smartd) to USB
- `-a`: All standard health checks
- `-o on -S on`: Drive's inbuilt background scanning and attribute autosave
- `-s (S/../.././02|L/../../6/03)`: *S*hort test every day at 02:00, *L*ong test every **Saturday** at 03:00 (smartd numbers weekdays `1`=Mon … `7`=Sun; use `7` for Sunday)
- `-W 4,50,60`: Warn at 4°C jump, small alert at 50°C, big alert at 60°C.
- `-m root -M exec /home/zeus/docker/containers/samba/smartd_warning.sh`: Run the script instead of mailing root when there is an error.

TODO: the NVMe is not in `smartd.conf` yet.

### Paths
The compose project lives at `/home/zeus/docker`. All containers store their files in `./containers/<container>/`. Tracked files and where they are deployed:

- `./configs/Caddyfile -> ./containers/caddy/Caddyfile`
- `./configs/prometheus.yml -> ./containers/prometheus/config/prometheus.yml`
- `./configs/samba_config.yml -> ./containers/samba/config/config.yml`
- `./configs/dynacat_config.yml -> ./containers/dynacat/config/` (as the config file Dynacat expects)
- `./loan-tracker/{Dockerfile,app.py,index.html} -> ./containers/loan-tracker/`
- `./.env.example -> ./.env`, `./.env.sparky.example -> ./.env.sparky` (fill in secrets; never commit)