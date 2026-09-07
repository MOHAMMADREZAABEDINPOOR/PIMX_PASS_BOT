<div align="center">

# 🤖 PIMX_PASS_BOT ⚡🛡️
### Production-Grade Telegram Bot & Embedded WebApp for VPN & Proxy Infrastructure Management

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg?style=for-the-badge)](https://www.gnu.org/licenses/agpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram_Bot_API-v20+-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Read in Persian](https://img.shields.io/badge/مطالعه_به_فارسی-Persian_README-008080?style=for-the-badge)](#-توضیحات-کامل-فارسی-persian-documentation)

<p align="center">
  An enterprise-grade Telegram bot engineered for high-concurrency proxy validation, automated protocol benchmarking (VLESS, VMess, Trojan, ShadowSocks), user subscription distribution, and real-time server cluster monitoring with an embedded Telegram Mini App (TMA).
</p>

[Features](#-key-features) •
[Architecture](#-bot-architecture) •
[Quick Start](#-installation--deployment) •
[توضیحات فارسی](#-توضیحات-کامل-فارسی-persian-documentation) •
[License](#-license)

</div>

---

## ⚡ Key Features

- 🔍 **Automated Proxy Configuration Auditing**:
  - Validates syntax, encryption cyphers, and TLS parameters for VLESS, VMess, Trojan, and WireGuard.
  - Detects expired subscriptions and broken connection links.
- 📱 **Telegram Mini App (TMA) Integration**:
  - Interactive web interface inside Telegram allowing users to browse server locations, copy configurations, and view connection speeds without leaving the app.
- ⚡ **Asynchronous Concurrency (Python 3.10+ & Asyncio)**:
  - Capable of serving hundreds of simultaneous user queries with AIORateLimiter to avoid Telegram FloodWait exceptions.
- 🗄️ **Multi-Tier Persistence**:
  - Lightweight SQLite database handling user permissions, quota allotments, access keys, and diagnostic history.
- 🌐 **Native Bilingual Interface (EN / FA)**:
  - Instant toggle between English and Persian inline keyboard menus with intuitive UX.

---

## 🏗️ Bot Architecture

```
[ User Telegram Client ] 
          │ (Commands & Mini App Touch)
          ▼
┌──────────────────────────────────────────────┐
│        python-telegram-bot (Async)           │
│  - AIORateLimiter & Request Dispatcher       │
│  - Conversation Handlers & Callback Routing  │
└──────────────────────┬───────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐       ┌──────────────────┐
│  SQLite3 Engine  │       │ Diagnostic Hub   │
│  - User Auth     │       │ - Ping & TCP SYN │
│  - Subscription  │       │ - GeoIP Resolver │
└──────────────────┘       └──────────────────┘
```

---

## 🚀 Installation & Deployment

### 1. Requirements
- Python 3.10 or higher
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 2. Setup
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

### 3. Environment Variables
Create `.env` in the project root:
```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_ID=your_telegram_numeric_id
DATABASE_PATH=bot.db
ENABLE_WEBAPP=true
```

### 4. Run the Bot
```bash
python bot.py
```

---

## 🇮🇷 توضیحات کامل فارسی (Persian Documentation)

### معرفی ربات PIMX_PASS_BOT
ربات **PIMX_PASS_BOT** یک سیستم جامع، قدرتمند و فوق‌العاده سریع در تلگرام برای مدیریت، اسکن و تست سلامت سرورها و کانفیگ‌های پروکسی است. این ربات با بهره‌گیری از مینی‌اپلیکیشن داخلی تلگرام (Telegram Mini App) به کاربران اجازه می‌دهد تا بدون نیاز به خروج از تلگرام، سرعت سرورها را بسنجند، کانفیگ‌های سالم را دریافت کرده و وضعیت حساب کاربری خود را بررسی نمایند.

### امکانات شاخص:
1. **اسکن و تست سلامت کانفیگ‌ها:**
   * بررسی ساختار فنی، پینگ، ارتباط TCP و اعتبار کدهای VLESS، Trojan، Shadowsocks و WireGuard.
2. **رابط کاربری وب‌اپ تلگرام (Mini App):**
   * محیط گرافیکی تعاملی، مدرن و با طراحی Glassmorphism داخل محیط چت تلگرام.
3. **معماری ناهمگام (Asyncio):**
   * مدیریت همزمان درخواست‌های صدها کاربر با سیستم هوشمند Rate-Limiting جهت جلوگیری از بلاک شدن توکن ربات.
4. **پایگاه‌داده بهینه SQLite:**
   * ذخیره سریع اطلاعات کاربران، گزارش خرابی‌ها و سطوح دسترسی مدیران.
5. **پشتیبانی دو زبانه کامل (فارسی و انگلیسی):**
   * منوها و دکمه‌های شیشه‌ای شیک به همراه متون راهنمای شفاف به زبان فارسی.

---

## 📜 License

Distributed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

---

<div align="center">
  <sub>Engineered by <a href="https://github.com/MOHAMMADREZAABEDINPOOR">MOHAMMADREZA ABEDINPOOR</a>. Don't forget to star ⭐ this project!</sub>
</div>
