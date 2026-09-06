<div align="center">

# 🤖🔍 PIMX_PASS_BOT ⚡📊

### Intelligent Server & Proxy Testing Telegram Bot with WebApp Visualization

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg?style=for-the-badge)](https://www.gnu.org/licenses/agpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot_API-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Telegram Mini App](https://img.shields.io/badge/Telegram-Mini_App-0088CC?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org/blog/web-apps)
[![Read in Persian](https://img.shields.io/badge/مطالعه_به_فارسی-Persian_README-008080?style=for-the-badge)](#-توضیحات-فارسی-persian-description)

<p align="center">
  A high-performance automated Telegram bot and WebApp engine for parsing, scanning, benchmarking, and publishing proxy and VPN server configurations. Features latency tracking, ping diagnostics, live Telegram inline pagination, and encrypted sharing.
</p>

[Key Features](#-key-features) •
[Quick Start](#-quick-start) •
[توضیحات فارسی](#-توضیحات-فارسی-persian-description) •
[License](#-license)

</div>

---

## ⚡ Key Features

- 🔎 **Automated Concurrency Testing**: Continuous background health scans for V2Ray, VMess, VLESS, Trojan, and Shadowsocks nodes.
- 📱 **Telegram Mini App (WebApp)**: Beautiful glassmorphic embedded web interface (`webapp.html`) for interactive visual sorting and config copying.
- 📩 **Interactive Paginated Menus**: Clean inline keyboard navigation (10 servers per page), search filtering, and one-tap test triggers.
- 🗄️ **SQLite Persistence Engine**: Persistent storage of historical latency benchmarks, uptime logs, and node status telemetry.
- 🔒 **Channel Membership Verification**: Optional mandatory Telegram channel subscription enforcement before accessing server endpoints.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/MOHAMMADREZAABEDINPOOR/PIMX_PASS_BOT.git
cd PIMX_PASS_BOT

# 2. Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and ADMIN_ID

# 4. Run the bot
python -m pimx_bot.telegram_app
```

---

## 🇮🇷 توضیحات فارسی (Persian Description)

### معرفی ربات PIMX_PASS_BOT
ربات **PIMX_PASS_BOT** یک سیستم خودکار و بسیار هوشمند برای بررسی سلامت، تست سرعت، پینگ و اشتراک‌گذاری کانفیگ‌ها و سرورهای پروکسی در تلگرام است که به همراه یک **مینی‌اپ تلگرام (WebApp)** تعاملی و زیبا طراحی شده است.

### امکانات برجسته:
1. **تست خودکار و لحظه‌ای سرورها:**
   * اسکن دوره‌ای سرورها و سنجش پینگ و تاخیر اتصال بدون نیاز به دخالت کاربر.
   * ثبت تاریخچه نتایج تست در دیتابیس محلی SQLite.
2. **رابط کاربری درون تلگرام و مینی‌اپ:**
   * مرور کانفیگ‌ها با دکمه‌های شیشه‌ای صفحه‌بندی شده (۱۰ سرور در هر صفحه).
   * امکان باز کردن مستقیم سرورها در مینی‌اپ با یک کلیک.
3. **قفل عضویت اجباری در کانال (Force Join):**
   * قابلیت اتصال به کانال تلگرام شما برای افزایش ممبر پیش از دریافت کانفیگ.

---

## 📜 License & Copyright

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

> **Copyright (c) 2026 MOHAMMADREZA ABEDINPOOR.**  
> Public SaaS deployments or bot instances must share their source code under identical AGPL-3.0 terms.

---

<div align="center">
  <sub>Developed with ❤️ by <a href="https://github.com/MOHAMMADREZAABEDINPOOR">MOHAMMADREZA ABEDINPOOR</a>. Star ⭐ this repo!</sub>
</div>
