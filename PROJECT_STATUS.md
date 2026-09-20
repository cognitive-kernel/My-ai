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

### Dynamic learning domains

از این نسخه، learning فقط محدود به زبان‌ها و موضوعات از قبل تعریف‌شده نیست.

وقتی کاربر می‌گوید یک زبان یا موضوع جدید یاد گرفته شود:

1. نام موضوع از درخواست استخراج می‌شود.
2. اگر domain از قبل وجود داشته باشد، همان curriculum ادامه پیدا می‌کند.
3. اگر جدید باشد، برای آن یک domain مستقل ساخته و در `learning_domains` ذخیره می‌شود.
4. curriculum جدید از سطح beginner تا expert ساخته می‌شود و تا حد امکان شامل prerequisites، fundamentals، intermediate، advanced، internals، security، testing، debugging، performance، architecture، production و capstone است.
5. منابع رسمی در کنار curriculum ذخیره می‌شوند.
6. domain جدید بلافاصله در لیست progress قرار می‌گیرد.
7. progress آن مستقل از Python، SQL Server و سایر domainها محاسبه می‌شود.
8. curriculum جدید بدون حذف یا reset کردن داده‌های قبلی اضافه می‌شود.

فایل‌های اصلی:

- `my_ai/dynamic_learning.py`
- `my_ai/domain_registry.py`
- `my_ai/scheduler.py`

### Weekly knowledge maintenance

بعد از کامل‌شدن یک domain، سیستم برای آن برنامه‌ی بررسی هفتگی ثبت می‌کند.

هر 7 روز:

1. domainهای موعدرسیده پیدا می‌شوند.
2. فقط domainهایی که curriculum فعلی‌شان کامل شده بررسی می‌شوند.
3. منابع رسمی ذخیره‌شده و در صورت نیاز جست‌وجوی وب بررسی می‌شوند.
4. مدل تشخیص می‌دهد آیا واقعاً مطلب یا تغییر جدیدی وجود دارد.
5. فقط مطالب جدید و غیرتکراری به curriculum اضافه می‌شوند.
6. موارد جدید دوباره وارد صف یادگیری و progress همان domain می‌شوند.
7. اگر چیز جدیدی وجود نداشته باشد، زمان بررسی بعدی 7 روز جلو می‌رود.

این بررسی به معنی ادعای خودکارِ «یادگیری کامل» نیست؛ مطالب جدید باید همان مسیر مطالعه، تمرین و verification را طی کنند.

زمان‌بندی با UTC/زمان‌های timezone-aware انجام می‌شود تا محاسبات هفتگی پایدار باشند؛ مستندات رسمی Python نیز استفاده از datetimeهای aware را برای نمایش یک لحظه مشخص توصیه می‌کند. citeturn0search0

### Progress

مشکل قبلی این بود که هنگام تغییر موضوع از Python به SQL Server، worker قبلی می‌توانست ادامه پیدا کند و تعداد topicهای تکراری نیز باعث می‌شد progress از سقف curriculum عبور کند؛ نمونه‌هایی مثل `17/16` یا `20/16` و حتی بالاتر از 100% دیده شده بود.

این مشکل اصلاح شده است:

- progress بر اساس topicهای یکتا و متعلق به همان curriculum محاسبه می‌شود.
- topicهای خارج از curriculum در progress حساب نمی‌شوند.
- progress به 100% محدود می‌شود.
- نمایش progress با گام 0.5% است: `0 → 0.5 → 1 → 1.5 → ... → 99.5 → 100`.
- تغییر زبان باید وضعیت learning هر زبان را مستقل نگه دارد.
- داده‌های قبلی نباید reset یا حذف شوند.
- domainهای جدید نیز به همین سیستم progress اضافه می‌شوند.
- بعد از اضافه‌شدن موضوعات جدید در بررسی هفتگی، progress همان domain دوباره بر اساس curriculum واقعی محاسبه می‌شود و هرگز از 100% عبور نمی‌کند.

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
- `d5a234e48dc9c5795fff6b0c5264906440842f6c` — Add dynamic learning domains and weekly knowledge review
- `54fa3985830dc00b9dc93efe623c6f585bbf3e71` — Harden scheduler for dynamic domains and review scheduling
- `712ea6d769172e65a37540155e31881e563d49f7` — Add regression tests for dynamic domains and weekly review scheduling

آخرین CI بررسی‌شده برای نسخه فعلی:

- tests workflow: موفق
- CI workflow: موفق
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
- اتصال نتایج بررسی هفتگی به صف یادگیری و verification

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

اگر کاربر گفت «این زبان/موضوع را یاد بگیر»، آن را به‌عنوان یک learning domain مستقل در نظر بگیر؛ اگر domain جدید است آن را به curriculum و progress اضافه کن، نه اینکه progress زبان دیگری را تغییر بدهی.

این سند باید بعد از هر update مهم، bug fix، تغییر معماری، تغییر curriculum، تغییر وضعیت تست‌ها یا تغییر milestone به‌روزرسانی شود.
