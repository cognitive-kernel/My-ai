# My-AI — Project Status & Handoff

> این فایل مرجع دائمی وضعیت پروژه است. بعد از هر تغییر مهم باید به‌روزرسانی شود تا در چت جدید یا بعد از پاک‌شدن تاریخچه، وضعیت پروژه قابل بازیابی باشد.

## 1. هدف پروژه

My-AI یک دستیار هوش مصنوعی محلی است که هدف آن داشتن حافظه، دانش قابل توسعه، توانایی یادگیری، کار با کد و دیتابیس، تشخیص و رفع خطا، و در آینده به‌روزرسانی امن خودش با تأیید کاربر است.

اصول کلیدی:

- یادگیری فقط به معنی ذخیره متن نیست؛ باید با تمرین، اجرا، تست و شواهد عملی تأیید شود.
- `knowledge coverage` از `verified skill` جدا است.
- هیچ مهارتی نباید فقط به دلیل مطالعه‌شدن 100% تلقی شود.
- self-update باید snapshot، تست، health check و rollback داشته باشد.
- تغییر زبان یادگیری باید worker قبلی را متوقف کند و progress هر زبان کاملاً مستقل باشد.
- progress از 0 تا 100 و با گام‌های 0.5 درصد نمایش داده می‌شود.

## 2. مخزن

- Repository: `cognitive-kernel/My-ai`
- Branch اصلی: `main`
- Local clone مورد استفاده: `D:\Projects\MY-AI`

## 3. وضعیت فعلی

### Learning / Knowledge

سیستم یادگیری از یک curriculum ساختاریافته استفاده می‌کند و برای Python و SQL Server دانش اولیه/Seed و موضوعات پیشرفته اضافه شده‌اند.

Python شامل حوزه‌هایی از مبانی تا موضوعات پیشرفته مانند:

- syntax و data types
- functions و modules
- OOP و Data Model
- decorators / descriptors / metaclasses
- generators / iterators / context managers
- typing / generics / protocols
- async/await و asyncio
- threading / multiprocessing / concurrency
- networking / subprocess
- testing / debugging / profiling
- packaging / dependencies
- performance / memory
- CPython / bytecode / internals
- security و real-project debugging

SQL Server نیز به‌صورت curriculum جداگانه برای موضوعاتی مانند:

- SQL و T-SQL
- database design
- joins / CTE / window functions
- procedures / functions / triggers
- transactions / isolation / locking
- deadlocks
- indexes / statistics
- execution plans
- query optimization
- security
- backup / restore
- HA / DR
- monitoring / performance
- internals

در طراحی فعلی، مدل باید بتواند دانش اولیه را از Seed دریافت کند و سپس با منابع معتبر، تمرین، اجرای کد و آزمون آن را تکمیل و verify کند.

### Progress

مشکل قبلی این بود که هنگام تغییر موضوع از Python به SQL Server، worker قبلی می‌توانست ادامه پیدا کند و تعداد topicهای تکراری نیز باعث می‌شد progress از سقف curriculum عبور کند؛ نمونه‌هایی مثل `17/16` یا `20/16` و حتی بالاتر از 100% دیده شده بود.

این مشکل اصلاح شده است:

- progress بر اساس topicهای یکتا و متعلق به همان curriculum محاسبه می‌شود.
- topicهای خارج از curriculum در progress حساب نمی‌شوند.
- progress به 100% محدود می‌شود.
- نمایش progress با گام 0.5% است: `0 → 0.5 → 1 → 1.5 → ... → 99.5 → 100`.
- تغییر زبان باید وضعیت learning هر زبان را مستقل نگه دارد.
- داده‌های قبلی نباید reset یا حذف شوند.

### Self-update / self-repair

هدف معماری این بخش:

