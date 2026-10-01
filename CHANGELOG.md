# Mr.shaw Marzban-Node Fork 更新记录

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
- 设备数量限制尚未实现，待用户级方案确定后单独开发。

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
