#!/usr/bin/env python3

import csv
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

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


def create_search_job(base_url: str, token: str, search: str, verify_ssl=True) -> str:
    endpoint = f"{base_url}/services/search/jobs"
    headers = make_headers(token)

    if not search.strip().lower().startswith("search "):
        search = "search " + search.strip()

    data = {
        "search": search,
        "output_mode": "json",
    }

    logging.info("Creating search job...")
    resp = requests.post(endpoint, headers=headers, data=data, verify=verify_ssl, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    sid = payload.get("sid")
    logging.info("Search job created. SID: %s", sid)

    return sid


def wait_for_job(base_url, token, sid, verify_ssl, poll, timeout):
    endpoint = f"{base_url}/services/search/jobs/{sid}"
    headers = make_headers(token)
    params = {"output_mode": "json"}

    logging.info("Waiting for search job to complete...")
    start = time.time()

    while True:
        if time.time() - start > timeout:
            logging.error("Timeout waiting for job %s", sid)
            raise TimeoutError(f"Job {sid} timeout")

        resp = requests.get(endpoint, headers=headers, params=params, verify=verify_ssl)
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


def fetch_results(base_url, token, sid, verify_ssl):
    endpoint = f"{base_url}/services/search/jobs/{sid}/results"
    headers = make_headers(token)
    params = {"output_mode": "json", "count": 0}

    logging.info("Fetching results for job %s", sid)
    resp = requests.get(endpoint, headers=headers, params=params, verify=verify_ssl)
    resp.raise_for_status()

    return resp.json().get("results", [])


def write_results_to_csv(results: list[dict], output_file: str):
    # Support full paths and ~ expansion
    output = Path(output_file).expanduser()

    # Make sure parent dirs exist (for full paths)
    if output.parent and not output.parent.exists():
        output.parent.mkdir(parents=True, exist_ok=True)

    logging.info("Writing results to %s", output)

    if not results:
        logging.warning("No results returned. Creating empty output file.")
        output.write_text("")
        return

    fieldnames = sorted({k for row in results for k in row.keys()})

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    logging.info("Finished writing %d results", len(results))


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

    base_url = spl["url"]
    token = spl["token"]
    search = spl["search"]
    output_file = spl["output_file"]

    verify_ssl = spl.get("verify_ssl", True)
    poll = int(spl.get("poll_interval_seconds", 2))
    timeout = int(spl.get("poll_timeout_seconds", 300))

    try:
        sid = create_search_job(base_url, token, search, verify_ssl)
        wait_for_job(base_url, token, sid, verify_ssl, poll, timeout)
        results = fetch_results(base_url, token, sid, verify_ssl)
        write_results_to_csv(results, output_file)
        logging.info("Splunk search completed successfully.")
    except Exception as e:
        logging.exception("Error running Splunk job: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
