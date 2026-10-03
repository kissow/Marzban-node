"""Validate and apply panel-managed proxy outbounds to an Xray config."""

from copy import deepcopy


_ALLOWED_PROTOCOLS = {"http", "socks"}
_MAX_PROFILES = 1
_MAX_TEXT = 256
_UDP_MODES = {"legacy", "proxy", "tcp_only"}
_DNS_TAG = "managed-residential-dns"
_DNS_QUERY_TAG = "managed-residential-dns-query"
_BLOCK_TAG = "managed-residential-udp-block"


class OutboundConfigError(ValueError):
    """Raised when a managed outbound profile is invalid or unsafe."""


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > _MAX_TEXT:
        raise OutboundConfigError(
            f"{field} must be a non-empty string of at most {_MAX_TEXT} characters"
        )
    return value.strip()


def _port(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise OutboundConfigError("port must be an integer between 1 and 65535")
    return value


def _profile(profile, tags):
    if not isinstance(profile, dict):
        raise OutboundConfigError("each outbound profile must be an object")
    tag = _text(profile.get("tag"), "tag")
    protocol = _text(profile.get("protocol"), "protocol").lower()
    if protocol not in _ALLOWED_PROTOCOLS:
        raise OutboundConfigError("only http and socks outbounds are supported")
    udp_mode = profile.get("udp_mode", "legacy")
    if not isinstance(udp_mode, str) or udp_mode not in _UDP_MODES:
        raise OutboundConfigError("invalid UDP mode")
    if udp_mode == "proxy" and protocol != "socks":
        raise OutboundConfigError("UDP proxy mode requires SOCKS5")
    if tag in tags:
        raise OutboundConfigError(f"duplicate outbound tag: {tag}")
    server = _text(profile.get("server"), "server")
    port = _port(profile.get("port"))
    username = profile.get("username")
    password = profile.get("password")
    if (username is None) != (password is None):
        raise OutboundConfigError("username and password must be provided together")
    server_config = {"address": server, "port": port}
    if username is not None:
        server_config["user"] = _text(username, "username")
        server_config["pass"] = _text(password, "password")
    return {"tag": tag, "protocol": protocol, "settings": server_config}


def _is_catch_all(rule):
    """Find an existing fallback without treating domain/IP rules as generic."""
    if not isinstance(rule, dict) or rule.get("type") != "field":
        return False
    matchers = set(rule) - {"type", "outboundTag", "balancerTag", "ruleTag"}
    return not matchers or matchers == {"network"} and rule.get("network") in (
        "tcp,udp", "udp,tcp", "tcp", "udp"
    )


def apply_managed_outbounds(config):
    """Merge a validated panel extension into an Xray config."""
    if "marzban_node_extensions" not in config:
        return
    candidate = deepcopy(config)
    _apply_managed_outbounds(candidate)
    config.clear()
    config.update(candidate)


def _apply_managed_outbounds(config):
    """Build on a private copy so a rejected policy cannot partially apply."""
    extension = config.pop("marzban_node_extensions", None)
    if extension is None:
        return
    if not isinstance(extension, dict):
        raise OutboundConfigError("marzban_node_extensions must be an object")
    profiles = extension.get("outbounds", [])
    if not isinstance(profiles, list) or len(profiles) > _MAX_PROFILES:
        raise OutboundConfigError("outbounds must contain at most one profile")
    existing = deepcopy(config.get("outbounds", []))
    if not isinstance(existing, list):
        raise OutboundConfigError("outbounds must be a list")
    tags = {item.get("tag") for item in existing if isinstance(item, dict) and item.get("tag")}
    managed = []
    udp_modes = {}
    for profile in profiles:
        outbound = _profile(profile, tags)
        tags.add(outbound["tag"])
        managed.append(outbound)
        udp_modes[outbound["tag"]] = profile.get("udp_mode", "legacy")
    config["outbounds"] = existing + managed

    default_tag = extension.get("default_outbound_tag")
    if default_tag is not None:
        default_tag = _text(default_tag, "default_outbound_tag")
        managed_tags = {item["tag"] for item in managed}
        if default_tag not in tags | managed_tags:
            raise OutboundConfigError(f"default outbound tag does not exist: {default_tag}")
        routing = config.setdefault("routing", {})
        if not isinstance(routing, dict):
            raise OutboundConfigError("routing must be an object")
        rules = routing.setdefault("rules", [])
        if not isinstance(rules, list):
            raise OutboundConfigError("routing.rules must be a list")
        fallback_index = next((index for index, rule in enumerate(rules) if _is_catch_all(rule)), len(rules))
        default_protocol = next(item["protocol"] for item in managed if item["tag"] == default_tag) \
            if default_tag in managed_tags else None
        udp_mode = udp_modes.get(default_tag, "legacy")
        if udp_mode == "tcp_only":
            reserved = {_DNS_TAG, _DNS_QUERY_TAG, _BLOCK_TAG}
            inbound_tags = {item.get("tag") for item in config.get("inbounds", []) if isinstance(item, dict)}
            dns = config.get("dns", {})
            if not isinstance(dns, dict):
                raise OutboundConfigError("dns must be an object")
            if reserved & (tags | inbound_tags) or dns.get("tag") in reserved:
                raise OutboundConfigError("reserved UDP compatibility tag already exists")
            config["outbounds"].extend([
                {"tag": _DNS_TAG, "protocol": "dns", "settings": {"network": "tcp", "nonIPQuery": "skip"},
                 "proxySettings": {"tag": default_tag}},
                {"tag": _BLOCK_TAG, "protocol": "blackhole"},
            ])
            # A/AAAA queries in Xray's DNS outbound use its built-in resolver,
            # not the outbound dialer. Explicitly tunnel that resolver too.
            config["dns"] = {**deepcopy(dns), "servers": ["tcp://1.1.1.1", "tcp://8.8.8.8"],
                             "tag": _DNS_QUERY_TAG}
            rules.insert(0, {"type": "field", "inboundTag": [_DNS_QUERY_TAG], "outboundTag": default_tag})
            fallback_index += 1
            # Existing explicit API/security/admin rules retain priority.
            rules[fallback_index:fallback_index] = [
                {"type": "field", "network": "udp", "port": "53", "outboundTag": _DNS_TAG},
                {"type": "field", "network": "udp", "outboundTag": _BLOCK_TAG},
            ]
            fallback_index += 2
        rules.insert(fallback_index, {
            "type": "field",
            "network": "tcp" if default_protocol == "http" or udp_mode == "tcp_only" else "tcp,udp",
            "outboundTag": default_tag,
        })
