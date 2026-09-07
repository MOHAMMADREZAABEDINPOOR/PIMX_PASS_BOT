<div align="center">

<!-- ============================================================================== -->
<!-- DYNAMIC ANIMATED CAPSULE HEADER                                                -->
<!-- ============================================================================== -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1,12,24,30&height=220&section=header&text=PIMX_PASS_BOT&fontSize=40&fontAlignY=35&desc=%F0%9F%9B%91%20Archived%20Open-Source%20Proxy%20Scanner%20%26%20Bot%20Reference&descFontSize=16&descAlignY=62" alt="PIMX_PASS_BOT Banner" width="100%" />

<!-- ============================================================================== -->
<!-- ANIMATED TYPING SVG TELEMETRY                                                 -->
<!-- ============================================================================== -->
<a href="https://github.com/MOHAMMADREZAABEDINPOOR/PIMX_PASS_BOT">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&duration=2800&pause=1000&color=00D2FF&center=true&vCenter=true&width=780&lines=Project+Status%3A+Inactive+%2F+Archived+Open-Source+Codebase;High-Concurrency+Telegram+Bot+Engine+(Python+3.10%2B+%26+Asyncio);Interactive+Telegram+Mini+App+(TMA)+with+Live+Latency+Pings;Strict+3-Stage+Network+Probe+Verification+Engine;Multi-Protocol+Config+Auditing+(VLESS%2C+VMess%2C+Trojan%2C+SS);Comprehensive+Pytest+Suite+with+21+Automated+Unit+Tests;Async+SQLite3+Persistence+with+Write-Ahead+Logging+(WAL)" alt="Typing SVG" />
</a>

<br/>

