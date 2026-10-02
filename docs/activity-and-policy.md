# Node 活动统计与设备策略合同

状态：2026-10-02，本地开发与验收中；未推送、未构建镜像、未部署。维护者：Mr.shaw。

## 数据流与认证

Marzban 通过原有 TLS REST/RPyC 控制通道读取对应 Node 的指标和同步策略；外部调用者使用 Marzban 的 `GET /api/node/{node_id}/health` 和超级管理员 Bearer Token。继续使用现有服务端口及 Xray API 端口，证书、数据目录、数据库和部署命令保持原样。

| 通道 | 请求 | 响应与用途 |
| --- | --- | --- |
| REST `POST /health` | 原有 `session_id` | 资源指标、活动采样及策略元数据 |
| REST `POST /device-activity` | 原有 `session_id` | 仅活动采样，读取不重置计费流量 |
| REST `POST /device-policies` | `session_id`、`policies` 数组 | 完整替换策略快照，返回接收确认 |
| RPyC `fetch_health()` | 原有 TLS 连接 | 与 REST 健康快照一致 |
| RPyC `fetch_device_activity()` | 原有 TLS 连接 | 与 REST 活动采样一致 |
| RPyC `set_device_policies(json_string)` | 原有 TLS 连接、JSON 字符串 | 避免 RPyC 容器 netref 的类型误判；与 REST 同一校验器 |

REST 会话缺失、失效或不匹配返回 403；无效策略返回 422。每批最多 10000 条，`device_limit` 为 0–100000 的整数，0 表示不限；用户标识唯一、长 1–128；模式只允许 `hwid`，动作只允许 `log_only` 或 `reject_new`。整批校验成功才原子替换；空数组清除旧快照。RPyC 接收端也接受本地 Python 数组，但主面板统一发送 JSON 字符串。

## 活动字段及口径

`active_users` 为非负整数或 null，绝不从主机 socket 数量推导。优先使用固定核心 `v26.3.27` 的 `GetAllOnlineUsers`。Node 在既有 Xray 配置的 policy levels 中启用 `statsUserOnline`，保留其他字段。

| 来源 | scope | 口径 |
| --- | --- | --- |
| `xray-online-users` | `online_users` | Xray 在线 IP 表中存在活动条目的用户；同一用户只计一次 |
| `xray-user-stats-delta` | `recent_traffic` | 旧核心未实现该 RPC 时，Node 在默认 120 秒滚动窗口内观察到流量变化的用户，尽力统计 |
| `panel-node-usage` | `recent_traffic` | 旧 Node 没有活动合同，主面板兼容使用最近 2 小时已有节点用量记录 |

响应包含 `active_users_sampled_at`、`activity_source`、`activity_scope`、`activity_reason`。流量回退附带 `active_users_window_seconds`；原生在线查询该字段为 null。面板用量回退附带 `active_users_window_hours`。Node 采样缓存 5 秒；主面板验证采样时间在 15 秒内且最多容许 5 秒时钟超前。

采样首次建立基线或长时间无采样后返回 null/`sampling_baseline`；Stats 失败返回 null/`stats_unavailable`。主面板不会用兼容回退掩盖新 Node 的查询失败。RPC 只有 UNIMPLEMENTED 会触发旧核心回退；网络错误不会伪装成零用户。Node 查询计数器始终使用 reset=false；原有主面板计费 reset=true 继续工作，Node 不抢占计费数据。旧核心回退可能漏掉两次采样间发生且被主面板清零的短流量，不能作为精确在线或结算统计。

## 策略接收与执行范围

示例请求仅包含策略字段：

```json
{
  "policies": [{
    "user": "1.example",
    "device_limit": 3,
    "device_limit_mode": "hwid",
    "device_limit_action": "reject_new"
  }]
}
```

完整快照包含 active、on_hold、limited 用户，排除 disabled、expired 和已删除用户。策略快照本身不会传递密码、订阅 Token、原始 HWID、设备记录或 IP 地址；设备专属协议凭据由主面板的 Xray 配置生成器按已登记设备加载，并通过现有认证控制通道随配置同步到 Node。

成功响应为 `accepted=true`、`policy_count`、`policy_revision`（规范化快照 SHA-256）、`policy_synced_at`（UTC）、`policy_enforcement=subscription_request_and_node_credentials`、`direct_connection_enforced=true`。健康接口保留以上元数据，主面板还显示 `policy_sync_status`：synced/pending/failed/unsupported。同步成功要求确认数量和执行范围匹配；错误确认标为失败。

Node 启动、重启及重新连接后同步；管理员创建、修改、删除用户后同步；60 秒任务补齐计划任务修改及失败重试。批次按顺序执行，一个批次只读一次数据库、最多并行推送 10 个 Node；单节点失败不阻断其他节点或回滚已保存用户。旧 REST 返回 404/405/501、旧 RPyC 无方法时标为 unsupported，继续原连接功能。

`reject_new` 当前在主面板订阅请求携带 `X-HWID` 时拒绝超出登记上限的新设备，并为每个已登记 HWID 生成 VLESS/VMess UUID 或 Trojan/Shadowsocks 密码。主面板和 Node 的 Xray 配置只加载这些已登记设备账号，因此更新后的配置会拒绝没有对应专属凭据的新连接；Node 接收策略确认本身不是拦截证据。已经导入旧共享 UUID/密码的客户端不会被订阅请求主动踢下线，在线 IP 表也不是实时物理设备数。

设备登记表由迁移 `4a9d2e8b7c61_add_user_device_limit.py` 创建，设备凭据由最新迁移 `6d7e8f9012ab_add_device_credentials.py` 保存；这是当前设备限制迁移链的最新 revision。切回 `log_only` 会清理设备账号并恢复共享账号。Node 不保存原始 HWID，也不独立计算 HWID；主面板负责登记和生成凭据。Node 返回的策略 ACK 不是实时在线设备数证明，直接拒绝依据是收到并加载后的 Xray 设备账号配置。

## 来源与致谢

本 Fork 保留 Marzban / Marzban-Node 上游历史、许可证和作者署名。Xray 协议依据官方 [StatsService protobuf](https://github.com/XTLS/Xray-core/blob/v26.3.27/app/stats/command/command.proto)、[实现](https://github.com/XTLS/Xray-core/blob/v26.3.27/app/stats/command/command.go) 和 [OnlineMap](https://github.com/XTLS/Xray-core/blob/v26.3.27/app/stats/online_map.go)。本次 wire 编解码及策略验证为本 Fork 自行实现，没有复制其他面板的设备限制源文件。

## 验证、升级与回退

两仓库运行 `python -B -m unittest discover -s tests -v`；主面板运行 `npm exec tsc -- --noEmit` 和 `npm exec vite -- build --outDir build-ci`。Node 设置 `XRAY_TEST_BINARY` 可运行固定核心真实配置预检及 TLS Stats RPC。UI 必须以原 Chakra 组件在桌面/手机渲染后审阅，再推送。

发布前补录两仓库 commit、Actions run、镜像 tag/index/架构 digest、OCI revision 和服务器验收；当前不提供已发布结论。脚本无运行时变更，核心继续固定 `v26.3.27`。已有 Fork 部署发布后使用 `marzban update` / `marzban-node update`，官方旧安装首次切换使用 adopt，新机才使用 install。保留数据库、环境文件、证书、现有端口、配置及数据卷；本轮包含设备凭据数据库迁移，必须先备份后升级。回退到先前配对镜像与保存的配置；旧面板忽略新增指标字段，旧 Node 被识别为不支持新增方法。
