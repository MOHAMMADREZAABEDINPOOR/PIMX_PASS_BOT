# PIMX_PASS_BOT — ربات مدیریت و نمایش سرورها (Telegram)

**رباتی برای اسکن، تست و نمایش کانفیگ سرورها در تلگرام — خودکار، ساده و امن**

Live Demo / Web UI: محلی (در صورت راه‌اندازی)

✨ ویژگی‌های اصلی

🔎 اسکن و تست خودکار سرورها
- زمان‌بندی تست‌ها (مثلاً هر ساعت) با پشتیبانی از اجرای موازی
- ثبت نتایج تست در SQLite و نمایش وضعیت تست به‌ صورت به‌هنگام
- گزارش دقیق زمان‌بندی‌شده و لاگ تست‌ها برای دیباگ و پیگیری

📩 تعامل با تلگرام
- نمایش لیست سرورها به‌صورت صفحه‌بندی (۱۰ تا ۱۰ تا)
- دکمه‌های قبلی/بعدی، جستجوی سرور و گزینه به‌روزرسانی/تست دستی
- نمایش وضعیت تست و درصد پیشرفت با ویرایش پیام (message edits)
- الزام عضویت کاربران در کانال برای دسترسی به لیست (کانال-پرانگ)

🗄️ ذخیره‌سازی و پیکربندی
- دیتابیس SQLite برای ذخیره سرورها و نتایج تست (`data/*.db`)
- پیکربندی از طریق فایل `.env` (توکن بات، روش Provider و غیره)
- امکان تنظیم Provider داده (DB یا فایل/سرویس دیگر)

🌐 رابط وب سبک
- صفحه وب ساده برای مشاهده کانفیگ‌ها و تولید لینک قابل‌کپی
- مناسب برای اشتراک‌گذاری کانفیگ‌ها بدون ارسال متن طولانی در چت

🔒 امنیت و نکات عملی
- **توکن‌ها (Bot token, PAT) را هرگز در ریپو نگهداری نکنید.** از `.env` و `.gitignore` استفاده کنید.
- اگر توکن یا اطلاعات حساس به‌طور ناخواسته منتشر شد، فوراً آن را بازنشانی (reset/revoke) کنید.

🚀 راه‌اندازی سریع

1) محیط مجازی و نصب وابستگی‌ها:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2) پیکربندی محیط (`.env`):
- `TELEGRAM_TOKEN=your_bot_token_here`
- `DATA_PROVIDER=db`
- `DATABASE_PATH=data/pimx.db`
- `WEB_PORT=8080`
- `PUBLIC_BASE_URL=https://your.domain` (در صورت نیاز)

3) اجرای برنامه:

```powershell
python main.py
```

یا برای اجرا به‌عنوان سرویس، از سیستم قطعه‌بندی مثل `systemd` یا Docker استفاده کنید.

🧰 فایل‌ها و ساختار پروژه

```
PIMX_PASS_BOT/
├── main.py
├── requirements.txt
├── .env.example
├── README.md
├── scripts/                # اسکریپت‌های کمکی (مثل push_to_github.ps1)
├── data/                   # دیتابیس‌ها و داده‌های محلی
└── pimx_bot/
    ├── config.py
    ├── db.py
    ├── scanner.py
    ├── server_tester.py
    ├── telegram_app.py
    └── web_server.py
```

🛠️ عیوب و رفع اشکال (Troubleshooting)
- موقعیت سرور یافت نشد: بررسی کنید آدرس/پورت صحیح است و فایروال دسترسی را مسدود نکرده باشد.
- تست‌ها اجرا نمی‌شوند: بررسی لاگ‌ها (`.log`) و دیتابیس برای خطاها و پیام‌های استثنایی.
- بات پیام ارسال نمی‌کند: بررسی توکن، اتصال به اینترنت و محدودیت‌های API تلگرام.

🤝 مشارکت (Contributing)
- باگ گزارش دهید یا پیشنهاد ویژگی بدهید (Issues)
- درخواست Pull Request با یک توصیف کامل و تست‌های لازم ارسال کنید

📄 مجوز
- این پروژه تحت **MIT License** منتشر شده است — آزاد برای استفاده و تغییر.

👤 نویسنده
Mohammadreza Abedinpour  — https://github.com/MOHAMMADREZAABEDINPOOR

Last updated: 2025

