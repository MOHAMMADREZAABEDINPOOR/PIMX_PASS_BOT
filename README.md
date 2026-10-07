<div align="center">

<img src="assets/readme/hero.gif" width="1200" alt="PIMX PASS BOT — rotating 3D geometry" />

**[English](README.md) · [فارسی](README.fa.md)**

<img src="assets/readme/identity.svg" width="1200" alt="ai / English and Persian documentation" />

</div>

# PIMX PASS BOT

A Telegram bot and companion web interface for finding, parsing and testing network/server configurations. Python modules separate providers, scanning, storage and web serving.

[GitHub](https://github.com/MOHAMMADREZAABEDINPOOR/PIMX_PASS_BOT) · [PIMX / Profile](https://github.com/MOHAMMADREZAABEDINPOOR) · [Static artwork](assets/readme/hero.png)

## Features

- Telegram commands and interactive UI
- Provider adapters and configuration parsing
- Scanner, server tester and database layer
- Web companion with configurable host/port

## Stack

| Tool | Version / source |
|---|---|
| python-telegram-bot[job-queue]>=21.0,<22 | `requirements.txt` |
| aiosqlite>=0.20,<1 | `requirements.txt` |
| cryptography>=41.0.0 | `requirements.txt` |

## Getting started

Python 3; a desktop/Tk installation for Tkinter or turtle examples. Tkinter is provided by the Python installation, not pip. Legacy dependencies may need a compatible Python version.

```bash
git clone https://github.com/MOHAMMADREZAABEDINPOOR/PIMX_PASS_BOT.git
cd PIMX_PASS_BOT

python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1; macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
# Copy .env.example to .env and configure BOT_TOKEN
python main.py
```

## Configuration

These names are found in the example configuration or source; not all are required. Check their defaults/usage in those files and supply secrets only in your local or hosting environment.

| Name | Role |
|---|---|
| `ACTIVE_CONFIRMATIONS` | Application setting; inspect its definition |
| `API_BASE_URL` | Application setting; inspect its definition |
| `BOT_TOKEN` | Credential/connection setting; keep private |
| `CHANNEL_ID` | Application setting; inspect its definition |
| `CHANNEL_LINK` | Application setting; inspect its definition |
| `CHANNEL_USERNAME` | Application setting; inspect its definition |
| `CORE_PATH_SEARCH_TIMEOUT_SECONDS` | Application setting; inspect its definition |
| `CORE_STARTUP_TIMEOUT_SECONDS` | Application setting; inspect its definition |
| `CORE_TEST_CONCURRENCY` | Application setting; inspect its definition |
| `DATA_PROVIDER` | Application setting; inspect its definition |
| `DB_PATH` | Application setting; inspect its definition |
| `LIST_UPDATE_INTERVAL_SECONDS` | Application setting; inspect its definition |
| `MAX_CONCURRENCY` | Application setting; inspect its definition |
| `MAX_LATENCY_MS` | Application setting; inspect its definition |
| `MAX_SELECTED_SERVERS` | Application setting; inspect its definition |
| `MEMBERSHIP_CHECK_INTERVAL_SECONDS` | Application setting; inspect its definition |
| `MIN_SELECTED_SERVERS` | Application setting; inspect its definition |
| `PORT` | Application setting; inspect its definition |
| `PUBLIC_BASE_URL` | Application setting; inspect its definition |
| `READ_DB_POOL_SIZE` | Application setting; inspect its definition |
| `REAL_TEST_MODE` | Application setting; inspect its definition |
| `SCAN_INTERVAL_SECONDS` | Application setting; inspect its definition |
| `SERVERS_PER_PAGE` | Application setting; inspect its definition |
| `SERVERS_TO_TEST` | Application setting; inspect its definition |
| `SESSION_TTL_SECONDS` | Application setting; inspect its definition |
| `SOURCE_FETCH_TIMEOUT_SECONDS` | Application setting; inspect its definition |
| `TEST_TARGET_HOST` | Application setting; inspect its definition |
| `TEST_TARGET_MODE` | Application setting; inspect its definition |
| `TEST_TARGET_PATH` | Application setting; inspect its definition |
| `TEST_TARGET_PORT` | Application setting; inspect its definition |
| `TEST_TIMEOUT_SECONDS` | Application setting; inspect its definition |
| `WEBSITE_URL` | Application setting; inspect its definition |
| `WEB_HOST` | Application setting; inspect its definition |
| `WEB_PORT` | Application setting; inspect its definition |
| `WEB_SKIP_TOP_SERVERS` | Application setting; inspect its definition |
| `WEB_SSL_CERT` | Application setting; inspect its definition |
| `WEB_SSL_KEY` | Credential/connection setting; keep private |
| `XRAY_PATH` | Application setting; inspect its definition |

## Usage

Copy .env.example to .env, set BOT_TOKEN and select the data provider. Run main.py, open the bot and use its available scanning controls. Configure PUBLIC_BASE_URL for a hosted Mini App.

## Project structure

| Path | Role |
|---|---|
| [`assets/`](assets/) | Brand/media/README assets |
| [`pimx_bot/`](pimx_bot/) | Bot/web modules |
| [`scripts/`](scripts/) | Development and maintenance utilities |
| [`main.py`](main.py) | Project entry/configuration file |
| [`test_miniapp.py`](test_miniapp.py) | Project entry/configuration file |

## Commands and checks

No automated test command is declared in a manifest. Verify behavior through a local example run.

## Deployment

Host a long-running bot process with environment secrets and private storage. Run a single polling instance. Check network access and dependency compatibility on the host.

## Limitations

Availability of public servers is temporary. Telegram web experiences require an externally reachable HTTPS URL. Local certificates and user databases must remain outside version control.

## Troubleshooting

- Authentication/provider errors: verify credentials and selected model/provider.
- No Telegram updates: check polling/webhook mode and concurrent bot instances.
- Missing dependencies: use the declared manifest or inspect imports if no manifest is provided.

## Contributing

Create a focused branch, verify the affected behavior and explain the change clearly. Keep private data, build outputs and local databases out of commits.

Supporting guides:

- [README_TESTING.md](README_TESTING.md)

## License

No repository-level license file is included in this snapshot. Public visibility alone does not grant reuse rights; contact the repository owner for terms.

---

Part of **PIMX** · Documentation in English and Persian.