<!-- ============================================================================== -->
<!-- BADGES MATRIX                                                                  -->
<!-- ============================================================================== -->
[![Project Status: Inactive / Archived](https://img.shields.io/badge/Status-Inactive%20%7C%20Archived-critical?style=for-the-badge&logo=archive)](https://github.com/MOHAMMADREZAABEDINPOOR)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg?style=for-the-badge&logo=gnu)](https://www.gnu.org/licenses/agpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram_Bot_API-v20+-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![SQLite](https://img.shields.io/badge/Database-SQLite3_Async-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Pytest](https://img.shields.io/badge/Tests-Pytest_Suite_Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org/)
[![Read in Persian](https://img.shields.io/badge/مطالعه_به_فارسی-Persian_README-008080?style=for-the-badge)](#-بخش-فوقالعاده-مفصل-و-جامع-به-زبان-فارسی-persian-documentation)

<p align="center">
  <b>PIMX_PASS_BOT</b> is an asynchronous Telegram bot and embedded Telegram Mini App (TMA) engineered for high-concurrency proxy validation, automated protocol benchmarking (VLESS, VMess, Trojan, ShadowSocks, WireGuard), user quota management, and high-speed subscription distribution. Equipped with an authentic 3-stage network probe verification engine, PIMX_PASS_BOT discards dead and packet-dropping nodes before users ever touch them.
</p>

<!-- ============================================================================== -->
<!-- QUICK NAVIGATION ANCHORS                                                       -->
<!-- ============================================================================== -->
[Project Overview](#-project-overview--problem-statement) •
[Directory Anatomy](#-exhaustive-directory--file-anatomy) •
[3-Stage Verification Engine](#-strict-3-stage-network-probe-engine) •
[Architecture & Dataflow](#-bot-architecture--dataflow) •
[Testing Suite](#-automated-pytest-verification-suite) •
[Installation Guide](#-installation--deployment) •
[Configuration](#-configuration--environment-variables) •
[توضیحات فارسی](#-بخش-فوقالعاده-مفصل-و-جامع-به-زبان-فارسی-persian-documentation) •
[Roadmap](#-strategic-engineering-roadmap) •
[License](#-copyleft-license--legal-attribution)

</div>

---

> [!CAUTION]
> ### 🛑 Project Status: Inactive / Archived (پروژه غیرفعال و بایگانی‌شده)
> **Notice**: This repository is currently **inactive** and maintained solely as an archived open-source reference / legacy codebase. The bot is not currently running in production, and active infrastructure has been decommissioned.
>
> **توجه مهم**: این ریپازیتوری در حال حاضر **کاملاً غیرفعال (Inactive / Archived)** است و صرفاً به عنوان آرشیو سورس‌کد و مرجع متن‌باز نگهداری می‌شود. هیچ ربات یا سرور فعالی بر روی آن در حال اجرا نیست.

## ⚡ Project Overview & Problem Statement

> *"Public proxy channels are saturated with dead links, expired certificates, and throttled endpoints. **PIMX_PASS_BOT** acts as an automated, multi-threaded triage hospital — filtering out broken nodes in milliseconds."*

### The Problem of Stale & Broken Configurations
Users attempting to bypass censorship through public Telegram channels frequently experience severe frustration:
1. **Dead Nodes & Timeouts**: Over 80% of configurations shared in public Telegram channels are either completely dead or suffer from packet drop rates exceeding 90%.
2. **Slow Manual Auditing**: Manually importing 50 different VLESS or VMess links into client apps to find a single working node wastes hours.
3. **FloodWait & API Throttling**: Standard Telegram bots crash or get throttled when handling hundreds of users simultaneously without asynchronous rate limiting.

### The PIMX_PASS_BOT Solution
**PIMX_PASS_BOT** automates the entire ingestion, validation, and delivery pipeline:
- 🔍 **Strict 3-Stage Testing**: Tests TCP/TLS sockets, dispatches HTTP HEAD requests, and validates end-to-end WebSocket/gRPC handshakes.
- 📱 **Interactive Telegram Mini App**: Users browse server nodes, examine ping latency bars, and copy functional configurations without leaving Telegram.
- ⚡ **Asynchronous Concurrency**: Built with `python-telegram-bot` v20+ and `AIORateLimiter` to gracefully handle heavy traffic surges.
- 🗄️ **High-Performance SQLite WAL**: Fast persistent storage for user accounts, quotas, and benchmark histories.

---

## 📂 Exhaustive Directory & File Anatomy

```
d:/code/bot/
│
├── main.py                          # Application bootstrap: argument parsing, loop setup & bot launch
├── requirements.txt                 # Dependencies (python-telegram-bot, aiosqlite, pytest, aiohttp)
├── key.pem                          # SSL cryptographic certificate for local HTTPS webhook testing
├── README.md                        # Master comprehensive bilingual documentation
├── README_TESTING.md                # Specialized guide detailing test cases & mock socket environments
├── TESTING_SUMMARY.md               # Summary of the 21 unit test cases and scanner diagnosis
├── run_tests.ps1                    # Automated PowerShell script executing test runner
│
├── pimx_bot/                        # Core Application Package
│   ├── __init__.py                  # Package initialization
│   ├── config.py                    # Environment variable loader, defaults & threshold constants
│   ├── db.py                        # SQLite asynchronous schema, user tables & quota manager
│   ├── parser.py                    # Multi-protocol URI parser (vless://, vmess://, trojan://, ss://)
│   ├── providers.py                 # Remote subscription fetchers & channel scrapers
│   ├── scanner.py                   # Multi-worker asynchronous scanner dispatcher
│   ├── server_tester.py             # 3-Stage TCP/TLS and HTTP probe verification engine
│   ├── telegram_app.py              # Telegram command handlers, callback queries & inline menus
│   ├── web_server.py                # Embedded lightweight HTTP server serving Mini App assets
│   └── static/
│       └── webapp.html              # Responsive Telegram Mini App single-page application
│
├── data/                            # Persistent Storage Directory
│   ├── pimx_bot.db                  # Primary SQLite relational database file
│   ├── pimx_bot.db-wal              # Write-Ahead Log ensuring non-blocking concurrent writes
│   └── pimx_bot.db-shm              # Shared memory index for WAL operations
│
└── scripts/                         # Operational & DevOps Toolchain
    ├── nginx_pimxpass_webapp.conf   # Production Nginx reverse proxy configuration for Mini App
    └── push_to_github.ps1           # Deployment and sync script
```

---

## 🔬 Strict 3-Stage Network Probe Engine

Unlike simple ping utilities that only measure ICMP echo, `pimx_bot/server_tester.py` uses an authentic 3-stage validation cycle:

```
[ Candidate Node (VLESS / VMess / Trojan) ]
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│  Stage 1: TCP/TLS Socket Handshake                     │
│  - Verifies host resolution and open port               │
│  - Completes cryptographic TLS 1.3 handshake           │
│  - Measures socket establishment duration              │
└──────────────────────────┬─────────────────────────────┘
                           │ (Pass: Socket Open)
                           ▼
┌────────────────────────────────────────────────────────┐
│  Stage 2: HTTP HEAD Request                            │
│  - Dispatches synthetic HTTP HEAD request              │
│  - Asserts valid HTTP response code (200, 101, 404)    │
│  - Measures Time to First Byte (TTFB)                  │
└──────────────────────────┬─────────────────────────────┘
                           │ (Pass: Web Layer Healthy)
                           ▼
┌────────────────────────────────────────────────────────┐
│  Stage 3: Protocol-Specific Payload Probe              │
│  - WebSocket Upgrade handshake (101 Switching Protocols│
│  - Validates gRPC HTTP/2 stream headers                │
│  - Confirms zero packet dropping                       │
└──────────────────────────┬─────────────────────────────┘
                           │ (Pass: End-to-End Verified)
                           ▼
          [ Stored in Active Verified Node Pool ]
```

---

## 🧪 Automated Pytest Verification Suite

The project includes an enterprise-grade test suite covering all critical subsystems:
- **`tests/test_scanner.py`**: Contains **759 lines of code** across **21 test cases** and **6 test classes**.
- **Mock Socket Testing**: Simulates network timeouts, connection resets, and TLS handshake failures to ensure graceful degradation without crashing worker threads.

To run the automated test suite:
```bash
# In project root:
pytest tests/ -v
# Or using the PowerShell automation script:
.\run_tests.ps1
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Type | Default Value | Description |
| :--- | :---: | :---: | :--- |
| `BOT_TOKEN` | `string` | `""` | Telegram Bot API token obtained from [@BotFather](https://t.me/BotFather). |
| `ADMIN_ID` | `int` | `0` | Numeric Telegram user ID of administrator for broadcast commands. |
| `SERVERS_TO_TEST` | `int` | `1000` | Maximum candidate nodes queued per scan cycle. |
| `MAX_LATENCY_MS` | `int` | `300` | Maximum acceptable round-trip latency threshold in milliseconds. |
| `MIN_SELECTED_SERVERS`| `int` | `50` | Minimum quota of active servers retained in the output pool. |
| `DATABASE_PATH` | `string` | `data/pimx_bot.db` | Filesystem path to SQLite relational database file. |
| `ENABLE_WEBAPP` | `bool` | `true` | Enables embedded HTTP server hosting the Telegram Mini App. |

---

## 🚀 Installation & Deployment

### 1. Prerequisites
- **Python**: v3.10 or higher
- **Telegram Bot Token**: From [@BotFather](https://t.me/BotFather)

### 2. Setup Virtual Environment
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

### 3. Launch Bot Daemon
```bash
python main.py
```

---

## 🇮🇷 بخش فوق‌العاده مفصل و جامع به زبان فارسی (Persian Documentation)

### ۱. مقدمه و چرایی ساخت ربات PIMX_PASS_BOT
پروژه **PIMX_PASS_BOT** یک ربات هوشمند، پیشرفته و چندنخی در بستر پیام‌رسان تلگرام است که به صورت تخصصی برای اسکن خودکار، اعتبارسنجی کیفیت و توزیع کانفیگ‌های فیلترشکن و پروکسی مهندسی شده است. این ربات مجهز به یک **مینی‌اپلیکیشن اختصاصی تلگرام (Telegram Mini App)** است که به کاربران اجازه می‌دهد بدون نیاز به کپی کردن دستی ده‌ها کانفیگ نامطمئن، پینگ زنده سرورها را درون چت مشاهده کرده و سرورهای سالم را دریافت کنند.

---

### ۲. تشریح ساختار پوشه‌ها و فایل‌های پروژه
- **`main.py`**: فایل اصلی راه‌اندازی ربات، پیکربندی صف‌های پردازشی ناهمگام (Asyncio) و اجرای همزمان وب‌سرور داخلی مینی‌اپ.
- **`pimx_bot/server_tester.py`**: موتور تست ۳ مرحله‌ای تخصصی شبکه؛ اعتبارسنجی لایه سوکت TCP، ارسال هدر HTTP، و بررسی هندشیک نهایی وب‌سوکت یا gRPC.
- **`pimx_bot/parser.py`**: تجزیه‌کننده هوشمند پروتکل‌های VLESS، VMess، Trojan و Shadowsocks جهت تفکیک آدرس سرور، پورت، UUID، و پارامترهای TLS.
- **`pimx_bot/telegram_app.py`**: مدیریت دستورات تلگرام، منوهای شیشه‌ای اینلاین، پیام‌های خوش‌آمدگویی و سیستم ریت‌لیمیتینگ جهت ممانعت از مسدود شدن توکن ربات توسط تلگرام.
- **`pimx_bot/static/webapp.html`**: رابط گرافیکی وب‌اپلیکیشن داخلی تلگرام با طراحی مدرن و نمایش پینگ رنگی سرورها.
- **`data/pimx_bot.db`**: دیتابیس محلی SQLite با تنظیمات پیشرفته WAL (Write-Ahead Logging) برای جلوگیری از تداخل تراکنش‌های همزمان.

---

### ۳. الگوریتم آزمون ۳ مرحله‌ای سرورها:
1. **مرحله اول (هندشیک سوکت TCP/TLS):** تست برقراری موفق ارتباط فیزیکی با آی‌پی سرور و مذاکره موفق گواهی امنیتی TLS.
2. **مرحله دوم (درخواست HTTP HEAD):** ارسال درخواست وب برای سنجش سرعت دریافت اولین بایت (TTFB).
3. **مرحله سوم (تست پروتکل اختصاصی):** ارسال داده در بستر وب‌سوکت (101 Switching Protocols) یا جریان gRPC برای اطمینان از مسدود نبودن در شبکه ملی.

---

## 🗺️ Strategic Engineering Roadmap

- [x] **v1.0**: Core async Telegram Bot, parser for VLESS/Trojan, SQLite storage.
- [x] **v1.5**: Telegram Mini App (TMA) embedded GUI, automated pytest test suite.
- [ ] **v2.0**: Geolocation IP lookup displaying flag emojis and ISP names alongside ping.
- [ ] **v2.5**: Automated speed test measuring actual megabits-per-second download throughput.
- [ ] **v3.0**: Distributed peer testing nodes verifying proxy connectivity from multiple Iranian ISPs simultaneously.

---

## 📜 Copyleft License & Legal Attribution

Distributed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.  
Under this copyleft covenant, any derivative software, hosted web application, or commercial software-as-a-service (SaaS) utilizing components of this repository MUST make its complete corresponding source code freely accessible under identical AGPL-3.0 terms.

---

<div align="center">

<!-- ============================================================================== -->
<!-- ANIMATED CAPSULE FOOTER                                                        -->
<!-- ============================================================================== -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1,12,24,30&height=120&section=footer" alt="Footer" width="100%" />

<sub>Architected with dedication by <a href="https://github.com/MOHAMMADREZAABEDINPOOR"><b>MOHAMMADREZA ABEDINPOOR</b></a>. If PIMX_PASS_BOT powers your digital freedom, consider leaving a ⭐!</sub>

</div>
