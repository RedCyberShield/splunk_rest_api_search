#!/usr/bin/env python3
"""Simple connectivity tester for Splunk Search Jobs API."""

import sys
from urllib.parse import urlparse

import requests

from splunk_search import (
    load_config,
    make_headers,
    resolve_proxies,
    validate_output_mode,
)


def test_connection(config_path: str = "config.toml") -> int:
    cfg = load_config(config_path)
    spl = cfg["splunk"]

    base_url = spl["url"].rstrip("/")
    token = spl["token"]
    verify_ssl = spl.get("verify_ssl", True)
    proxies = resolve_proxies(spl.get("proxy", ""), base_url)

    # Validate output_mode early to surface errors in config
    validate_output_mode(spl.get("output_mode", "json"))

    headers = make_headers(token)
    params = {"output_mode": "json", "count": 1}

    parsed = urlparse(base_url)
    display_host = parsed.hostname or base_url

    try:
        response = requests.get(
            base_url,
            headers=headers,
            params=params,
            verify=verify_ssl,
            proxies=proxies,
            timeout=15,
        )
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - troubleshooting helper
        proxy_info = proxies or requests.utils.get_environ_proxies(base_url)
        print(f"Connection to {display_host} failed: {exc}")
        if proxy_info:
            print("Proxy configuration detected during failure:")
            for scheme, value in proxy_info.items():
                print(f"  {scheme}: {value}")
        return 1

    data = response.json()
    entry_count = len(data.get("entry", []))
    print(
        f"Connection to {display_host} successful. Retrieved {entry_count} job(s) from the API."
    )
    return 0


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.toml"
    sys.exit(test_connection(config_file))
