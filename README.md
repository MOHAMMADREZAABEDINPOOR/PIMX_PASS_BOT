<div align="center">

# 🤖 PIMX_PASS_BOT ⚡🛡️
### Production-Grade Telegram Bot, Mini App & Multi-Threaded Proxy Scanner Engine

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg?style=for-the-badge)](https://www.gnu.org/licenses/agpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram_Bot_API-v20+-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![SQLite](https://img.shields.io/badge/Database-SQLite3_Async-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Pytest](https://img.shields.io/badge/Tests-Pytest_Suite_Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org/)
[![Read in Persian](https://img.shields.io/badge/مطالعه_به_فارسی-Persian_README-008080?style=for-the-badge)](#-توضیحات-فوقالعاده-جامع-فارسی-persian-documentation)

<p align="center">
  A multi-threaded Telegram bot and interactive Telegram Mini App (TMA) designed for automated proxy health scanning, cryptographic configuration auditing (VLESS, VMess, Trojan, ShadowSocks, WireGuard), user quota management, and high-speed subscription distribution. Features a rigorous 3-stage network probe verification engine.
</p>

[Project Overview](#-project-overview--problem-statement) •
[Directory Structure](#-directory--file-structure) •
[3-Stage Verification Engine](#-strict-3-stage-network-probe-engine) •
[Architecture](#-bot-architecture) •
[Installation & Testing](#-installation--testing) •
[Configuration](#-configuration--environment-variables) •
[توضیحات فارسی](#-توضیحات-فوقالعاده-جامع-فارسی-persian-documentation) •
[License](#-license)

</div>

---

## 🎯 Project Overview & Problem Statement

Users frequently encounter non-functional, expired, or intercepted proxy configurations on public Telegram channels. Manually testing thousands of nodes is tedious and unreliable.

**PIMX_PASS_BOT** solves this by acting as an automated proxy quality filter:
- **Massive Ingestion**: Ingests hundreds of configuration strings from upstream providers.
- **Strict 3-Stage Probe Testing**: Discards dead or packet-dropping nodes before users ever touch them.
- **Telegram Mini App (TMA)**: Users can browse real-time server pings, select locations, and copy functional configurations via an interactive in-app browser interface.

---

## 📂 Directory & File Structure

```
bot/
│
├── main.py                          # Application entry point, CLI flags & process orchestrator
├── requirements.txt                 # Python dependencies (python-telegram-bot, pytest, aiosqlite)
├── key.pem                          # SSL certificate for local HTTPS webhook testing
├── README.md                        # Master comprehensive bilingual documentation
├── README_TESTING.md                # Specialized guide for running pytest suites
├── TESTING_SUMMARY.md               # Summary of the 21 unit test cases and scanner diagnosis
├── run_tests.ps1                    # Automated PowerShell script executing scanner test suites
│
├── pimx_bot/                        # Core Python Package
│   ├── config.py                    # Environment variable loader, defaults & threshold constants
│   ├── db.py                        # SQLite asynchronous schema & user quota manager
│   ├── parser.py                    # Multi-protocol URI parser (vless://, vmess://, trojan://, ss://)
│   ├── providers.py                 # Remote subscription fetchers & channel scrapers
│   ├── scanner.py                   # Multi-worker asynchronous scanner dispatcher
│   ├── server_tester.py             # 3-Stage TCP/TLS and HTTP probe verification engine
│   ├── telegram_app.py              # Telegram command handlers, callback queries & inline menus
│   ├── web_server.py                # Embedded lightweight HTTP server serving Mini App assets
│   └── static/
│       └── webapp.html              # Responsive Telegram Mini App single-page application
│
├── data/                            # Persistent state
│   ├── pimx_bot.db                  # SQLite database storing users, servers & test logs
│   ├── pimx_bot.db-wal              # Write-Ahead Log for high-concurrency database writes
│   └── pimx_bot.db-shm              # Shared memory index for SQLite WAL mode
│
└── scripts/                         # Operational deployment scripts
    ├── nginx_pimxpass_webapp.conf   # Production Nginx reverse proxy configuration for Mini App
    └── push_to_github.ps1           # Deployment and sync script
```

---

## 🔬 Strict 3-Stage Network Probe Engine

Unlike simple ping utilities that only measure ICMP echo, `pimx_bot/server_tester.py` uses an authentic 3-stage validation cycle:

```
[ Unverified Node Candidate ]
              │
              ▼
┌──────────────────────────────────────────────┐
│  Stage 1: TCP/TLS Handshake Check            │
│  - Verifies socket connectivity              │
│  - Validates TLS certificate negotiation     │
└──────────────────────┬───────────────────────┘
                       │ (Pass)
                       ▼
┌──────────────────────────────────────────────┐
│  Stage 2: HTTP HEAD Request                  │
│  - Sends synthetic HTTP request              │
│  - Measures Time to First Byte (TTFB)        │
└──────────────────────┬───────────────────────┘
                       │ (Pass)
                       ▼
┌──────────────────────────────────────────────┐
│  Stage 3: Protocol-Specific Payload Probe    │
│  - WebSocket handshake / gRPC stream check   │
│  - Asserts end-to-end packet transmission    │
└──────────────────────┬───────────────────────┘
                       │ (Pass)
                       ▼
     [ Verified Active Server Added to Pool ]
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `BOT_TOKEN` | `string` | `""` | Telegram Bot API token from [@BotFather](https://t.me/BotFather). |
| `ADMIN_ID` | `int` | `0` | Numeric Telegram ID of administrator for broadcast commands. |
| `SERVERS_TO_TEST` | `int` | `1000` | Maximum candidate nodes queued per scan cycle. |
| `MAX_LATENCY_MS` | `int` | `300` | Maximum acceptable round-trip latency in milliseconds. |
| `MIN_SELECTED_SERVERS`| `int` | `50` | Minimum quota of active servers retained in the output pool. |
| `DATABASE_PATH` | `string` | `data/pimx_bot.db` | Filesystem path to SQLite relational database. |

---

## 🚀 Installation & Testing

### 1. Installation
```bash
git clone https://github.com/MOHAMMADREZAABEDINPOOR/PIMX_PASS_BOT.git
cd PIMX_PASS_BOT

python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run Automated Pytest Suite
```bash
pytest tests/ -v
# Or run with the PowerShell helper:
.\run_tests.ps1
```

### 3. Launch Bot
```bash
python main.py
```

---

## 🇮🇷 توضیحات فوق‌العاده جامع فارسی (Persian Documentation)

### ۱. معرفی پروژه ربات PIMX_PASS_BOT
پروژه **PIMX_PASS_BOT** یک سیستم اتوماتیک، پیشرفته و چندنخی در تلگرام برای اسکن، تست سلامت و توزیع کانفیگ‌های پروکسی است. این ربات دارای مینی‌اپلیکیشن داخلی (**Telegram Mini App**) بوده و به کاربران اجازه می‌دهد بدون خروج از تلگرام، سرعت واقعی سرورها را مشاهده کرده و سرورهای پرسرعت را با یک کلیک کپی کنند.

---

### ۲. تشریح ساختار پوشه‌ها و فایل‌های پروژه
- **`main.py`**: نقطه ورود و راه‌انداز اصلی ربات و وب‌سرور داخلی.
- **`pimx_bot/server_tester.py`**: موتور آزمون ۳ مرحله‌ای شبکه (بررسی سوکت TCP، ارسال هدر HTTP، و اعتبارسنجی جریان داده وب‌سوکت یا gRPC).
- **`pimx_bot/parser.py`**: تجزیه‌کننده هوشمند انواع لینک‌های پروکسی (VLESS, VMess, Trojan, Shadowsocks).
- **`pimx_bot/telegram_app.py`**: کنترل‌کننده دستورات کاربری، منوهای شیشه‌ای و ارسال پیام‌های همگانی.
- **`pimx_bot/static/webapp.html`**: رابط گرافیکی جذاب مینی‌اپلیکیشن تلگرام با قابلیت رندر زنده پینگ سرورها.
- **`data/pimx_bot.db`**: دیتابیس SQLite برای ذخیره کاربران و سرورهای سالم.

---

### ۳. الگوریتم تست ۳ مرحله‌ای سرورها:
1. **تست اول (اتصال فیزیکی TCP/TLS):** بررسی باز بودن پورت سرور و برقراری موفق هندشیک رمزگذاری‌شده.
2. **تست دوم (ارسال درخواست HTTP HEAD):** اندازه‌گیری تأخیر پاسخ‌دهی لایه وب سرور.
3. **تست سوم (انتقال بسته در پروتکل اختصاصی):** ارسال داده واقعی در بستر پروتکل برای اطمینان از قطع نبودن ترافیک در شبکه ایران.

---

## 📜 License

Distributed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

---

<div align="center">
  <sub>Engineered by <a href="https://github.com/MOHAMMADREZAABEDINPOOR">MOHAMMADREZA ABEDINPOOR</a>. Leave a ⭐ to support open internet access!</sub>
</div>
