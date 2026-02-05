# 🔒 Cloudflare DoH Proxy

یک DoH (DNS over HTTPS) Proxy قدرتمند و امن با استفاده از Cloudflare Workers - کاملاً رایگان!

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-orange.svg)](https://workers.cloudflare.com/)
[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-green.svg)](https://pages.github.com/)

## 📖 توضیحات

این پروژه یک DoH Proxy حرفه‌ای است که با استفاده از Cloudflare Workers ساخته شده و امکان رمزنگاری کامل DNS queries شما را فراهم می‌کند. این سرویس از 4 سرور DNS معتبر استفاده می‌کند و در صورت عدم دسترسی به یکی، به صورت خودکار به سرور بعدی متصل می‌شود.

## ✨ ویژگی‌ها

- 🔐 **رمزنگاری کامل DNS**: تمام درخواست‌های DNS شما رمزنگاری می‌شود
- ⚡ **Fallback خودکار**: استفاده از 4 سرور DNS با قابلیت جایگزینی خودکار
- 🛡️ **امنیت بالا**: 
  - Rate Limiting (100 درخواست در دقیقه)
  - Input Validation
  - Security Headers
  - Request Timeout (10 ثانیه)
- **کاملاً رایگان**: تا 100,000 درخواست در روز
- **سریع**: استفاده از شبکه جهانی Cloudflare CDN
- **سازگار با همه دستگاه‌ها**: مرورگرها، موبایل، ویندوز، مک
- **مناسب ایران**: برای رمزنگاری DNS و افزایش امنیت

## 🚀 نصب سریع

### مرحله 1: ایجاد Cloudflare Worker

1. به [dash.cloudflare.com](https://dash.cloudflare.com) بروید و وارد شوید
2. از منوی سمت چپ **Workers & Pages** را انتخاب کنید
3. روی **Create Application** کلیک کنید
4. **Create Worker** را انتخاب کنید
5. یک نام برای Worker انتخاب کنید (مثلاً `my-doh-proxy`)
6. روی **Deploy** کلیک کنید

### مرحله 2: کپی کردن کد

1. روی **Edit Code** کلیک کنید
2. تمام کد پیش‌فرض را پاک کنید
3. محتوای فایل [`worker.js`](manual-worker/worker.js) را کپی کرده و جایگذاری کنید
4. روی **Save and Deploy** کلیک کنید

### مرحله 3: دریافت URL

بعد از Deploy، URL شما به این شکل خواهد بود:

```
https://your-worker-name.your-subdomain.workers.dev/dns-query
```

این URL را در مرورگر یا دستگاه خود به عنوان DoH استفاده کنید.

### گزینه جایگزین: استفاده از Cloudflare Pages

علاوه بر Cloudflare Workers، این پروژه از Cloudflare Pages نیز پشتیبانی می‌کند. می‌توانید ریپازیتوری GitHub را مستقیماً به Cloudflare Pages متصل کنید و DoH Proxy خود را بسازید.

1. به [dash.cloudflare.com](https://dash.cloudflare.com) بروید و وارد شوید
2. از منوی سمت چپ **Workers & Pages** را انتخاب کنید
3. روی **Create Application** کلیک کنید و گزینه **Pages** را انتخاب کنید
4. روی **Connect to Git** کلیک کنید و ریپازیتوری [cloudflare-doh-proxy](https://github.com/4n0nymou3/cloudflare-doh-proxy) را انتخاب کنید
5. در بخش Build settings، Framework را None انتخاب کنید
6. روی **Save and Deploy** کلیک کنید

بعد از Deploy، URL شما به شکل `https://your-page.pages.dev/dns-query` خواهد بود.

## 📱 نحوه استفاده

### مرورگر Firefox

```
Settings → Privacy & Security → DNS over HTTPS
→ Choose provider: Custom
→ URL: https://your-worker.workers.dev/dns-query
```

### مرورگر Chrome/Edge/Brave

```
Settings → Privacy and security → Security
→ Use secure DNS → Custom
→ URL: https://your-worker.workers.dev/dns-query
```

### اپلیکیشن Intra (اندروید)

1. [Intra](https://play.google.com/store/apps/details?id=app.intra) را از Google Play نصب کنید
2. اپلیکیشن را باز کنید
3. روی **Configure custom server URL** بزنید
4. URL خود را وارد کنید
5. دکمه **ON** را فعال کنید

### iOS, iPadOS و macOS

برای دستگاه‌های اپل، Worker به صورت خودکار پروفایل DoH شخصی شما را می‌سازد:

1. به آدرس Worker خود بروید (بدون `/dns-query`)
2. روی دکمه **🍎 دانلود پروفایل iOS/macOS** کلیک کنید
3. فایل `.mobileconfig` دانلود می‌شود

**نصب در iOS/iPadOS:**
- فایل را با Safari باز کنید
- Settings → General → VPN, DNS & Device Management
- Downloaded Profile → Install

**نصب در macOS:**
- System Settings → Privacy & Security → Profiles
- نصب پروفایل دانلود شده

### کلاینت‌های Xray (v2rayNG و مشابه)

برای استفاده در کلاینت‌هایی با هسته Xray:

1. فایل کانفیگ [`xray-doh-proxy-client-config.jsonc`](https://raw.githubusercontent.com/4n0nymou3/cloudflare-doh-proxy/refs/heads/main/xray-doh-proxy-client-config.jsonc) را دانلود کنید
2. در قسمت مشخص شده URL DoH Proxy خود را قرار دهید
3. کانفیگ را در v2rayNG یا کلاینت مورد نظر import کنید
4. به DoH Proxy شخصی خود متصل شوید

**نکته:** این روش یک اتصال مستقیم با DNS امن ایجاد می‌کند (بدون رمزنگاری ترافیک).

### ویندوز 11

```
Settings → Network & Internet → Properties
→ DNS server assignment → Edit
→ Preferred DNS encryption: Encrypted only (DNS over HTTPS)
→ URL: https://your-worker.workers.dev/dns-query
```

## 🌐 سرورهای DNS استفاده شده

این DoH Proxy از 4 سرور DNS معتبر استفاده می‌کند:

1. **Cloudflare DNS** (1.1.1.1)
2. **Google DNS** (8.8.8.8)
3. **Quad9 DNS** (9.9.9.9)
4. **OpenDNS**

اگر یک سرور در دسترس نباشد، به صورت خودکار به سرور بعدی متصل می‌شود.

## ⚙️ تنظیمات پیشرفته

### تغییر Upstream DNS

می‌توانید لیست سرورهای DNS را در فایل `worker.js` تغییر دهید:

```javascript
const UPSTREAM_DNS_PROVIDERS = [
  'https://cloudflare-dns.com/dns-query',
  'https://dns.google/dns-query',
  'https://dns.quad9.net/dns-query',
  'https://doh.opendns.com/dns-query'
];
```

### تغییر Rate Limit

```javascript
const RATE_LIMIT_REQUESTS = 100;
const RATE_LIMIT_WINDOW = 60000;
```

### تغییر Cache TTL

```javascript
const DNS_CACHE_TTL = 300;
```

## 🧪 تست کردن

برای تست Worker خود:

### روش 1: مرورگر

به آدرس اصلی Worker بروید (بدون `/dns-query`):

```
https://your-worker.workers.dev
```

اگر صفحه با وضعیت "فعال و آماده به کار" نمایش داده شد، همه چیز درست کار می‌کند.

### روش 2: cURL

```bash
curl -H 'accept: application/dns-json' \
  'https://your-worker.workers.dev/dns-query?name=google.com&type=A'
```

## 📊 محدودیت‌ها

### Cloudflare Workers Free Plan:

- ✅ 100,000 درخواست در روز
- ✅ 10ms CPU time per request
- ✅ بدون محدودیت bandwidth

این مقادیر برای استفاده شخصی کاملاً کافی است!

## ⚠️ نکات مهم

- این سرویس **فقط DNS queries** را رمزنگاری می‌کند
- برای دسترسی به سایت‌های فیلتر شده، از **VPN** استفاده کنید
- این سرویس جایگزین VPN نیست
- برای امنیت بیشتر، از HTTPS برای تمام سایت‌ها استفاده کنید
- کانفیگ Xray فقط DNS را امن می‌کند و ترافیک را رمزنگاری نمی‌کند

## 📝 مجوز

این پروژه تحت مجوز MIT منتشر شده است. برای اطلاعات بیشتر فایل [LICENSE](LICENSE) را مشاهده کنید.

## 🔗 لینک‌های مفید

- [مستندات Cloudflare Workers](https://developers.cloudflare.com/workers/)
- [RFC 8484 - DNS over HTTPS](https://datatracker.ietf.org/doc/html/rfc8484)
- [Cloudflare DNS](https://1.1.1.1/)
- [اپلیکیشن Intra](https://getintra.org/)
- [کانفیگ Xray](https://raw.githubusercontent.com/4n0nymou3/cloudflare-doh-proxy/refs/heads/main/xray-doh-proxy-client-config.jsonc)

## 👨‍💻 سازنده

طراحی و توسعه توسط: [Anonymous](https://t.me/BXAMbot)

---

⭐ اگر این پروژه برای شما مفید بود، یک ستاره به آن بدهید!

🔒 برای اینترنت آزاد و امن
