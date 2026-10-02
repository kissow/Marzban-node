# Marzban-Node 发布清单

## MR-20261002-01 镜像发布核对（服务器验收待完成）

- [x] 本地 Python 3.12 完整 39 项测试通过，设置 `XRAY_TEST_BINARY` 后无跳过项。
- [x] 真实固定 Xray 26.3.27 验证 TLS Stats、VLESS 在线用户出现/消失、不清零计费以及 4 种 HTTP/SOCKS 配置。
- [x] 原子策略替换、认证会话、错误输入、即时健康确认和旧核心回退均有测试。
- [x] CI 增加固定核心实测步骤；接口合同和配对主面板文档更新。
- [x] Linux Actions 和发布镜像已完成；服务器验收尚未执行。

发布证据：Node `master` commit `d6f3bec204a75085939b5b4e25fa6502f5946ae5`，Actions `36975383911` 成功，GHCR index `sha256:f2a9e93ca3168abb3559f3e48baa98d02e6377fb8d4a480407f447a97bbbf774`；amd64 `sha256:81965a75de1bc07f5948bb42ea216d5cd80be36bca152641c41c0bf7820c0bc3`，arm64 `sha256:6d82315f1b73a0cd75b7c5ac2f5c3163d4fab10304a54fe8c250e461a4da63cd`。配对主面板 commit `a6efaa8eafd82c3f68d2ff29074cf9eeb1ec8ae0`，正式 Xray `v26.3.27`。

本清单适用于 `kissow/Marzban-node` 的每一次 Node 通道、健康指标、Xray 配置、住宅出口、核心版本、脚本或文档更新。涉及主面板下发协议时，必须和 `kissow/Marzban` 配对记录。

## 变更登记

- [x] 已记录 Node commit、配对主面板 commit、脚本 commit、分支和发布状态。
- [x] 已标记是否修改认证 REST/RPyC 通道、能力标识、配置字段、Xray 核心、证书、服务端口或 API 端口。
- [x] 已明确旧版 Node 的兼容行为；不新增公网监控端口，不覆盖证书和现有数据卷。
- [ ] 没有提交 `_patch-node.tmp`、日志、证书私钥、Token、代理密码或生产配置。

## 协议和配置

- [x] 新增或修改的 Node 方法、请求、响应、错误和能力标识已同步到主面板接口文档及 CHANGELOG。
- [ ] Xray 配置有 JSON 预检；失败时不会先停止当前核心，失败日志不泄露密码。
- [ ] HTTP/SOCKS 出站的 TCP/UDP 路由、认证、DNS、恢复直连和删除出站行为有测试。
- [ ] 如果只改 Node 文档或脚本，明确写出主面板通道和运行时无变化。

## 测试

- [ ] `python -B -m unittest discover -s tests -v`
- [ ] 已用配套 Xray 二进制验证核心版本和最终 JSON；正式基线当前为 `v26.3.27`。
- [ ] 已测试健康快照、过期/离线、重连、配置失败回滚和多 Node 隔离。
- [ ] 已测试 Node 证书、服务端口、API 端口、订阅和原有入站功能不受影响。
- [ ] 已在隔离 Linux Node 与主面板完成真实认证联调，再决定是否进入正式镜像。

## CI、镜像和发布

- [x] GitHub Actions 成功，记录 run ID、源 commit、架构和失败重试结果。
- [x] `ghcr.io/kissow/marzban-node` 的 tag/index digest 和 OCI revision 与预期 Node commit 匹配。
- [x] 主面板需要同步发布时，两个仓库的配对 SHA、协议兼容范围和升级顺序已记录。
- [x] `CHANGELOG.md`、`FORK_FEATURES.md`、README、开发计划和项目验收清单状态一致。

## 服务器验收与回滚

- [ ] 每台 Node 更新前备份证书、Compose、配置和数据目录，记录位置和校验。
- [ ] 官方旧安装只执行 `adopt`；已切 Fork 的 Node 只执行 `update`；新 Node 才执行 `install`。
- [ ] 更新后验证 `marzban-node status`、日志、Xray 实际版本、主面板连接、节点订阅和出站公网 IP。
- [ ] 明确回滚镜像/tag 和配置恢复方式；不删除 `/var/lib/marzban-node`，不重建证书。

## 发布记录最小字段

```text
Node commit：
配对主面板 commit：
脚本 commit：
Actions run：
GHCR index/架构 digest：
OCI revision：
能力标识与协议版本：
Xray 版本：
真实 Node 验收：
已知限制与回滚方式：
```
