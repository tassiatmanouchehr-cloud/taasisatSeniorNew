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

## نکته

پوشه‌های زیر نباید داخل پروژه نگهداری شوند:

- `.venv`
- `venv`
- `node_modules`
- `__pycache__`
