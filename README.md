# PIMX_PASS_BOT - Server Scanning and Display Bot (Telegram)

[![Persian Description](https://img.shields.io/badge/Read-Persian%20Description-0A66C2?style=for-the-badge)](#persian-description)

An automated, simple, and secure Telegram bot for scanning, testing, and presenting server configurations.

## Key Features

- Automated scanning and testing with scheduled runs.
- Paginated server list in Telegram with Previous/Next navigation.
- Manual update and test actions from bot buttons.
- Live progress and status updates by editing messages.
- Optional channel membership requirement for access control.
- SQLite storage for servers and test results.
- Lightweight web view for showing and sharing long configurations.
- Environment-based configuration via `.env`.

## Quick Start

1. Create and activate virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment in `.env` (based on `.env.example`):

- `TELEGRAM_TOKEN=your_bot_token_here`
- `DATA_PROVIDER=db`
- `DATABASE_PATH=data/pimx.db`
- `WEB_PORT=8080`
- `PUBLIC_BASE_URL=https://your.domain` (optional)

3. Run the app:

```powershell
python main.py
```

## Project Structure

```text
PIMX_PASS_BOT/
|-- main.py
|-- requirements.txt
|-- .env.example
|-- README.md
|-- scripts/
|-- data/
`-- pimx_bot/
    |-- config.py
    |-- db.py
    |-- scanner.py
    |-- server_tester.py
    |-- telegram_app.py
    `-- web_server.py
```

## Security Notes

- Never store secrets (Telegram token, PAT, API keys) in the repository.
- Use `.env` and rotate leaked secrets immediately.

## Author

Mohammadreza Abedinpour  
GitHub: https://github.com/MOHAMMADREZAABEDINPOOR

## Persian Description

PIMX_PASS_BOT یک ربات تلگرام خودکار، ساده و امن برای اسکن، تست و نمایش کانفیگ‌های سرور است.

### ویژگی‌های کلیدی

- اسکن و تست خودکار با اجرای زمان‌بندی‌شده.
- نمایش لیست سرورها به‌صورت صفحه‌بندی‌شده در تلگرام با ناوبری قبلی/بعدی.
- اجرای دستی عملیات به‌روزرسانی و تست از طریق دکمه‌های ربات.
- نمایش زنده پیشرفت و وضعیت با ویرایش پیام‌ها.
- امکان اجباری‌کردن عضویت در کانال برای کنترل دسترسی.
- ذخیره‌سازی سرورها و نتایج تست در SQLite.
- رابط وب سبک برای نمایش و اشتراک‌گذاری کانفیگ‌های طولانی.
- پیکربندی مبتنی بر `.env`.

### شروع سریع

1. ساخت و فعال‌سازی محیط مجازی:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. پیکربندی فایل `.env` (بر اساس `.env.example`):

- `TELEGRAM_TOKEN=your_bot_token_here`
- `DATA_PROVIDER=db`
- `DATABASE_PATH=data/pimx.db`
- `WEB_PORT=8080`
- `PUBLIC_BASE_URL=https://your.domain` (اختیاری)

3. اجرای برنامه:

```powershell
python main.py
```

### ساختار پروژه

```text
PIMX_PASS_BOT/
|-- main.py
|-- requirements.txt
|-- .env.example
|-- README.md
|-- scripts/
|-- data/
`-- pimx_bot/
    |-- config.py
    |-- db.py
    |-- scanner.py
    |-- server_tester.py
    |-- telegram_app.py
    `-- web_server.py
```

### نکات امنیتی

- هیچ‌گاه اطلاعات محرمانه (توکن تلگرام، PAT، کلید API) را داخل ریپو قرار ندهید.
- از `.env` استفاده کنید و در صورت نشت اطلاعات، کلیدها/توکن‌ها را فوری تغییر دهید.
