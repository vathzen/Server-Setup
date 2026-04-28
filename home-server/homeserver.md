# Olympus
Home Server Setup Guide so that I don't forget what the fuck I did.

### Tools installed:
```bash
build-essentials
```

### Software Packages
btop
tree

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

### Paths
All docker containers store their files in the `./containers/<container>/` workspace. Listed are the files that are commited to track changes and the paths they go in.

- `./configs/Caddyfile -> ./containers/caddy/`
- `./configs/prometheus.yml -> ./containers/prometheus/config/`
- `./configs/config.yml -> ./containers/samba/config/`
