#!/usr/bin/env python3

import json
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse

import requests

# TOML loader for Python < 3.11
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


###############################################################################
# LOGGING SETUP
###############################################################################
def setup_logging(log_dir: str, retention_days: int, level: str = "INFO"):
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / f"splunk_search_{datetime.now().strftime('%Y%m%d')}.log"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        filename=log_file,
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cleanup_old_logs(log_path, retention_days)
    logging.info("Logging initialized. Log file: %s", log_file)


def cleanup_old_logs(log_path: Path, retention_days: int):
    cutoff = datetime.now() - timedelta(days=retention_days)
    for file in log_path.glob("splunk_search_*.log"):
        try:
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime < cutoff:
                file.unlink()
        except Exception as e:
            logging.warning("Failed to delete old log %s: %s", file, e)


def mask_proxy_credentials(proxy_url: str) -> str:
    """Mask credentials in a proxy URL for safe logging."""

    if not proxy_url:
        return ""

    try:
        parsed = urlparse(proxy_url)
    except Exception:
        return proxy_url

    if not parsed.username:
        return proxy_url

    username_placeholder = "****"
    password_placeholder = "****" if parsed.password else ""
    credentials = username_placeholder

    if password_placeholder:
        credentials = f"{credentials}:{password_placeholder}"

    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"

    netloc = f"{credentials}@{host}" if host else credentials

    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def resolve_proxies(proxy_value: str, base_url: str):
    """Return a proxies dict for requests, preferring config over environment.

    An empty return value (None) signals to requests to use its defaults,
    including environment variables.
    """

    proxy_value = (proxy_value or "").strip()
    if proxy_value:
        proxies = {"http": proxy_value, "https": proxy_value}
        logging.info("Using proxy from config: %s", mask_proxy_credentials(proxy_value))
        return proxies

    env_proxies = requests.utils.get_environ_proxies(base_url)
    if env_proxies:
        masked = {k: mask_proxy_credentials(v) for k, v in env_proxies.items()}
        logging.info("Using proxy from environment: %s", masked)
        return env_proxies

    logging.info("No proxy configuration detected; connecting directly.")
    return None


###############################################################################
# CONFIG LOADING
###############################################################################
def load_config(config_path: str = "config.toml") -> dict:
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("rb") as f:
        config = tomllib.load(f)

    if "splunk" not in config:
        raise ValueError("Missing [splunk] section in config.toml")

    if "logging" not in config:
        raise ValueError("Missing [logging] section in config.toml")

    return config


