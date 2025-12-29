# PIMX Telegram Bot (Python)

**ربات تلگرام برای اسکن، تست و نمایش کانفیگ‌های سرور — ساده، امن و قابل توسعه.**

این پروژه یک بات تلگرام است که منطق پروژه‌ی `PIMX_PERSONAL` را برای نمایش سرورها داخل تلگرام پیاده‌سازی می‌کند.

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

