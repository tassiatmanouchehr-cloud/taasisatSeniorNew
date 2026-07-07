# اجرای پروژه بدون venv داخل پروژه

این نسخه طوری اصلاح شده که فایل `.env` به صورت خودکار خوانده شود و نیاز نباشد هر بار متغیرهای دیتابیس را دستی در PowerShell ست کنید.

## پیش‌نیازها

روی سیستم باید این‌ها نصب باشند:

- Python 3.12
- PostgreSQL 16 با پورت `5433`
- Node.js / npm فقط برای build کردن CSS

## 1) نصب پکیج‌های Python در محیط اصلی سیستم

اگر نمی‌خواهید داخل پروژه `.venv` داشته باشید، این دستور را در مسیر `src` اجرا کنید:

```powershell
python -m pip install -r requirements\base.txt
```

## 2) تنظیم دیتابیس

فایل `.env` باید این مقادیر را داشته باشد:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5433
DATABASE_NAME=marketplace
DATABASE_USER=marketplace
DATABASE_PASSWORD=marketplace
GIS_ENABLED=false
```

**نکته مهم:** نصب PostgreSQL این role/database را خودش نمی‌سازد — باید دستی
بسازید (یک‌بار، با کاربر `postgres`):

```powershell
psql -U postgres -p 5433 -c "CREATE ROLE marketplace LOGIN PASSWORD 'marketplace' CREATEDB;"
psql -U postgres -p 5433 -c "CREATE DATABASE marketplace OWNER marketplace;"
```

`CREATEDB` روی role لازم است چون `python manage.py test` یک دیتابیس تست
جداگانه (پیش‌فرض: `test_marketplace`) خودش می‌سازد و پاک می‌کند.

اگر `python manage.py migrate` با خطای زیر متوقف شد:

```text
password authentication failed for user "marketplace"
```

یعنی یکی از این دو مورد است:
1. دستورات بالا هنوز اجرا نشده‌اند (role وجود ندارد).
2. یک متغیر محیطی قدیمی روی سیستم (مثلاً از `setx DATABASE_PASSWORD ...` در
   یک پروژه/جلسه قبلی) مقدار فایل `.env` را override کرده — چون مقادیر
   `.env` فقط زمانی اعمال می‌شوند که آن متغیر از قبل در محیط ست نشده باشد.
   با این دستور بررسی کنید و در صورت وجود حذفش کنید:
   ```powershell
   Get-ChildItem Env:DATABASE_*
   [Environment]::SetEnvironmentVariable("DATABASE_PASSWORD", $null, "User")
   ```

## 3) ساخت CSS

```powershell
npm install
npm run build
```

## 4) اجرای Migration

```powershell
python manage.py migrate
```

## 5) اجرای سایت

```powershell
python manage.py runserver
```

بعد در مرورگر باز کنید:

```text
http://127.0.0.1:8000/ui/
```

## 6) اجرای تست‌ها

`python manage.py <command>` مقدار `DJANGO_SETTINGS_MODULE` را همیشه، حتی
قبل از خواندن فایل `.env`، به `config.settings.development` ست می‌کند
(داخل خود `manage.py`). یعنی فایل `.env` نمی‌تواند این مقدار را برای تست‌ها
عوض کند — باید صریحاً در همان دستور ست شود:

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.testing"
python manage.py test
```

اگر این مرحله رد شود و تست‌ها با خطای زیر متوقف شوند:

```text
KeyError: 'MIRROR'
```

مطمئن شوید از نسخه به‌روز `config/settings/testing.py` استفاده می‌کنید —
نسخه‌های قدیمی‌تر دیکشنری `DATABASES["default"]["TEST"]` را کامل جایگزین
می‌کردند به‌جای merge کردن، که می‌توانست کلیدهای پیش‌فرض جنگو (از جمله
`MIRROR`) را حذف کند.

## نکته

پوشه‌های زیر نباید داخل پروژه نگهداری شوند:

- `.venv`
- `venv`
- `node_modules`
- `__pycache__`
