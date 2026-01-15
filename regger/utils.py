from __future__ import annotations


def parse_proxy(proxy_value: str) -> str:
    raw = (proxy_value or "").strip()
    if not raw:
        raise ValueError("Proxy is required.")
    if "://" in raw:
        return raw
    auth_split = raw.rsplit(":", 1)
    if len(auth_split) != 2:
        raise ValueError("Proxy must be in host:port:user:pass format.")
    host_port_user, password = auth_split
    parts = host_port_user.split(":", 2)
    if len(parts) != 3:
        raise ValueError("Proxy must be in host:port:user:pass format.")
    host, port, user = parts
    return f"socks5://{user}:{password}@{host}:{port}"
