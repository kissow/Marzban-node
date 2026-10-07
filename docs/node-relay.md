# Mr.shaw Node → Node 线协议

MR-20261008-NODE-RELAY-SOURCES：本地开发/测试，未推送、未发布本轮镜像、未服务器验收。配对主控完整管理/API/升级合同见 [NODE_RELAY_SOURCES](https://github.com/kissow/Marzban/blob/master/docs/NODE_RELAY_SOURCES.md)；该链接在本轮上传后才公开可用，当前本地位于 ../../Marzban/docs/NODE_RELAY_SOURCES.md。

源 Node 接受主控通过原认证 REST/RPyC 下发的固定目标快照，使用已有 Xray v26.3.27 独立进程转发 TCP，不经过源住宅出口。目标 Node 继续使用原认证、设备凭据和出口。无需额外转发软件，新增 psutil==5.9.4；不改原证书/控制/API端口、.env、数据目录或核心配置。必须放行源的业务监听 TCP端口。

能力 `managed-node-relay-v1` 在 health capabilities 与状态返回。REST POST `/relays/status` 接收 session_id；POST `/relays` 接收 session_id/profiles，原 TLS 客户端证书与会话认证继续生效，错会话403。RPyC `fetch_relay_status()`、`set_relays(JSON字符串)` 均经原 SSL连接，响应JSON字符串，嵌套列表/字典为普通值而非远程对象。

```json
{"profiles":[{"node_id":2,"listen_port":18443,"target_address":"node2.example.com","target_port":8443}]}
```

REST还需原session_id字段；RPyC只传profiles列表的JSON字符串。每profile只允许四个示例字段；node_id正整数且唯一，listen_port整数1024–65535且不占用，target_port整数1–65535，禁止bool冒充整数、URI/模板/回环目标及快照目标指向其中的中转端口。不接受任意Xray JSON或用户密钥。最多512目的地；主控单目标只配一个来源，不自动串联多跳，并做来源自身/环路校验。

状态返回capability/core_started/running/profiles/error/occupied_ports；写ACK返回capability/running/profiles/error。非空快照要求核心已启动；REST未启动409、输入422、进程应用失败409。RPyC相同情况抛明确异常。空列表清理，核心未启动仍可清理。Node验证JSON与固定Xray配置后替换；绑定失败尝试恢复旧进程。监听就绪只代表本地进程端口归属，不代表目标公网可达/客户端速度。

控制会话接管、断开、显式停止清理旧进程；源进程意外退出由主控周期检查后重下发数据库快照。服务/容器重启没有独立relay数据库，主控重连恢复。写超时可能实际已应用；主控恢复前通过状态核对，不盲目重放或广告新端点。原在线用户查询只统计源自身核心；透明转发用户在目标认证，不等于源Node新增物理设备或重复用户计费。

本轮源 Node 镜像必须配对发布；已切Fork且承担来源的服务器发布后用marzban-node update，随后更新主面板。仅作目标的现有配对Node无新来源要求；原安装不能用重装/删卷更新。旧Node无能力时主控明确拒绝新的Node来源设置，主控来源/直连仍可使用。

本地测试覆盖快照范围/认证错误/REST ASGI JSON/真实本地RPyC序列化/固定Xray多目标TLS透明转发/占用失败回滚和进程恢复。真实Linux mTLS配对、供应商网络、手机/桌面、吞吐及持续运行仍待验收，非稳定发布。CI第一轮未准备Xray的跳过项必须由第二轮显式固定Xray测试全部执行；不能将跳过当通过。

最终Node完整60/60连续两轮、无跳过；配对主控164/164两轮，前端47/47、TypeScript/Vite、依赖/编译/diff通过。使用项目固定Python环境与真实v26.3.27测试二进制；不是已完成干净LinuxCI或跨服务器mTLS联调。当前尚未上传或构建新镜像。

感谢 Marzban、Marzban-Node 与 Xray 原作者/贡献者，保留上游许可。node_relay.py复用Mr.shaw本Fork主控纯模块，无3X-UI源码复制。
