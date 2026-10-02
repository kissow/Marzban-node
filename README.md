# Marzban-node

> **Mr.shaw community fork:** This repository preserves the upstream Marzban-Node project and adds node health reporting plus one managed HTTP/SOCKS outbound per Node. Read [Fork features](FORK_FEATURES.md), the [Changelog](CHANGELOG.md), and [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md). Local development adds online-user queries and device-policy acknowledgement; [the contract and limitations](docs/activity-and-policy.md) distinguish subscription registration from direct connection enforcement. These changes are unpublished; direct connections are not yet device-limited.

Every Node code, protocol, Xray-core, configuration, UI-facing contract, or documentation change must be registered with the paired `kissow/Marzban` and `kissow/Marzban-scripts` records. The Node is not considered released until the protocol notes, paired commit, tests, Actions result, GHCR digest, and server acceptance status are recorded. If a change does not affect the Node channel, explicitly record that the channel, certificates, ports, and data are unchanged.

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

## Interface and release record

The canonical cross-repository interface list is [`../09-接口登记索引.md`](../09-接口登记索引.md).
Before changing a REST/RPyC method, health snapshot field, `marzban_node_extensions`
field, Xray preflight rule, certificate/port behavior, or installation command, update
that index, this README, `CHANGELOG.md`, and the paired Marzban and Marzban-scripts
records in the same change. The required change card and evidence fields are defined in
[`../08-跨仓库更新登记模板.md`](../08-跨仓库更新登记模板.md).

For every release, record the Node commit, paired panel commit, scripts commit, image
tag and GHCR digest, GitHub Actions run, fixed Xray version, protocol compatibility,
backup path, and server acceptance result. A UI-only or documentation-only change must
explicitly state that the Node channel, certificates, ports, data directories, and API
behavior are unchanged. Do not mark a release as published until the cross-repository
gate in the interface index is complete.
