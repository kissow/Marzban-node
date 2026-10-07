# Marzban-node

## MR-20261008-NODE-RELAY-SOURCES（镜像已发布，服务器/视觉验收待完成）

连接方式采用原React/Chakra独立管理弹窗和原信息图标。可选择Marzban主服务器或另一台源Node中转到目标Node；保留原订阅别名、顺序、数量，只替换精确匹配的端点，不新增Relay。目标认证、设备凭据和出口不变。自转发/环路/占用/能力/精确ACK/失败回滚、来源隔离与恢复有回归测试。

管理API增加source/source_node_id/来源列表，additive迁移9012ab34cd56；Node新增managed-node-relay-v1、原认证REST/RPyC完整快照与独立转发进程。固定Xray26.3.27，原证书、控制/API端口、用户、.env与数据卷保留。首版VLESS TCP/RAW REALITY、IPv4/DNS-only入口、单跳选择，不是所有协议或任意UDP转发；每源512个配置不是吞吐承诺。

本地最终代码和独立发布副本再次复测：主控164/164、Node60/60（准备固定Xray，无跳过）、前端47/47、类型/生产构建、依赖/diff通过。干净Linux CI与两镜像双架构发布核对完成；真实跨服务器mTLS、公网吞吐、多引擎数据库、实际原组件UI截图仍待验收，不标稳定版。UI截图因浏览器策略blocked，未绕过。

主控revision 93bfbb5b17dd8ee731449976df1a4af4e0f57ca5，Actions37657985804；Node revision 7b45fc0dc3b4451045a06123b52ccdaaa5911b8d，Actions37657976968。scripts合并ed274ba82410f9e6f580cbec59b2a15a89ab81ea，Actions37657994843成功，脚本运行时不变。先在承担来源的Node运行marzban-node update，再在主控运行marzban update；仅作目标的既有配对Node不强制更新。新Node沿用仓库install，现在拉取新latest；旧机不重装、不删卷、不重复adopt。源业务入口TCP需放行，客户端刷新订阅。

[精确配对SHA、index/架构/config摘要、接口与SSH验收证据](https://github.com/kissow/Marzban/blob/master/docs/NODE_RELAY_SOURCES_RELEASE.md)。下方旧记录只描述各自日期的阶段，不代替本轮最新状态；文档[skip ci]提交不改变已核对的运行时镜像revision。


> **Current release (2026-10-03, MR-20261003-EGRESS-UDP):** Paired panel/Node code and multiarchitecture latest images are published and OCI revisions verified. [Source SHAs, successful Actions and exact image digests](docs/egress-udp-release.md). Server/provider/mobile/UI screenshot acceptance remains pending; this is not a stable-release claim. Update Node first, then panel. Scripts runtime, certificates, ports, volumes and pinned Xray v26.3.27 are unchanged. Legacy remains default. TCP-only DNS is not arbitrary UDP-to-TCP conversion. [Wire contract and acceptance](docs/egress-udp.md).

> **Historical release (2026-10-03, HWID compatibility):** Source commit `c135743d1ad26d45538e4c6c7a65a9c6693856a8`, Actions `37090612247`, image index `sha256:21340918298f0b8647fb7eb360294334891fc219e280a75af5d133c66ee9fbc1`. Its runtime-unchanged note does not apply to the current UDP feature, which requires Node update. This historical digest is not current latest.

> **Mr.shaw community fork:** This repository preserves the upstream Marzban-Node project and adds node health reporting plus one managed HTTP/SOCKS outbound per Node. Read [Fork features](FORK_FEATURES.md), the [Changelog](CHANGELOG.md), and [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md). The current image includes online-user queries and device-policy acknowledgement/credential loading; [the contract and limitations](docs/activity-and-policy.md) distinguish subscription registration from direct connection enforcement. The image is published and awaiting server acceptance.

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
