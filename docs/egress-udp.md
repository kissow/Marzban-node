# Managed outbound UDP contract

Change: `MR-20261003-EGRESS-UDP` (2026-10-03), Mr.shaw. Local/unpublished; no new image or server acceptance is claimed. Pair with the panel change of the same ID. Scripts are unchanged; pinned Xray remains `v26.3.27`.

## Wire format

Use the existing authenticated REST/RPyC Xray configuration channel; no new listener, certificate, database or public API:

```json
{
  "marzban_node_extensions": {
    "outbounds": [{
      "tag": "managed-residential-egress",
      "protocol": "socks",
      "server": "proxy.example.invalid",
      "port": 1080,
      "udp_mode": "tcp_only"
    }],
    "default_outbound_tag": "managed-residential-egress"
  }
}
```

At most one profile per Node; optional username/password must be supplied together. Do not log passwords/config payloads. Preserve encrypted panel storage and the existing Xray HTTP/SOCKS credential mapping. Node health adds `managed-outbounds-udp-v1`; retain `managed-outbounds-v1`.

| Mode | Semantics |
| --- | --- |
| absent / `legacy` | Old behavior. Panel omits the field for backward compatibility; SOCKS fallback uses TCP/UDP, HTTP fallback uses TCP. |
| `proxy` | SOCKS fallback TCP/UDP via the provider; no DNS rewrite. HTTP is invalid. This is not a capability probe of the provider. |
| `tcp_only` | Fallback UDP53 → DNS outbound with TCP through the residential proxy; other fallback UDP → blackhole; fallback TCP → residential proxy. |

All existing explicit API/security/domain/IP/inbound rules before the generic fallback retain priority, including explicit direct routes. Do not claim full-flow leak protection. No new direct fallback is added. Non-DNS UDP is not converted to TCP; application fallback is not guaranteed.

For `tcp_only`, the Node-local DNS server list is replaced with `tcp://1.1.1.1` and `tcp://8.8.8.8`; hosts/queryStrategy and other DNS settings are preserved. The resolver's private inbound tag routes through the provider. A/AAAA use the internal resolver; other DNS requests use the DNS outbound TCP tunnel. Providers must permit TCP53, and custom DNS server/domain rules are replaced. Reserved tags `managed-residential-dns`, `managed-residential-dns-query`, `managed-residential-udp-block` cannot collide with existing inbound/outbound/DNS tags.

The extension is validated and applied on a deep copy, committed only on success. Invalid mode/type, HTTP+proxy, duplicate/reserved tags or invalid structure raise `OutboundConfigError`. Core preflight must succeed before replacing the running core. A syntactically valid config does not prove the provider is reachable.

## Compatibility and rollback

Panel GET/PUT egress expose `udp_mode`, default legacy. Nonlegacy requires both capability flags and is checked before saving and again on connect/restart. Missing capability/old/offline Node returns panel 409; invalid input 422. Legacy remains compatible with old managed-outbound Nodes. A downgraded Node cannot silently ignore saved nonlegacy settings.

After paired images are actually published and approved: update Node first, check connection, then update panel and enable a mode on a test Node. Back up Compose, certificates/config and data directories. Keep existing service/API ports, volumes and credentials; do not reinstall or delete volumes. Restore legacy before downgrading either side. Panel migration only adds `node_egress.udp_mode`; Node has no migration.

## Evidence and acceptance

Local: 48 Node unittest tests passed without skips using the pinned binary, including 8 authenticated/unauthenticated HTTP/SOCKS parser combinations and 4 real A/TXT DNS TCP runtime tests against localhost fake providers. No supplier secrets/external DNS network are used in these tests. Route priority, non-DNS UDP blackhole rules, invalid policy atomicity and old behavior are covered. Non-DNS blackhole coverage is unit-level, not a real-app acceptance claim.

Pending: Linux authenticated panel/Node integration, real supplier TCP53 support, actual v2rayNG vs Clash Meta DNS/routes, non-DNS UDP/apps, residential egress IP, legacy rollback and a UDP-capable supplier regression. Never change a busy production Node merely to isolate one phone's traffic.

Attribution: retain Gozargah/Marzban-Node and XTLS/Xray-core licenses and credits. Reference only, not copied code: [Xray DNS outbound v26.3.27](https://github.com/XTLS/Xray-core/blob/v26.3.27/proxy/dns/dns.go) and [DNS config parser](https://github.com/XTLS/Xray-core/blob/v26.3.27/infra/conf/dns_proxy.go). Panel contract: `Marzban/docs/NODE_EGRESS_UDP.md` in the paired repository.
