# Marzban-Node 开源扩展功能

本仓库由 Mr.shaw 基于 [Gozargah/Marzban-node](https://github.com/Gozargah/Marzban-node) 开发，供其他使用者按开源许可证使用。感谢原作者和贡献者；保留原有 Git 历史与 AGPL-3.0 许可证。本说明中的扩展不是上游官方功能。

当前配对发布分支为 `feature/mrshaw-release`，与 `kissow/Marzban` 的同名分支配对。合并后由 `kissow/Marzban-node` 的 `master` 作为唯一日常安装、升级和镜像发布源；原作者仓库只保留为历史基线、许可证及致谢来源。

## 当前扩展

- 已有认证的 REST `/health` 和 RPyC 通道向 Marzban 主面板返回节点运行指标及 `managed-outbounds-v1` 能力标识，不新增公网监控端口，也不向任何业务系统直连。指标注明来源；没有可靠来源的节点级在线用户数始终返回 `null`。
- 从主面板配置中读取可选的 `marzban_node_extensions` 扩展，每个 Node 最多接受一条住宅 IP 出站，并转换为 Xray HTTP/SOCKS 出站。普通官方配置没有扩展时行为不变。
- 路由保留管理员已有的具体规则优先；默认住宅出口位于兜底规则之前。HTTP 默认出口只匹配 TCP，避免把 UDP 送入不支持的协议。
- 核心重启前运行 Xray 配置预检；预检失败不会先停掉当前核心。配置错误不在日志中输出代理密码。

当前尚未实现住宅代理连通性健康检查、故障摘除或自动故障回滚，也没有准确的节点级活跃用户计数。部署前必须在隔离节点验证代理协议、认证、DNS、TCP/UDP 路由和恢复直连。

## 本地验证

运行 `python -B -m unittest discover -s tests -v`。若安装了 Xray 二进制，设置 `XRAY_TEST_BINARY` 为其绝对路径后重跑测试，会额外验证 HTTP/SOCKS 有认证和无认证的 4 种最终 Xray 配置。
