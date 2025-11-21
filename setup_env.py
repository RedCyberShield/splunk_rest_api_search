#!/usr/bin/env python
"""
Cross-platform setup script for the Splunk Search Runner (offline).

- Detects OS (Windows / macOS / Linux)
- Ensures Python 3.8+
- Creates a virtual environment in ./venv
- Installs dependencies ONLY from ./offline-libs using:
    pip install --no-deps --no-index <all-wheels>

No internet access required.
"""

import sys
import subprocess
from pathlib import Path
import platform


def run(cmd):
    print(f"Running: {' '.join(map(str, cmd))}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"Command failed with exit code {result.returncode}")


def main():
    print("=== Red Cyber Shield – Offline Setup ===")

    # ----- OS info (mostly just for logging) -----
    system = platform.system().lower()
    if "windows" in system:
        os_name = "windows"
    elif "darwin" in system:
        os_name = "macos"
    elif "linux" in system:
        os_name = "linux"
    else:
        os_name = system
    print(f"Detected OS: {os_name}")

    # ----- Python version check -----
    major, minor = sys.version_info[:2]
    print(f"Python version: {major}.{minor}")
    if major < 3 or (major == 3 and minor < 8):
        raise SystemExit("ERROR: Python 3.8+ is required.")

    project_root = Path(__file__).parent.resolve()
    venv_dir = project_root / "venv"
    offline_libs = project_root / "offline-libs"

    # ----- Create venv if needed -----
    if not venv_dir.exists():
        print("Creating virtual environment in ./venv ...")
        run([sys.executable, "-m", "venv", str(venv_dir)])
    else:
        print("Virtual environment ./venv already exists, skipping creation.")

    # ----- venv python path -----
    if os_name == "windows":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        raise SystemExit(f"ERROR: venv python not found at {venv_python}")

    # ----- Find offline wheels -----
    if not offline_libs.is_dir():
        raise SystemExit(f"ERROR: offline-libs directory not found at {offline_libs}")

    wheel_files = sorted(offline_libs.glob("*.whl"))
    if not wheel_files:
        raise SystemExit(f"ERROR: No .whl files found in {offline_libs}")

    print("Found the following offline wheels:")
    for w in wheel_files:
        print(f"  - {w.name}")

    # ----- Install all wheels with no deps and no index -----
    print("\nInstalling dependencies from offline-libs ...")
    cmd = [
        str(venv_python),
        "-m",
        "pip",
        "install",
        "--no-deps",
        "--no-index",
    ] + [str(w) for w in wheel_files]

    run(cmd)

    print("\n=== Offline setup complete ===")
    if os_name == "windows":
        print("Activate the venv with:")
        print(r"  .\venv\Scripts\Activate.ps1  (PowerShell)")
        print(r"  .\venv\Scripts\activate.bat   (cmd.exe)")
    else:
        print("Activate the venv with:")
        print("  source venv/bin/activate")

    print("\nThen run:")
    print("  python splunk_search.py  [optional path/to/config.toml]\n")


if __name__ == "__main__":
    main()
