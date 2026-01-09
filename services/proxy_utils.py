import re
from dataclasses import dataclass
from typing import Iterable, List, Optional


PROXY_PATTERN = re.compile(
    r"^(?P<host>[^:]+):(?P<port>\d{2,5})(?::(?P<user>[^:]+):(?P<password>.+))?$"
)


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

    def as_url(self) -> str:
        if self.username and self.password:
            return f"socks5://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"socks5://{self.host}:{self.port}"


class ProxyPool:
    def __init__(self, proxies: Iterable[ProxyConfig]):
        self._proxies = list(proxies)
        self._index = 0

    def next_proxy(self) -> Optional[ProxyConfig]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy


def parse_proxy_line(line: str) -> Optional[ProxyConfig]:
    match = PROXY_PATTERN.match(line.strip())
    if not match:
        return None
    data = match.groupdict()
    return ProxyConfig(
        host=data["host"],
        port=int(data["port"]),
        username=data.get("user"),
        password=data.get("password"),
    )


def parse_proxy_list(lines: Iterable[str]) -> List[ProxyConfig]:
    proxies: List[ProxyConfig] = []
    for line in lines:
        if not line.strip():
            continue
        proxy = parse_proxy_line(line)
        if proxy:
            proxies.append(proxy)
    return proxies