- Advanced City Search: Autocomplete city search with real-time suggestions
- Multi-City Management: Save up to 20 cities and switch between them seamlessly
- Persistent Storage: Cities and preferences saved in browser localStorage

🌤️ Comprehensive Weather Data
Current Conditions
- Real-time Temperature: Current, feels-like, and daily min/max temperatures
- Detailed Weather Stats (13 stat cards with animated progress bars):
  - 🌡️ Feels Like Temperature
  - 💧 Humidity
  - 💨 Wind Speed & Direction
  - 🔽 Atmospheric Pressure
  - 👁️ Visibility
  - 💦 Dew Point
  - 🌧️ Precipitation
  - ☀️ UV Index
  - 🏭 Air Quality Index (AQI)
  - 🌅 Sunrise Time
  - 🌇 Sunset Time
  - 🌙 Moon Phase

Forecasts
- 24-Hour Hourly Forecast: Detailed hour-by-hour predictions with weather icons
- Extended Daily Forecast: Choose between 7 or 14-day forecasts
- Visual Weather Icons: Beautiful animated icons for all weather conditions
- Dynamic Themes: UI automatically adapts to weather conditions (sunny, cloudy, rainy, snowy, night)

📊 Historical Data & Analytics
Interactive Charts
- Precipitation History:
  - View data for past week, month, 6 months, or year
  - Interactive Chart.js line charts
  - Statistics: Total precipitation, average max/min, max daily precipitation
- Temperature History:
  - Historical temperature trends
  - Visual temperature charts

☀️🌙 Advanced Astronomy Features
Sun Arc Visualization 🎨
- Beautiful Arc Chart: Real-time visualization of sun's path across the sky using Quadratic Bezier Curves
- Time Markers: Visual markers for 9 AM, 12 PM, 3 PM, and 6 PM
- Color Gradient: Smooth gradient from sunrise to sunset
- Glow Effects: Animated glow effects and pulse animations
- Live Position Tracking: Real-time sun position with altitude angle display
- Detailed Sun Information:
  - 🌅 Sunrise Time
  - 🌇 Sunset Time
  - ⏱️ Day Length
  - 🌞 Solar Noon
  - 📐 Sun Altitude
  - 🧭 Sun Azimuth
  - ⬆️ Maximum Altitude
  - 🌍 Distance from Sun

Moon Arc Visualization 🌙
- Moon Path Visualization: Beautiful arc chart showing moon's journey across the sky
- Twinkling Stars: Animated stars in the night sky background
- Night Visual Effects: Atmospheric night-time visuals
- Live Moon Tracking: Real-time moon position display
- Detailed Moon Information:
  - 🌕 Moon Phase (8 phases with graphical display)
  - 💡 Illumination Percentage
  - 📅 Moon Age (days since new moon)
  - 🌜 Moonrise Time
  - 🌛 Moonset Time
  - ⏱️ Duration Above Horizon
  - 📐 Moon Altitude
  - 📏 Distance from Earth

Solar System Visualization 🪐
- Real Astronomical Positions: All 8 planets (Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune) with accurate VSOP87 calculations
- Interactive Time Control:
  - Hour slider (00:00 - 23:00) to observe planetary motion throughout the day
  - "Now" button to jump to current time
  - Real-time position updates
- Zoom Controls: Zoom in/out and reset for better viewing (0.5x to 2.0x)
- Planet Details: Click any planet to see:
  - Distance from Sun (AU)
  - 3D Coordinates (X, Y, Z)
  - Angle and position information
- Visual Features:
  - Saturn's rings
  - Earth's moon
  - Color-coded planet legend
- Accuracy: Positions accurate for any date/time (1800-2200 CE)

🎯 User Experience
Navigation & Controls
- Day Navigation: Click any day in the forecast to see detailed hourly breakdown
- Date Selector: Previous/Next day buttons with live date display
- Live Clock: Real-time local time display for selected city
- Auto-refresh: Weather data updates automatically

Customization
- Multi-language Support:
  - 🇫🇷 Persian (Farsi)
  - 🇬🇧 English
  - Auto-detection based on browser/geolocation
- Temperature Units: Toggle between Celsius (°C) and Fahrenheit (°F)
- Responsive Zoom: Auto-optimized zoom levels for mobile, tablet, and desktop

Visual Design
- Beautiful Animations: Weather-specific animations (sun, clouds, rain, snow, night)
- Loading screen animations
- Smooth transitions and hover effects
- Dynamic Color Themes: UI adapts colors based on weather conditions
- Progress Bar Animations: Animated progress bars for all stat cards
- SVG Graphics: Custom SVG elements for astronomical visualizations

