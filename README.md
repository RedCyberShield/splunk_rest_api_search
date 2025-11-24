# Splunk Search Runner  
Built and maintained by **Red Cyber Shield**

This tool runs a Splunk search through the Splunk REST API, waits for the job to complete, and exports the results to a CSV file.  
All behavior is controlled by a simple `config.toml` file.

---

## 1. Environment Setup (Windows, macOS, Linux)

This project includes a fully cross-platform setup script: **`setup_env.py`**.  
It will:

- Detect your operating system  
- Check your Python version  
- Create a virtual environment (`venv/`)  
- Install all dependencies automatically  

### 1.1 Run the setup script

From the project root (where `setup_env.py` is):

**Windows:**

```powershell
python setup_env.py
```

**macOS & Linux:**

```bash
python3 setup_env.py
```

### 1.2 What the setup script does

- Verifies Python 3.8+ is installed  
- Creates `./venv/` if it does not already exist  
- Installs dependencies from `requirements.txt`:
  - `requests`
  - `tomli` (for Python < 3.11)
- Prints instructions for activating the virtual environment  

---

## 2. Activating the Virtual Environment

After setup completes, activate the environment:

### 2.1 Windows (PowerShell)

```powershell
.\env\Scripts\Activate.ps1
```

### 2.2 Windows (CMD)

```cmd
venv\Scripts\activate.bat
```

### 2.3 macOS / Linux

```bash
source venv/bin/activate
```

When active, your terminal prompt will usually show something like:

```
(venv)
```

---

## 3. Configuring `config.toml`

All settings are controlled through the **`config.toml`** file.  
This file must exist in the same directory as `splunk_search.py` unless you specify a custom path when running the program.

### Example `config.toml`

```toml
[splunk]
# Splunk Search Jobs endpoint (no trailing slash)
url = "https://your-splunk-host:8089/services/search/v2/jobs"
token = "YOUR_SPLUNK_TOKEN_HERE"
search = "search index=_internal | head 10"

# Saved search support
saved_search = false
saved_search_name = ""
saved_search_user = ""
saved_search_app = ""

output_file = "results.csv"
output_mode = "json"  # or "csv"
append_date_to_output_file = false
verify_ssl = true
proxy = ""  # Set to your proxy URL or leave blank to use system settings
poll_interval_seconds = 2
poll_timeout_seconds = 300

[logging]
log_dir = "logs"
retention_days = 7
log_level = "INFO"
```

### Notes

- `output_file` supports full paths and auto-creates directories.
- `append_date_to_output_file` adds a `YYYYMMDD` suffix to the filename before
  the extension when set to `true`.
- Set `saved_search` to `true` and provide `saved_search_user`/`saved_search_app`
  to run a saved search through the `/servicesNS/<user>/<app>/search/jobs/export`
  endpoint. The tool will continue to poll results from the standard jobs
  endpoint configured in `url`.
- `log_dir` supports full paths and will be created if missing.
- Splunk search behavior matches the Splunk UI.
- If `proxy` is left blank, the tool will log and rely on any system proxy
  settings (e.g., `HTTP_PROXY`/`HTTPS_PROXY`).

---

## 4. Running the Program

### Basic run

```bash
python splunk_search.py
```

### Run with custom config path

```bash
python splunk_search.py /path/to/config.toml
```

---

## 5. What the Program Does

1. Loads configuration  
2. Initializes logging  
3. Creates Splunk search job  
4. Polls job until done or timeout  
5. Fetches results  
6. Writes results to CSV  

---

## 6. Output Files

### CSV Results

Stored at the location specified in `output_file`.

### Logs

Stored in:

```
logs/
```

(or the folder defined in `log_dir`)

---

## 7. Troubleshooting

### SSL Errors  
Set:

```toml
verify_ssl = false
```

### Authentication Errors  
Check token and Splunk URL.

### Empty CSV  
Run the search manually in Splunk to verify results.

### Permission Issues  
Ensure write access to directories.

---

## 8. Project Structure

```
splunk_search.py
config.toml
setup_env.py
requirements.txt
pyproject.toml
README.md
LICENSE
.gitignore
```

---

## 9. License

Licensed under the MIT License.  
Built and maintained by **Red Cyber Shield**.
