هدف

ثبت تمام نیازهای غیرعملکردی (Non-Functional Requirements) که کیفیت سیستم را تعیین می‌کنند اما مستقیماً قابلیت جدیدی اضافه نمی‌کنند.

1. Performance
NFR-001

ایجاد پرونده خدمت نباید بیش از ۳ ثانیه زمان ببرد.

NFR-002

نمایش داشبورد Customer باید کمتر از ۲ ثانیه انجام شود.

NFR-003

ثبت رویداد (Event) نباید مانع ادامه عملیات شود.

ثبت Event باید تا حد امکان Asynchronous باشد.

2. Availability
NFR-004

سامانه باید حداقل 99.9% در دسترس باشد.

NFR-005

خرابی سرویس Notification نباید باعث توقف Service Case شود.

3. Scalability
NFR-006

معماری باید امکان پشتیبانی از:

هزاران Organization
صدها هزار Customer
میلیون‌ها Service Session

را بدون تغییر اساسی فراهم کند.

4. Reliability
NFR-007

هیچ Event نباید از بین برود.

NFR-008

ثبت Timeline باید Atomic باشد.

5. Configurability
NFR-009

تمام زمان‌ها باید توسط Platform Owner قابل تنظیم باشند.

مثلاً:

زمان لغو
زمان Reminder
فاصله ساخت Sessionها
6. Maintainability
NFR-010

هیچ Rule مهمی نباید Hard-Code باشد.

7. Extensibility
NFR-011

اضافه شدن کانال جدید Notification نباید باعث تغییر منطق Event Engine شود.

8. Auditability
NFR-012

تمام عملیات مهم باید قابل Audit باشند.