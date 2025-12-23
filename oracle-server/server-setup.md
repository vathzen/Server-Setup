# Server Setup for Oracle Cloud
#### Open Port 80 to Public
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo netfilter-persistent save
sudo systemctl restart nginx
```
TODO: Read about IP Tables

#### Install Go
```bash
wget https://go.dev/dl/go1.19.13.linux-amd64.tar.gz
sudo tar -xzvf go.tar.gz -C /usr/local
echo export PATH=$HOME/go/bin:/usr/local/go/bin:$PATH >> ~/.zshrc
echo export GOPATH=$HOME/go/build >> ~/.zshrc
```

#### Install Discord Bots
Set API Tokens in `.zshrc`

Fetch Git Repos then do:
```bash
go get
go install
```

#### Install Node using NVM
```bash
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
nvm install stable
```
I use `pm2` for Process Management:
```bash
npm install pm2
pm2 start <botname>
```

#### Finally 
