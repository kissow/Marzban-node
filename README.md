# Marzban-node

> **Mr.shaw community fork:** This repository preserves the upstream Marzban-Node project and adds node health reporting plus one managed HTTP/SOCKS outbound per Node. Read [Fork features](FORK_FEATURES.md) and the [Changelog](CHANGELOG.md). Device limiting is planned for a later release.

## Quick install
Install Marzban-node on your server using this command
```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban-node.sh)" @ install
```
Install Marzban-node on your server using this command with custom name:
```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban-node.sh)" @ install --name marzban-node2
```
Or you can only install this script (marzban-node command) on your server by using this command
```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban-node.sh)" @ install-script
```

Use `help` to view all commands:
```marzban-node help```


## Manual install
Read the setup guide here: https://gozargah.github.io/marzban/docs/marzban-node

## Residential outbound setup

The Node does not require a separate residential-proxy program. Install Docker,
run the normal one-click Node installer, and keep the existing certificate,
service port and Xray API port. Configure the residential HTTP/SOCKS5 endpoint
in the paired Marzban panel; the panel sends the Node-specific setting through
the existing authenticated channel. The Node validates the generated Xray
configuration before restart. If no endpoint is configured, the Node behaves
like the upstream release.

For an existing official installation, switch it without deleting the current
certificate, ports or data:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/kissow/Marzban-scripts/master/marzban-node.sh)" @ adopt
```