###############################################################################
# SPLUNK FUNCTIONS
###############################################################################
def make_headers(token: str) -> dict:
    return {
        "Authorization": f"Splunk {token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def validate_output_mode(value: str) -> str:
    mode = value.lower().strip()
    if mode not in {"json", "csv"}:
        raise ValueError("output_mode must be either 'json' or 'csv'")
    return mode


def create_search_job(
    base_url: str,
    token: str,
    search: str,
    output_mode: str,
    verify_ssl=True,
    proxies=None,
) -> str:
    endpoint = base_url
    headers = make_headers(token)

    if not search.strip().lower().startswith("search "):
        search = "search " + search.strip()

    data = {
        "search": search,
        # Always request JSON for the job creation response so we can parse the SID
        "output_mode": "json",
    }

    logging.info("Creating search job...")
    resp = requests.post(
        endpoint,
        headers=headers,
        data=data,
        verify=verify_ssl,
        proxies=proxies,
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()

    sid = payload.get("sid")
    logging.info("Search job created. SID: %s", sid)

    return sid


def wait_for_job(base_url, token, sid, verify_ssl, poll, timeout, proxies=None):
    endpoint = f"{base_url}/{sid}"
    headers = make_headers(token)
    params = {"output_mode": "json"}

    logging.info("Waiting for search job to complete...")
    start = time.time()

    while True:
        if time.time() - start > timeout:
            logging.error("Timeout waiting for job %s", sid)
            raise TimeoutError(f"Job {sid} timeout")

        resp = requests.get(
            endpoint,
            headers=headers,
            params=params,
            verify=verify_ssl,
            proxies=proxies,
        )
        resp.raise_for_status()
        content = resp.json()["entry"][0]["content"]

        dispatch_state = content.get("dispatchState", "")
        is_done = content.get("isDone", False)

        if is_done or dispatch_state.lower() == "done":
            logging.info("Job %s completed", sid)
            return

        if dispatch_state.lower() in ("failed", "canceled"):
            logging.error("Search job ended with state %s", dispatch_state)
            raise RuntimeError(f"Job {sid} failed: {dispatch_state}")

        time.sleep(poll)


def fetch_results(base_url, token, sid, output_mode, verify_ssl, proxies=None):
    endpoint = f"{base_url}/{sid}/results"
    headers = make_headers(token)
    params = {"output_mode": output_mode, "count": 0}

    logging.info("Fetching results for job %s", sid)
    resp = requests.get(
        endpoint,
        headers=headers,
        params=params,
        verify=verify_ssl,
        proxies=proxies,
    )
    resp.raise_for_status()

    if output_mode == "json":
        return resp.json().get("results", [])

    return resp.text


def build_output_path(base_path: Path, append_date: bool, suffix_number: int | None = None) -> Path:
    """Return a new path with optional date and numeric suffix appended."""

    suffixes = "".join(base_path.suffixes) or base_path.suffix
    stem = base_path.stem

    if append_date:
        stem = f"{stem}_{datetime.now().strftime('%Y%m%d')}"

    if suffix_number:
        stem = f"{stem}-{suffix_number}"

    return base_path.with_name(f"{stem}{suffixes}")


def write_results(
    results, output_file: str, output_mode: str, append_date_to_filename: bool
):
    # Support full paths and ~ expansion
    base_path = Path(output_file).expanduser()
    output = build_output_path(base_path, append_date_to_filename)

    # Make sure parent dirs exist (for full paths)
    if output.parent and not output.parent.exists():
        output.parent.mkdir(parents=True, exist_ok=True)

    attempt = 0
    while True:
        try:
            logging.info("Writing results to %s", output)

            if output_mode == "json":
                output.write_text(json.dumps(results, indent=2))
                logging.info("Finished writing %d results", len(results))
                return

            if not results:
                logging.warning("No results returned. Creating empty output file.")
                output.write_text("")
                return

            with output.open("w", encoding="utf-8") as f:
                f.write(results)

            logging.info("Finished writing CSV output")
            return
        except PermissionError:
            attempt += 1
            output = build_output_path(base_path, append_date_to_filename, attempt)
            logging.warning(
                "Permission denied when writing results. Retrying with new filename: %s",
                output,
            )



###############################################################################
# MAIN
###############################################################################
def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.toml"

    cfg = load_config(config_file)
    spl = cfg["splunk"]
    log_cfg = cfg["logging"]

    # Setup logging
    setup_logging(
        log_dir=log_cfg.get("log_dir", "logs"),
        retention_days=int(log_cfg.get("retention_days", 7)),
        level=log_cfg.get("log_level", "INFO"),
    )

    base_url = spl["url"].rstrip("/")
    token = spl["token"]
    search = spl["search"]
    output_file = spl["output_file"]
    output_mode = validate_output_mode(spl.get("output_mode", "json"))
    append_date_to_filename = spl.get("append_date_to_output_file", False)

    verify_ssl = spl.get("verify_ssl", True)
    poll = int(spl.get("poll_interval_seconds", 2))
    timeout = int(spl.get("poll_timeout_seconds", 300))
    proxies = resolve_proxies(spl.get("proxy", ""), base_url)

    try:
        sid = create_search_job(
            base_url, token, search, output_mode, verify_ssl, proxies=proxies
        )
        wait_for_job(
            base_url, token, sid, verify_ssl, poll, timeout, proxies=proxies
        )
        results = fetch_results(
            base_url, token, sid, output_mode, verify_ssl, proxies=proxies
        )
        write_results(results, output_file, output_mode, append_date_to_filename)
        logging.info("Splunk search completed successfully.")
    except Exception as e:
        logging.exception("Error running Splunk job: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
