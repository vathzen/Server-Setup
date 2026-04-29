# Olympus
Home Server Setup Guide so that I don't forget what the fuck I did.

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

### Disk Setup
Set Drive standby to 30 mins - Drive stops spinning and parks after 30 mins if there is no activity:
```bash
zeus@olympus ➜  ~  sudo hdparm -S 241 /dev/disk/by-label/Cornucopia
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
- `-o on -S on`: Drive's inbuild background scanning and attribute autosave
- `-s (S/../.././02|L/../../6/03)`: Schedule a *S*hort test every day at 2 and a comprehensive (*L*) test every Sunday (*6*) at 2.
- `-W 4,50,60`: Warn at 4°C jump, small alert at 50°C, big alert at 60°C.
- `-m root -m exec /home/zeus/docker/containers/samba/smartd_warning.sh`: Run the script as root when there is an error.

### Paths
All docker containers store their files in the `./containers/<container>/` workspace. Listed are the files that are commited to track changes and the paths they go in.

- `./configs/Caddyfile -> ./containers/caddy/`
- `./configs/prometheus.yml -> ./containers/prometheus/config/`
- `./configs/config.yml -> ./containers/samba/config/`
