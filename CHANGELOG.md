# Mr.shaw Marzban-Node Fork 更新记录

## 2026-10-03 主面板订阅兼容修复配对说明（Node 运行时无变化）

- 主面板修复 `reject_new` 对无 `X-HWID` 客户端返回 `428` 的回归，并恢复共享账号；Node 继续通过原有认证 Xray 控制通道接收共享账号和已登记 HWID 的独立账号。
- Node 不保存原始 HWID、不自行判断订阅是否带 HWID，也不新增端口、数据库、证书或 Xray 核心版本；本次不需要更新 Node 镜像。
- 带 HWID 的新设备超额拒绝由主面板订阅登记执行，Node 只加载主面板下发的最终账号配置。无 HWID 客户端使用共享凭据，不能获得 HWID 限额保证；策略 ACK 不是所有客户端被拦截的证明。
- 主面板本轮服务器验收需重新完成；本条不能把此前 Node 镜像发布证据当作本轮验收通过。

## 2026-10-02 设备账号加载链（镜像已发布，服务器验收待完成）

> 历史条目中的“无 HWID 返回 428”由 2026-10-03 主面板兼容修复取代；保留作为历史发布记录。

- 配对主面板通过现有认证 Xray 控制通道下发每个 HWID 的独立账号；Node 配置加载这些账号，支持 `reject_new` 用户的新连接凭据拒绝。
- Node 不保存原始 HWID，也不把策略快照或在线用户数误报为物理设备数；没有 `X-HWID` 的旧客户端由主面板返回 `428`。
- 现有证书、服务端口、API 端口、数据目录和固定 Xray `v26.3.27` 保持不变；Node commit `d6f3bec204a75085939b5b4e25fa6502f5946ae5` 已推送，Actions `36975383911` 成功，GHCR `latest` 已发布。真实 Linux Node 与客户端矩阵、服务器验收仍待完成。

## 2026-10-02 活动查询与策略接收（镜像已发布，服务器验收待完成）

- 固定 Xray v26.3.27 的 `GetAllOnlineUsers` 经现有 TLS API 查询；policy 启用 `statsUserOnline` 并保留已有字段。只有未实现 RPC 的旧核心回退到观察到的近期流量；失败显示未知。读取始终 reset=false，不清零主面板计费数据。
- 新增认证 REST `/device-activity`、`/device-policies` 和 RPyC 配对方法。共用原子校验，完整快照替换、重复用户拒绝、数量/revision/UTC 时间确认；不发送 HWID、IP 或用户代理凭据。
- 健康资源缓存和活动/策略元数据分别合成，避免缓存掩盖刚完成的同步。核心重启清除活动基线，认证会话更新清除旧策略。
- `device-policy-v1`、`xray-user-stats-v1` 表示合同支持；`policy_enforcement=subscription_request_and_node_credentials`、`direct_connection_enforced=true` 表示当前版本已经把已登记设备凭据加载到 Node 的 Xray 配置中。策略 ACK 本身仍不是实时在线设备数证明；旧版本的“仅订阅请求”描述已由本轮实现取代。
- 本地真实 Xray 验证 VLESS 连接/断开、TLS Stats RPC、非重置流量读取，以及 HTTP/SOCKS 配置；CI 固定核心实测步骤和 GHCR 构建均已成功，服务器尚未更新。
- 接口、旧节点兼容、升级和回退见 [合同](docs/activity-and-policy.md)。证书、服务端口、API 端口、数据库、数据目录、核心版本与安装脚本保持原样。

本文件仅记录本 Fork 相对 [Gozargah/Marzban-node](https://github.com/Gozargah/Marzban-node) 的改动。原作者、许可证和上游 Git 历史均保留；完整功能边界见 [FORK_FEATURES.md](FORK_FEATURES.md)。

## 正式版核心一致性闸门（2026-09-30，未发布）

- 构建完成后立即读取 Xray 二进制版本，并强制核对为 `v26.3.27`；下载脚本返回错误版本时镜像构建失败。
- GitHub Actions 增加正式版本锁定检查，避免主面板和 Node 的 `latest` 镜像意外混入其他核心。

## Xray 核心正式基线收口（2026-09-30，未发布）

- Node Dockerfile、GitHub Actions 和安装脚本统一锁定 `XRAY_CORE_VERSION=v26.3.27`，不再从动态 `latest` 地址取核心。
- Node 的 `core-update` 采用相同固定版本，并同步修正下载完成提示；删除无效的旧核心菜单变量，避免出现多个版本来源。
- 保留显式版本参数作为隔离测试入口；正式镜像和生产 Node 不使用 `v26.9.9` 等测试候选版本。
- 本次没有删除或迁移证书、端口、节点数据、Docker 数据卷或现有配置；镜像尚未由本地变更直接宣称发布。

## 开发中（尚未发布）

- 通过既有认证 REST/RPyC 通道向主面板提供节点 CPU、内存、磁盘和运行时间，不新增监控端口。
- 支持主面板下发的单条 HTTP 或 SOCKS5 住宅代理出口；每个 Node 最多一条。
- 具体路由规则优先于默认住宅出口；HTTP 出口只承接 TCP，UDP 保持原路由。
- Xray 重启前先验证新配置；验证失败时不先停止正在运行的核心。日志不输出住宅代理密码。
- （历史阶段记录）直接连接设备数量限制尚未实现；当时本地开发版只有用户策略元数据接收，订阅 HWID 限制由配对主面板执行。该阶段已被上方“设备账号加载链”取代，不代表当前实现。

发布时须记录与 `kissow/Marzban` 的配对版本，并完成真实 Linux 节点联调。

## 文档与接口登记规则

- 所有 REST/RPyC 方法、健康快照字段、`managed-outbounds-v1` 能力、
  `marzban_node_extensions` 配置字段和 Xray 预检行为，必须同步登记到
  [`../09-接口登记索引.md`](../09-接口登记索引.md)。
- 同一提交必须更新本文件、[`FORK_FEATURES.md`](FORK_FEATURES.md)、
  [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)、Node 开发计划和配对的
  Marzban/Marzban-scripts 文档；仅 UI 或文档变更也要写明运行时接口无变化。
- 发布记录必须包含三仓库 commit、Actions run、GHCR 镜像 digest、Xray 版本、
  备份位置、配对最低版本和服务器验收结果。未完成的接口只能标记为开发中。
