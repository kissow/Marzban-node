# Marzban-Node 开源扩展功能

## 2026-10-03 主面板订阅兼容配对（Node 运行时无变化）

主面板在 `reject_new` 下对不带 `X-HWID` 的普通客户端恢复原共享订阅；Node 仍从原有认证控制通道加载主面板配置中的共享账号和已登记 HWID 独立账号。Node 不接收原始 HWID、不独立登记设备、不新增端口/数据库/证书/核心版本，本次不需更新 Node。带 HWID 的超额拒绝由主面板执行；无 HWID/共享配置可绕过 HWID 限额，因此不是物理设备或实时在线设备限制。真实 Node 验收需随主面板重新执行。

## 2026-10-02 发布状态

- 状态：镜像已发布，服务器验收待完成；本地 39 项测试、真实 Xray `v26.3.27` 检查和 GitHub Actions 已完成，不能写成稳定发布。
- `master` commit `d6f3bec204a75085939b5b4e25fa6502f5946ae5`，Actions run `36975383911`；`ghcr.io/kissow/marzban-node:latest` index `sha256:f2a9e93ca3168abb3559f3e48baa98d02e6377fb8d4a480407f447a97bbbf774`，amd64 `sha256:81965a75de1bc07f5948bb42ea216d5cd80be36bca152641c41c0bf7820c0bc3`，arm64 `sha256:6d82315f1b73a0cd75b7c5ac2f5c3163d4fab10304a54fe8c250e461a4da63cd`，两个架构 OCI revision 均对应该 commit。
- 配对主面板为 `a6efaa8eafd82c3f68d2ff29074cf9eeb1ec8ae0`；Node 服务器更新前仍需备份证书、Compose、配置和数据目录。

本仓库由 Mr.shaw 基于 [Gozargah/Marzban-node](https://github.com/Gozargah/Marzban-node) 开发，供其他使用者按开源许可证使用。感谢原作者和贡献者；保留原有 Git 历史与 AGPL-3.0 许可证。本说明中的扩展不是上游官方功能。

`kissow/Marzban-node` 的 `master` 是唯一日常安装、升级和镜像发布源；与主面板的配对变更在临时分支完成，合并后删除临时分支；原作者仓库只保留为历史基线、许可证及致谢来源。

## 当前扩展

- 已有认证的 REST `/health` 和 RPyC 通道向 Marzban 主面板返回节点运行指标；新增 `device-policy-v1`、`xray-user-stats-v1` 能力标识，不新增公网监控端口。优先查询核心在线用户，旧核心尽力回退到近期流量；来源与 scope 单独标注。见 [活动与策略合同](docs/activity-and-policy.md)。
- REST `/device-activity` / `/device-policies` 与 RPyC 配对方法提供活动采样及原子策略快照接收，返回数量、revision、同步时间和执行范围。策略不含用户代理凭据、HWID 或 IP；配对主面板通过既有 Xray 控制通道另行同步每个 HWID 的设备账号，Node 重启后从生成配置加载这些账号，支持新连接凭据拒绝。
- 从主面板配置中读取可选的 `marzban_node_extensions` 扩展，每个 Node 最多接受一条住宅 IP 出站，并转换为 Xray HTTP/SOCKS 出站。普通官方配置没有扩展时行为不变。
- 路由保留管理员已有的具体规则优先；默认住宅出口位于兜底规则之前。HTTP 默认出口只匹配 TCP，避免把 UDP 送入不支持的协议。
- 核心重启前运行 Xray 配置预检；预检失败不会先停掉当前核心。配置错误不在日志中输出代理密码。

当前尚未实现住宅代理连通性健康检查、故障摘除或自动故障回滚，以及实时在线设备数统计。`reject_new` 的设备账号加载链已在本地开发版实现：Node 接受主面板为已登记 HWID 下发的独立 Xray 凭据，同时保留主面板要求的共享兼容账号，不自行保存原始 HWID。没有 `X-HWID` 的客户端由主面板返回共享订阅；因此无法获得 HWID 限额保证。已有旧配置不会被 Node 主动踢下线。仍须配对镜像与真实 Linux 节点验收，不能把本地测试写成已部署。

## Xray 核心版本与功能边界

仓库正式构建基线统一为 `v26.3.27`（稳定版）。Node 的 Dockerfile 和 GitHub Actions 通过 `XRAY_CORE_VERSION` 固定该版本，并与主面板配对发布；Node 不再在构建时随 `latest` 自动漂移。`v26.9.9` 当前是预发布版本，不能直接作为生产 `latest`。

Xray 核心新增协议或传输层不会自动变成 Node 的可配置功能。只有主面板能生成对应 Xray JSON、Node 能安全接收并预检/重启、订阅转换覆盖客户端格式，且完成端到端测试后，才会新增面板开关。当前 Node 扩展只处理节点健康回报和每个 Node 独立的 HTTP/SOCKS 住宅代理出站；Hysteria 2、Finalmask、XHTTP/3、ECH、WireGuard 等暂不宣称已通过本扩展开放。

如果测试 `v26.9.9`，必须使用独立测试镜像标签，不覆盖 `latest`，并检查配置预检、TCP/UDP、DNS、证书、重启恢复和回滚。服务器上的 `core-update` 可能写入外部 Xray 二进制，导致容器内外出现不同版本；正式部署以仓库镜像中的固定版本为准。
## 本地验证

运行 `python -B -m unittest discover -s tests -v`。若安装了 Xray 二进制，设置 `XRAY_TEST_BINARY` 为其绝对路径后重跑测试，会额外验证 HTTP/SOCKS 有认证和无认证的 4 种最终 Xray 配置。

## 跨仓库登记

当前可依赖的 REST/RPyC 通道、健康快照和 `marzban_node_extensions` 配置合同，
以 [`../09-接口登记索引.md`](../09-接口登记索引.md) 为唯一索引；不要仅凭本文件
新增接口。变更时同时更新主面板的接口说明、scripts 的命令合同、CHANGELOG、
测试证据和 [`../08-跨仓库更新登记模板.md`](../08-跨仓库更新登记模板.md)。
安装命令、证书、服务端口、数据目录或镜像来源发生变化时，必须增加升级、回退和
服务器验收记录；若没有变化，也要明确写出“无变化”。
