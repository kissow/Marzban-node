# MR-20261003-EGRESS-UDP paired release evidence

2026-10-03, Mr.shaw. Images published; real server, provider, mobile applications and UI screenshot acceptance remain pending. This is not a stable-release claim.

| Repository | Image source revision | Successful Actions |
| --- | --- | --- |
| kissow/Marzban | `10f46df8e52ad24c79a1d4a1aafc020a7f7ad335` | [37119086192](https://github.com/kissow/Marzban/actions/runs/37119086192) |
| kissow/Marzban-node | `ff3ed8affb43a7c0be84b7404b25ba149cd9c805` | [37119086117](https://github.com/kissow/Marzban-node/actions/runs/37119086117) |
| kissow/Marzban-scripts (documentation only) | `23c6dffe006eea30e117ffc86972f5fc94eab33d` | [37119329541](https://github.com/kissow/Marzban-scripts/actions/runs/37119329541) |

`ghcr.io/kissow/marzban:latest` index `sha256:6d008568b64fc0ebdf6b323d0a3a7ffeb8d717aa55fd93c30724127ff6146a81`; amd64 `sha256:1206e3f858795ec1790e7506d27c8069e6e72d8a1268369453258647a83f59c9`; arm64 `sha256:18c54440017bee8aeb3fb0b53e9eb2103806009663c972b2ad8413cfaf399976`. Both OCI revisions match the panel source above.

`ghcr.io/kissow/marzban-node:latest` index `sha256:01935b08bacfad38f1e938d6edcd675ba44b5a4e89a0fa85be89197b81318cb9`; amd64 `sha256:b996deaaecea716394623eaeb328bbeabef02da00f6ba15d6efce6200094250a`; arm64 `sha256:6649c8d399d81b615b87ad69886f0629d34e6150b2dd344bb83c846947e89dc6`. Both OCI revisions match the Node source above.

Complete local tests: panel 54, Node 48 without skips, including 8 pinned-core parser configurations and 4 real A/TXT DNS TCP tests with fake local providers. Linux Actions and both multiarchitecture builds succeeded without reruns. The initial local GHCR evidence utility incorrectly parsed PowerShell HTTP Byte[] as JSON text; UTF-8 decoding fixed that utility and both registry checks were repeated successfully. It was not a runtime/Actions failure.

Subsequent evidence-only documentation commits use `[skip ci]` and do not rebuild the images. Repository documentation HEAD may be newer than the image source SHA; do not label it as the OCI source revision.

Back up first. Existing switched installations: update every Node with `marzban-node update`, verify status/panel connection, then panel with `marzban update`. No repeated adopt/reinstall, no volume deletion, no additional software or ports. Scripts runtime unchanged; pinned Xray remains `v26.3.27`.

Legacy remains default. New modes require `managed-outbounds-udp-v1`. Enable only on a test Node first; real provider TCP53, mobile v2rayNG/Clash Meta, Linux authenticated pairing, non-DNS UDP apps, residential egress IP, UDP-capable providers, rollback and real UI screenshots are not accepted yet. TCP-only DNS is not arbitrary UDP-to-TCP or full-flow leak protection. Restore legacy before downgrading and preserve data. See [wire contract](egress-udp.md) and the panel's `docs/EGRESS_UDP_RELEASE.md`.
