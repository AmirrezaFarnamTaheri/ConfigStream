# کانفیگ‌استریم (ConfigStream) — سامانهٔ جامع پالایش و توزیع پروکسی‌های ضدسانسور

[![Pipeline](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/main.yml)
[![CI](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/ci.yml)
[![Pages Deploy](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/workflows/deploy-pages.yml)

**[English](README.md) • [فارسی](README_FA.md) • [简体中文](README_ZH.md) • [Русский](README_RU.md)**

کانفیگ‌استریم (ConfigStream) یک پلتفرم خودکار، امن و مستقل برای جمع‌آوری، راستی‌آزمایی چندمرحله‌ای، شست‌وشوی زنجیره‌ای و توزیع اشتراک‌های پروکسی در شرایط اختلال شدید شبکه و فیلترینگ است.

---

## 🚀 لینک‌های اشتراک مستقیم (به‌روزرسانی خودکار هر ۱۵ دقیقه)

همهٔ لینک‌ها شامل متادیتای پیشرفتهٔ Hiddify (`#profile-title`، `#profile-update-interval` و غیره) و کدگذاری Base64 استاندارد هستند:

| دسته / پروفایل | فرمت لینک متنی | فرمت Base64 | سازگاری کلاینت |
| :--- | :--- | :--- | :--- |
| **همهٔ کانفیگ‌ها (All)** | [`configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/configs.txt) | [`configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/configs_base64.txt) | همهٔ کلاینت‌ها |
| **تست‌شده و پایدار (Verified)** | [`verified/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/verified/configs.txt) | [`verified/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/verified/configs_base64.txt) | Hiddify, v2rayNG, Streisand |
| **سریع و کم‌تاخیر (Fast)** | [`fast/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/fast/configs.txt) | [`fast/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/fast/configs_base64.txt) | گیمینگ، تماس صوتی |
| **امن و دارای PFS (Secure)** | [`secure/configs.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/secure/configs.txt) | [`secure/configs_base64.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/secure/configs_base64.txt) | Reality, Hysteria2, TUIC |
| **۱۰۰ کانفیگ برتر (Top 100)** | [`top100.txt`](https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/top100.txt) | — | انتخاب سریع |

### اشتراک‌های کلاینت‌های تخصصی (Clash / Sing-box)
- **اشتراک Clash / Mihomo:** `https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/clash.yaml`
- **اشتراک Sing-box (v1.13+):** `https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/output/singbox.json`

---

## 🛡 معماری آبشار راستی‌آزمایی ۴ مرحله‌ای

1. **لایهٔ L0/L1 (پالایش ساختاری و یکتاسازی):**
   - حذف نودهای تکراری بر پایهٔ `(Host, Port, Protocol, UUID)`
   - بررسی اعتبارسنجی UUID استاندارد (۳۶ کاراکتری) و فشرده (۳۲ رقمی هگز) و رشته‌های سفارشی مجاز Xray زیر ۳۰ بایت.
   - فیلتر پورت‌های نامعتبر یا رنج‌های خصوصی شبکه داخلی (جلوگیری از SSRF).
2. **لایهٔ L2 (دست‌دادن TCP و DNS تفکیک‌شده):**
   - حل همروند نام دامنه‌ها از طریق استخر ۶۴ نخی جهت جلوگیری از قفل‌شدگی حلقهٔ asyncio.
   - کاوش هم‌زمان تا ۳ آدرس IP برای هاست‌های چند IP (پوشش ۹۹.۵٪ سرورهای زنده).
   - محدودیت همروندی سخت روی ۸۰۰ سوکت باز جهت عدم بروز خطای `EMFILE (Errno 24)`.
3. **لایهٔ L3 (آزمون واقعی اتصال با هستهٔ محلی):**
   - اندازه‌گیری عبور واقعی ترافیک تا نقاط انتهایی HTTP 204.
   - پالایش نودهای لرزان (Flaky) از طریق میانگین/میانهٔ آزمون‌های چنددوره‌ای.
4. **لایهٔ احیا و شست‌وشو (Washer & Chaining):**
   - احیای کانفیگ‌های فیلترشده با تونل‌های Cloudflare WARP و Masque.

---

## 📱 راهنمای راه‌اندازی در کلاینت‌های محبوب

### ۱. کلاینت Hiddify (اندروید، ویندوز، مک، لینوکس، iOS)
1. لینک اشتراک Base64 یا Singbox را کپی کنید.
2. در نرم‌افزار روی دکمهٔ **+ (افزودن پروفایل)** بزنید.
3. گزینهٔ **افزودن از کلیپ‌بورد (Add from Clipboard)** را انتخاب کنید.

### ۲. کلاینت v2rayNG / Streisand / Shadowrocket
1. لینک اشتراک Base64 را کپی کنید.
2. از منوی تنظیمات اشتراک (Subscription Settings)، نشانی را وارد کرده و دکمهٔ **بروزرسانی اشتراک (Update Subscriptions)** را بزنید.

### ۳. کلاینت Clash Verge Rev / Mihomo Party
1. وارد بخش **Profiles** شوید.
2. نشانی `clash.yaml` را در قسمت URL وارد کرده و دکمهٔ **Import** را بزنید.

---

## 💻 راه‌اندازی محلی و توسعه

```bash
# کلون مخزن
git clone https://github.com/AmirrezaFarnamTaheri/ConfigStream.git
cd ConfigStream

# ایجاد محیط مجازی و نصب وابستگی‌ها
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip install -e . --no-deps

# اجرای پایپ‌لاین آزمایشی
python -m configstream.cli merge --sources sources/batch_1.txt --output output/

# اجرای تست‌های جامع
pytest tests/unit/
```

---

## 📜 پروانه و کپی‌رایت
این پروژه تحت پروانهٔ نرم‌افزار آزاد **AGPL-3.0-or-later** منتشر شده است.