1. inspect پروژه
2. تشخیص bug یا update
3. پیشنهاد تغییر
4. دریافت تأیید کاربر
5. snapshot نسخه فعلی
6. اجرای تغییر در محیط ایزوله/worktree
7. compile و test
8. فعال‌سازی نسخه جدید
9. health check / watchdog
10. rollback در صورت شکست
11. نگه‌داشتن logs و failure lessons برای یادگیری بعدی

## 4. GitHub authentication

برای ورود GitHub مسیرهای OAuth/CLI و tokenهای موجود در پروژه توسعه داده شده‌اند. هدف اصلی، استفاده از جریان رسمی GitHub تا حد امکان و عدم وابستگی اجباری به PAT در UI است.

جزئیات فعلی را در `my_ai/git_connector.py` و routeهای مربوط به `/git/login` و `/git/login/status` بررسی کن. هیچ credential واقعی نباید در این فایل ثبت شود.

## 5. مستندات کمک

پوشه `docs/help/` برای موضوعات مختلف پروژه ایجاد شده است، از جمله:

- chat
- learning
- coding
- security
- github
- memory
- scheduler
- voice
- api
- docker

## 6. تست و CI

Workflowهای GitHub Actions برای نصب، compile و pytest فعال هستند.

آخرین اصلاحات progress با commit زیر ثبت شده‌اند:

- `2bf30f6338ee874b2f182fd82a38b1146284a38f` — Fix learning progress bounds and deduplicate topics
- `c50b78d8200f80ac20d3ac5a3ce2d6767461cfe9` — Add regression tests for learning progress and language switching

آخرین CIهای بررسی‌شده برای اصلاحات progress موفق بوده‌اند:

- CI: موفق
- tests: موفق
- compileall: موفق
- pytest: موفق

## 7. اصل مهم برای ادامه توسعه

بعد از هر تغییر:

1. کد فعلی را بررسی کن.
2. تغییر را مستقیم در repo اعمال کن.
3. تست مرتبط اضافه/اصلاح کن.
4. compile و کل test suite را اجرا کن.
5. CI را بررسی کن.
6. اگر شکست خورد، بدون منتظر ماندن برای تأیید کاربر علت را اصلاح و دوباره تست کن.
7. فقط بعد از موفقیت کامل، وضعیت این فایل را به‌روزرسانی کن.
8. سپس به کاربر اعلام کن که تغییرات آماده pull هستند.

## 8. کار بعدی پیشنهادی

مرحله مهم بعدی، کامل‌کردن `Universal Learning & Skill Engine` است:

- Knowledge Seed برای زبان‌ها و فناوری‌ها
- curriculum مستقل برای هر domain
- concept/example/error/pattern storage
- آزمون نظری
- coding task
- debugging task
- اجرای sandboxed
- regression testing
- skill score مستقل از knowledge coverage
- evidence برای مهارت‌های verified
- یادگیری مجدد مباحث ضعیف
- version-aware revalidation
- داشبورد دقیق progress برای هر domain

## 9. معیار موفقیت یادگیری

به‌جای یک عدد ساده مثل `Python = 100%`، وضعیت باید چندبعدی باشد:

- `knowledge_coverage`
- `concept_score`
- `implementation_score`
- `debugging_score`
- `testing_score`
- `real_project_score`
- `verified`
- `last_verified`
- `evidence`

فرمول مفهومی پروژه:

`Study → Practice → Execute → Test → Fail → Analyze → Fix → Retest → Verify`

## 10. نکته برای چت‌های آینده

اگر کاربر در چت جدید گفت «ادامه پروژه My-AI» یا مشابه آن، ابتدا این فایل را به‌عنوان وضعیت مرجع بخوان و سپس وضعیت واقعی `main` را با repo مقایسه کن. فرض نکن تغییرات ادعاشده در چت‌های قبلی هنوز روی branch فعلی وجود دارند؛ commitها و فایل‌های فعلی را بررسی کن.

این سند باید بعد از هر update مهم، bug fix، تغییر معماری، تغییر curriculum، تغییر وضعیت تست‌ها یا تغییر milestone به‌روزرسانی شود.
