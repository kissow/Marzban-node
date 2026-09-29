# Mr.shaw Marzban-Node Fork 更新记录

本文件仅记录本 Fork 相对 [Gozargah/Marzban-node](https://github.com/Gozargah/Marzban-node) 的改动。原作者、许可证和上游 Git 历史均保留；完整功能边界见 [FORK_FEATURES.md](FORK_FEATURES.md)。

## 开发中（尚未发布）

- 通过既有认证 REST/RPyC 通道向主面板提供节点 CPU、内存、磁盘和运行时间，不新增监控端口。
- 支持主面板下发的单条 HTTP 或 SOCKS5 住宅代理出口；每个 Node 最多一条。
- 具体路由规则优先于默认住宅出口；HTTP 出口只承接 TCP，UDP 保持原路由。
- Xray 重启前先验证新配置；验证失败时不先停止正在运行的核心。日志不输出住宅代理密码。
- 设备数量限制尚未实现，待用户级方案确定后单独开发。

发布时须记录与 `kissow/Marzban` 的配对版本，并完成真实 Linux 节点联调。
