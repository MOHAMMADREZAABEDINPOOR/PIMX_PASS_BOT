<a id="english-description"></a>
# PIMX_PASS_BOT 🤖
## Telegram Bot for Server Scanning, Testing, and Config Sharing

[![Persian Description](https://img.shields.io/badge/Read-Persian%20Description-0A66C2?style=for-the-badge)](#persian-description)

PIMX_PASS_BOT is an automated, practical, and security-aware Telegram bot for scanning servers/configs, testing them, storing results, and presenting outputs in Telegram plus a lightweight web view.

This project is designed for teams or admins who need to:
- monitor many configs from one place,
- run tests manually or on schedule,
- track test status in real time,
- and share long configs through a web page instead of long Telegram messages.

## ✨ Main Features

### 🔎 Scanning and Testing
- Automatic scan/test workflow (scheduled or triggered).
- Manual test buttons directly inside Telegram.
- Progress updates in real time via message edits.
- Clear pass/fail-style visibility for quick operations.

### 📲 Telegram Workflow
- Paginated server list (easy navigation for long lists).
- Previous/Next controls to move between pages.
- Update/test controls from bot actions.
- Optional requirement to join a channel before using the bot.

### 🗃 Data and Storage
- SQLite-backed storage for server/config and test data.
- Local data model with simple maintenance.
- Pluggable provider structure in code for future extensions.

### 🌐 Lightweight Web View
- Small web page for rendering long configuration content.
- Better UX for copy/share compared to sending full raw text in chat.
- Useful for publishing or reviewing long configs safely.

### ⚙️ Configuration
- Environment-based setup using `.env`.
- Ready `.env.example` for faster onboarding.
- Easy deployment adaptation for local server, VPS, Docker, or process manager.

## 🚀 Quick Start

### 1) Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure `.env`

Start from `.env.example` and set at least:

- `TELEGRAM_TOKEN=your_bot_token_here`
- `DATA_PROVIDER=db`
- `DATABASE_PATH=data/pimx.db`
- `WEB_PORT=8080`
- `PUBLIC_BASE_URL=https://your.domain` (optional, when needed)

### 3) Run the bot

```powershell
python main.py
```

## 🧱 Project Structure

```text
PIMX_PASS_BOT/
|-- main.py
|-- requirements.txt
|-- .env.example
|-- README.md
|-- scripts/
|-- data/
`-- pimx_bot/
    |-- __init__.py
    |-- config.py
    |-- db.py
    |-- parser.py
    |-- providers.py
    |-- scanner.py
    |-- server_tester.py
    |-- telegram_app.py
    |-- web_server.py
    `-- static/
```

## 🧠 Core Modules (High-Level)

- `pimx_bot/telegram_app.py`: bot commands, callbacks, message/update flow.
- `pimx_bot/scanner.py`: scan logic and orchestration.
- `pimx_bot/server_tester.py`: testing logic and result evaluation.
- `pimx_bot/db.py`: SQLite access and persistence layer.
- `pimx_bot/web_server.py`: lightweight web endpoint for config display.
- `pimx_bot/providers.py`: data provider abstraction.

## 🔐 Security Notes

- Never commit real secrets: Telegram token, PAT, API keys, private keys.
- Keep secrets in `.env` only.
- Rotate any leaked key/token immediately.
- Keep runtime/session files out of Git (`*.session`, wal/shm db files, etc.).

## 🛠 Operational Tips

- Use logs to diagnose scan/test errors quickly.
- If Telegram updates are not sent, verify token and network access.
- If data looks stale, check scheduler settings and DB write permissions.
- If web links fail, verify `PUBLIC_BASE_URL` and web port mapping.

## 🧪 Testing and Validation

- Use `run_tests.ps1` and existing test files as baseline checks.
- Validate Telegram callbacks after any UI/callback change.
- Re-check DB schema compatibility when adding new result fields.

## 📦 Deployment Notes

You can run this bot in several ways:
- local development (simple `python main.py`),
- VPS with process manager (recommended for production),
- Docker/systemd setups (team/production style).

For production:
- enable restart policy,
- isolate `.env` permissions,
- monitor logs and DB size growth.

## 🤝 Contributing

Contributions are welcome:
- report bugs via GitHub Issues,
- propose features with clear use case,
- open PRs with focused commits and test notes.

## 👤 Author

Mohammadreza Abedinpour  
GitHub: https://github.com/MOHAMMADREZAABEDINPOOR

---

<a id="persian-description"></a>
## توضیحات فارسی

[![Back to English](https://img.shields.io/badge/Back%20to-English-0B1F3A?style=for-the-badge)](#english-description)

PIMX_PASS_BOT یک ربات تلگرام خودکار، کاربردی و امن برای اسکن سرورها/کانفیگ‌ها، تست آن‌ها، ذخیره نتایج، و نمایش خروجی در تلگرام به‌همراه یک رابط وب سبک است.

این پروژه برای مدیران یا تیم‌هایی مناسب است که نیاز دارند:
- تعداد زیادی کانفیگ را از یک نقطه مدیریت کنند،
- تست‌ها را دستی یا زمان‌بندی‌شده اجرا کنند،
- وضعیت تست را به‌صورت زنده ببینند،
- و کانفیگ‌های طولانی را به‌جای ارسال متن بلند در چت، در وب‌ویو به اشتراک بگذارند.

## ✨ قابلیت‌های اصلی

### 🔎 اسکن و تست
- فرایند اسکن/تست خودکار (زمان‌بندی‌شده یا دستی).
- دکمه‌های اجرای تست مستقیم داخل تلگرام.
- به‌روزرسانی زنده پیشرفت از طریق ویرایش پیام.
- نمایش واضح وضعیت برای تصمیم‌گیری سریع عملیاتی.

### 📲 جریان کاری تلگرام
- لیست صفحه‌بندی‌شده سرورها برای مدیریت ساده لیست‌های بزرگ.
- دکمه‌های قبلی/بعدی برای ناوبری سریع.
- کنترل اجرای تست/آپدیت از طریق اکشن‌های ربات.
- قابلیت الزام عضویت کانال قبل از استفاده از ربات.

### 🗃 داده و ذخیره‌سازی
- استفاده از SQLite برای ذخیره اطلاعات سرور/کانفیگ و نتایج تست.
- ساختار ساده برای نگهداری و پشتیبانی.
- معماری قابل توسعه برای افزودن Providerهای جدید.

### 🌐 رابط وب سبک
- نمایش کانفیگ‌های طولانی در یک صفحه وب سبک.
- تجربه بهتر برای کپی/اشتراک‌گذاری نسبت به پیام‌های متنی طولانی.
- مناسب برای مرور یا انتشار کنترل‌شده کانفیگ‌ها.

### ⚙️ پیکربندی
- تنظیمات مبتنی بر `.env`.
- فایل `.env.example` برای راه‌اندازی سریع.
- مناسب برای اجرا در محیط محلی، VPS، Docker یا process manager.

## 🚀 شروع سریع

### 1) ساخت و فعال‌سازی محیط مجازی

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) پیکربندی `.env`

بر اساس `.env.example` حداقل این مقادیر را تنظیم کنید:

- `TELEGRAM_TOKEN=your_bot_token_here`
- `DATA_PROVIDER=db`
- `DATABASE_PATH=data/pimx.db`
- `WEB_PORT=8080`
- `PUBLIC_BASE_URL=https://your.domain` (در صورت نیاز)

### 3) اجرای ربات

```powershell
python main.py
```

## 🧱 ساختار پروژه

```text
PIMX_PASS_BOT/
|-- main.py
|-- requirements.txt
|-- .env.example
|-- README.md
|-- scripts/
|-- data/
`-- pimx_bot/
    |-- __init__.py
    |-- config.py
    |-- db.py
    |-- parser.py
    |-- providers.py
    |-- scanner.py
    |-- server_tester.py
    |-- telegram_app.py
    |-- web_server.py
    `-- static/
```

## 🧠 ماژول‌های اصلی

- `pimx_bot/telegram_app.py`: مدیریت دستورات، callbackها و به‌روزرسانی پیام‌ها.
- `pimx_bot/scanner.py`: منطق اسکن و ارکستریشن فرایند.
- `pimx_bot/server_tester.py`: منطق تست و تحلیل نتیجه.
- `pimx_bot/db.py`: لایه ارتباط با SQLite و ذخیره‌سازی.
- `pimx_bot/web_server.py`: وب‌سرور سبک برای نمایش کانفیگ‌ها.
- `pimx_bot/providers.py`: لایه انتزاع Provider برای توسعه‌پذیری.

## 🔐 نکات امنیتی

- اطلاعات حساس (توکن تلگرام، PAT، API Key، کلید خصوصی) را هرگز commit نکنید.
- همه Secrets را فقط داخل `.env` نگه دارید.
- در صورت نشت، فوری کلید/توکن را Rotate کنید.
- فایل‌های runtime/session را از Git خارج نگه دارید.

## 🛠 نکات عملیاتی

- برای خطایابی تست/اسکن، لاگ‌ها را خط به خط بررسی کنید.
- اگر پیام‌ها ارسال نمی‌شوند، توکن و دسترسی شبکه را چک کنید.
- اگر داده‌ها به‌روز نیستند، زمان‌بندی و مجوز نوشتن DB را بررسی کنید.
- اگر لینک وب کار نمی‌کند، `PUBLIC_BASE_URL` و تنظیم پورت را چک کنید.

## 🧪 تست و اعتبارسنجی

- از `run_tests.ps1` و تست‌های موجود به‌عنوان baseline استفاده کنید.
- بعد از تغییر callbackها، سناریوهای Telegram UI را تست کنید.
- در تغییرات DB، سازگاری schema با نسخه قبلی را بررسی کنید.

## 📦 استقرار

روش‌های رایج اجرا:
- اجرای محلی با `python main.py`,
- اجرای VPS با process manager,
- استقرار با Docker یا systemd.

برای محیط تولید:
- policy ری‌استارت فعال باشد،
- سطح دسترسی `.env` محدود باشد،
- لاگ و رشد حجم دیتابیس مانیتور شود.