📱 Responsive Design
- Mobile-First: Optimized for all screen sizes
- Breakpoint Support:
  - Mobile (≤560px)
  - Tablet (≤880px)
  - Desktop (>880px)
- Touch-Friendly: Optimized touch targets and gestures
- Adaptive Layouts: Grid and Flexbox layouts that adapt to screen size

🚀 Getting Started
Quick Start
Clone the repository

git clone https://github.com/MOHAMMADREZAABEDINPOOR/PIMX_WEATHER.git
cd PIMX_WEATHER
Open in browser

Simply open index.html in any modern web browser
No build process or dependencies required!
Start using

- Allow location access when prompted (optional)
- Or search for any city worldwide

Browser Requirements
- Modern Browser: Chrome, Firefox, Safari, Edge (latest versions)
- JavaScript: Must be enabled
- Internet Connection: Required for API calls

No Installation Needed!
This is a pure client-side application:

✅ No server required
✅ No build process
✅ No npm/node dependencies (except CDN libraries)
✅ Works offline for saved cities (after initial load)

🌐 Data Sources & APIs
Weather APIs
- Primary: Open-Meteo - Free, accurate, and reliable weather API
- Forecast API: Real-time and future weather data
- Archive API: Historical weather data
- Air Quality API: Air pollution and AQI data
- Geocoding API: City search and reverse geocoding

Location Services
- GPS: Native browser geolocation API
- IP Geolocation: ipapi.co - IP-based location detection

Astronomical Calculations
- VSOP87: Variations Séculaires des Orbites Planétaires - Planetary position calculations
- Kepler's Equation: Solving for planetary orbits
- Julian Day: Astronomical date/time conversion
- Reference Standards:
  - JPL Horizons
  - Astronomical Algorithms by Jean Meeus

## قابلیت‌ها

- دیتابیس SQLite با پسوند `.db`
- اسکن و تست خودکار سرورها هر ۱ ساعت (در حالت `DATA_PROVIDER=db`)
- نمایش وضعیت تست (پیشرفت `tested/1000`) با ادیت کردن پیام
- نمایش لیست سرورها ۱۰ تا ۱۰ تا + دکمه‌های قبلی/بعدی
- الزام عضویت در کانال قبل از نمایش لیست

## راه‌اندازی

1) پکیج‌ها:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2) تنظیمات:

- فایل `.env` بسازید (مثل `.env.example`) و مقادیر را پر کنید.
- برای چک عضویت، بات باید داخل کانال عضو باشد (ترجیحاً ادمین).
- برای «کپی با یک کلیک» روی کانفیگ‌های طولانی، `WEB_PORT` و `PUBLIC_BASE_URL` را تنظیم کنید تا بات به‌جای ارسال کانفیگ در چت، لینک کوتاهِ قابل‌کپی بدهد.

3) اجرا:

```bash
python main.py
```

## نکته امنیتی

توکن بات را داخل ریپو نگه ندارید. اگر قبلاً توکن را جایی منتشر کرده‌اید، از BotFather توکن را ریست کنید.

## بارگذاری به GitHub

> **قبل از ادامه:** اگر توکن (PAT) را افشا کرده‌اید، فوراً آن را در https://github.com/settings/tokens لغو کنید. از ارسال توکن در چت یا تعبیه آن در کد جداً خودداری کنید.

برای ساخت ریپوزیتوری و push امن، دو راه دارید:

1) با GitHub CLI (توصیه‌شده):
   - نصب: https://cli.github.com/
   - ورود تعاملی: `gh auth login`
   - ایجاد و push: `gh repo create PIMX_PASS_BOT --public --source=. --remote=origin --push`
   - یا از اسکریپت `scripts\push_to_github.ps1` استفاده کنید.

2) با وب و HTTPS یا SSH:
   - ریپوزیتوری روی GitHub بسازید و سپس:
     - HTTPS: `git remote add origin https://github.com/<username>/PIMX_PASS_BOT.git` و سپس `git push -u origin main`
     - SSH: `git remote add origin git@github.com:<username>/PIMX_PASS_BOT.git` و سپس `git push -u origin main`

اگر نیاز دارید، من می‌توانم برای حذف توکن از تاریخچه گیت دستورالعمل‌های امن بدم یا اسکریپت آماده کنم.

