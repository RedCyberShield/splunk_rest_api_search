# Splunk Search Runner

A small Python utility to run a Splunk search via the REST API, wait for completion, and write the results to a file.

Built and maintained by **Red Cyber Shield**.

---

## Features

- Configure everything via `config.toml`
- Uses a Splunk **token** (Authorization: `Splunk <token>`)
- Polls a Splunk search job until completion (with timeout)
- Writes results to **CSV**
- Flexible paths for:
  - Output result file
  - Log directory
- File-based logging with:
  - Configurable log level
  - Log retention by number of days
  - Automatic cleanup of old logs

---

## Repository Layout

Typical layout (you can adjust as needed):

```text
.
├── splunk_search.py
├── config.toml
├── README.md
├── LICENSE
└── .gitignore
