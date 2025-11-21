#!/usr/bin/env python
"""
Cross-platform setup script for the Splunk Search Runner.

- Detects OS (Windows / macOS / Linux)
- Ensures Python 3.8+
- Creates a virtual environment in ./venv
- Installs dependencies from requirements.txt (if present)
  or falls back to installing 'requests' and 'tomli' directly.

Run with:
    python setup_env.py
"""

import os
import sys
import subprocess
from pathlib import Path
import platform


def run(cmd, **kwargs):
    print(f"Running: {' '.join(map(str, cmd))}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        raise SystemExit(f"Command failed with exit code {result.returncode}")


def main():
    print("=== Red Cyber Shield – Splunk Search Runner Setup ===")

    # ----- Detect OS -----
    system = platform.system().lower()
    if "windows" in system:
        os_name = "windows"
    elif "darwin" in system:
        os_name = "macos"
    elif "linux" in system:
        os_name = "linux"
    else:
        os_name = system  # fallback

    print(f"Detected OS: {os_name}")

    # ----- Check Python version -----
    major, minor = sys.version_info[:2]
    print(f"Python version detected: {major}.{minor}")
    if major < 3 or (major == 3 and minor < 8):
        raise SystemExit("ERROR: Python 3.8+ is required.")

    # ----- Create virtual environment -----
    venv_dir = Path("venv")
    if not venv_dir.exists():
        print("Creating virtual environment in ./venv ...")
        run([sys.executable, "-m", "venv", "venv"])
    else:
        print("Virtual environment ./venv already exists, skipping creation.")

    # ----- Determine venv Python path -----
    if os_name == "windows":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        raise SystemExit(f"ERROR: Could not find venv python at {venv_python}")

    # ----- Upgrade pip -----
    print("Upgrading pip in the virtual environment...")
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])

    # ----- Install dependencies -----
    req_file = Path("requirements.txt")
    if req_file.is_file():
        print("Installing dependencies from requirements.txt ...")
        run([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        print("requirements.txt not found, installing minimal deps directly...")
        deps = ["requests", "tomli"]
        run([str(venv_python), "-m", "pip", "install"] + deps)

    # ----- Final instructions -----
    print("\n=== Setup Complete ===")
    print("Virtual environment created in ./venv and dependencies installed.\n")

    if os_name == "windows":
        print("To activate the virtual environment, run:")
        print(r"  .\venv\Scripts\Activate.ps1  (PowerShell)")
        print(r"  .\venv\Scripts\activate.bat   (cmd.exe)")
    else:
        print("To activate the virtual environment, run:")
        print("  source venv/bin/activate")

    print("\nOnce activated, run the tool with:")
    print("  python splunk_search.py  [optional path/to/config.toml]\n")


if __name__ == "__main__":
    main()
