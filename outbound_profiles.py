"""Validate and apply panel-managed proxy outbounds to an Xray config."""

from copy import deepcopy


_ALLOWED_PROTOCOLS = {"http", "socks"}
_MAX_PROFILES = 1
_MAX_TEXT = 256


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
    for profile in profiles:
        outbound = _profile(profile, tags)
        tags.add(outbound["tag"])
        managed.append(outbound)
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
        rules.insert(fallback_index, {
            "type": "field",
            "network": "tcp" if default_protocol == "http" else "tcp,udp",
            "outboundTag": default_tag,
        })
