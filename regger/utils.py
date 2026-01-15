from __future__ import annotations


def format_endpoint(template: str, **values: str) -> str:
    safe_values = {key: value or "" for key, value in values.items()}
    return template.format(**safe_values)
