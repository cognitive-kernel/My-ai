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

Python شامل حوزه‌هایی از مبانی تا موضوعات پیشرفته مانند syntax و data types، functions و modules، OOP و Data Model، decorators/descriptors/metaclasses، generators/iterators/context managers، typing، async/concurrency، networking، testing/debugging/profiling، packaging، performance، CPython internals، security و real-project debugging است.

SQL Server نیز به‌صورت curriculum جداگانه برای SQL/T-SQL، database design، joins/CTE/window functions، procedures/functions/triggers، transactions/isolation/locking، deadlocks، indexes/statistics، execution plans، query optimization، security، backup/restore، HA/DR، monitoring/performance و internals پوشش داده می‌شود.

در طراحی فعلی، مدل باید بتواند دانش اولیه را از Seed دریافت کند و سپس با منابع معتبر، تمرین، اجرای کد و آزمون آن را تکمیل و verify کند.

### Dynamic learning domains

یادگیری فقط محدود به زبان‌ها و موضوعات از قبل تعریف‌شده نیست.

وقتی کاربر می‌گوید یک زبان یا موضوع جدید یاد گرفته شود:

1. نام موضوع از درخواست استخراج می‌شود.
2. اگر domain از قبل وجود داشته باشد، همان curriculum ادامه پیدا می‌کند.
3. اگر جدید باشد، برای آن یک domain مستقل ساخته و در `learning_domains` ذخیره می‌شود.
4. curriculum جدید از beginner تا expert ساخته می‌شود و تا حد امکان prerequisites، fundamentals، intermediate، advanced، internals، security، testing، debugging، performance، architecture، production و capstone را پوشش می‌دهد.
5. منابع رسمی در کنار curriculum ذخیره می‌شوند.
6. domain جدید بلافاصله در لیست progress قرار می‌گیرد.
7. progress آن مستقل از سایر domainها محاسبه می‌شود.
8. داده‌های قبلی حذف یا reset نمی‌شوند.

فایل‌های اصلی: `my_ai/dynamic_learning.py`، `my_ai/domain_registry.py`، `my_ai/scheduler.py`.

### Weekly knowledge maintenance

بعد از کامل‌شدن یک domain، سیستم برای آن برنامه‌ی بررسی هفتگی ثبت می‌کند.

هر 7 روز domainهای موعدرسیده بررسی می‌شوند، منابع رسمی و در صورت نیاز جست‌وجوی وب خوانده می‌شوند، مدل تغییرات واقعی را تشخیص می‌دهد، مطالب جدید به curriculum اضافه می‌شوند و سپس دوباره وارد چرخه‌ی یادگیری و verification می‌شوند. اگر مطلب جدیدی نباشد، review بعدی 7 روز جلو می‌رود.

### Memory deduplication

حافظه‌ی دانشی اکنون content-addressed شده است تا یک مطلب یکسان چند بار ذخیره نشود.

- محتوای دانش normalize و با SHA-256 شناسه‌گذاری می‌شود.
- اگر همان محتوا قبلاً وجود داشته باشد، رکورد جدید ساخته نمی‌شود.
- اگر رکورد قبلی source نداشته باشد و رکورد جدید source داشته باشد، source به همان رکورد اضافه می‌شود.
- در startup، duplicateهای قدیمی migration و حذف می‌شوند.
- unique index روی `content_hash` از duplicateهای بعدی جلوگیری می‌کند.
- پس از migration، FTS5 rebuild می‌شود تا جست‌وجوی حافظه سازگار بماند.

فایل‌های اصلی: `my_ai/db.py` و `my_ai/memory.py`.

نکته‌ی آینده: semantic similarity برای تشخیص مطالب «مشابه ولی نه کاملاً یکسان» هنوز مرحله‌ی بعدی Universal Learning & Skill Engine است.

### Database learning

SQLite دیتابیس فعلی خود My-AI است و به‌صورت curriculum مستقل در فهرست یادگیری وجود دارد. SQL Server و MySQL نیز curriculum مستقل دارند. هدف این است که دیتابیس‌هایی که پروژه واقعاً از آن‌ها استفاده می‌کند فقط به‌عنوان ابزار استفاده نشوند و خود My-AI مفاهیم طراحی، query، indexing، transactions، reliability و performance آن‌ها را نیز یاد بگیرد.

### Response quality / LLM backend

قواعد پاسخ‌گویی تقویت شده‌اند:

- پاسخ در زبان کاربر تولید می‌شود.
- برای فارسی، grammar، spelling، punctuation، نیم‌فاصله و ساختار طبیعی صریحاً رعایت می‌شوند.
- مدل باید قبل از پاسخ یک مرور داخلی کوتاه برای grammar و factual consistency انجام دهد.
- ادعای تست، منبع، نسخه یا قابلیت بدون evidence ممنوع است.

Backend مدل قابل تنظیم است:

- پیش‌فرض: Ollama محلی.
- اختیاری: OpenAI-compatible Responses API.
- فعال‌سازی با `LLM_PROVIDER=openai`.
- کلید فقط از `OPENAI_API_KEY` خوانده می‌شود و نباید داخل Git ذخیره شود.
- مدل پیش‌فرض این backend: `gpt-5.6-luna` و قابل تغییر با `OPENAI_MODEL`.
- اتصال مستقیم به runtime همین گفت‌وگو وجود ندارد؛ اتصال از طریق API انجام می‌شود.

### Progress

مشکل قبلی این بود که هنگام تغییر موضوع از Python به SQL Server، worker قبلی می‌توانست ادامه پیدا کند و duplicate topicها progress را از سقف curriculum عبور دهند.

اصلاحات:

- progress بر اساس topicهای یکتا و متعلق به همان curriculum است.
- topicهای خارج از curriculum شمرده نمی‌شوند.
- progress هرگز بیشتر از 100% نمی‌شود.
- گام progress دقیقاً 0.5% است.
- تغییر زبان worker قبلی را متوقف و worker زبان جدید را شروع می‌کند.
- domainهای جدید نیز progress مستقل دارند.
- مطالب جدید weekly review پس از verification دوباره در progress همان domain لحاظ می‌شوند.

### Self-update / self-repair

هدف معماری:

1. inspect پروژه
2. تشخیص bug یا update
3. پیشنهاد تغییر
4. تأیید کاربر
5. snapshot
6. worktree ایزوله
7. compile و test
8. فعال‌سازی
9. health check / watchdog
10. rollback در شکست
11. ثبت failure و lesson

## 4. GitHub authentication

مسیرهای OAuth/CLI و token موجود هستند. هدف استفاده از جریان رسمی GitHub و عدم وابستگی اجباری به PAT در UI است. credential واقعی نباید در repo ذخیره شود.

## 5. مستندات کمک

پوشه `docs/help/` شامل راهنماهای chat، learning، coding، security، github، memory، scheduler، voice، api و docker است.

## 6. تغییرات اخیر

- `2bf30f6338ee874b2f182fd82a38b1146284a38f` — Fix learning progress bounds and deduplicate topics
- `c50b78d8200f80ac20d3ac5a3ce2d6767461cfe9` — Add regression tests for learning progress and language switching
- `d5a234e48dc9c5795fff6b0c5264906440842f6c` — Add dynamic learning domains and weekly knowledge review
- `54fa3985830dc00b9dc93efe623c6f585bbf3e71` — Harden scheduler for dynamic domains and review scheduling
- `712ea6d769172e65a37540155e31881e563d49f7` — Add regression tests for dynamic domains and weekly review scheduling
- `90cec7b087ba475fea6b11274af21b8e7627138f` — Document dynamic learning domains and weekly review
- `6fcf5fd5238e7a52f6dd1a772e1ad08356610be4` — Deduplicate knowledge storage and prepare database learning metadata
- `2d6d5ffb301697f7dcc33e722cf8fa3e25a58313` — Use content-addressed memory to prevent duplicate knowledge
- `f3b79a4d620b5891643099ea766952a1f271414e` — Add optional OpenAI-compatible model configuration
- `6dbd3122244b188b7cb286d9ff20fe83bc3a0da7` — Add optional OpenAI Responses API backend
- `c4d34f831369a165c6494a8afc488f5b1a1bd605` — Improve response quality and use configured LLM backend
- `908f6d03fb6540a383d73a15fa24bc794250c67f` — Use configured LLM backend for autonomous learning
- `725d51627e91ee23105588acec533d593256846f` — Add regression tests for memory deduplication
- `90cec7b087ba475fea6b11274af21b8e7627138f` — Document dynamic learning domains and weekly review

## 7. تست و CI

بعد از هر تغییر باید compile و کل test suite اجرا شود و CI بررسی شود. اگر شکست خورد، ابتدا علت اصلاح و دوباره تست می‌شود؛ فقط بعد از موفقیت کامل اعلام pull انجام می‌شود.

برای این مرحله تست‌های regression مربوط به deduplication اضافه شده‌اند. CIهای قبلی dynamic learning موفق بوده‌اند؛ وضعیت CI همین تغییرات باید قبل از اعلام pull بررسی شود.

## 8. کار بعدی پیشنهادی

Universal Learning & Skill Engine:

- Knowledge Seed
- curriculum مستقل
- concept/example/error/pattern storage
- آزمون نظری
- coding task
- debugging task
- sandboxed execution
- regression testing
- skill score مستقل از knowledge coverage
- evidence برای verified skills
- یادگیری مجدد مباحث ضعیف
- version-aware revalidation
- semantic similarity برای duplicateهای غیر دقیق
- provenance چندمنبعی بدون تکرار محتوا
- داشبورد چندبعدی progress

## 9. معیار موفقیت یادگیری

- `knowledge_coverage`
- `concept_score`
- `implementation_score`
- `debugging_score`
- `testing_score`
- `real_project_score`
- `verified`
- `last_verified`
- `evidence`

فرمول مفهومی:

`Study → Practice → Execute → Test → Fail → Analyze → Fix → Retest → Verify`

## 10. نکته برای چت‌های آینده

اگر کاربر در چت جدید گفت «ادامه پروژه My-AI»، ابتدا این فایل و سپس وضعیت واقعی `main` بررسی شود. فرض نشود تغییرات چت‌های قبلی هنوز روی branch وجود دارند.

اگر کاربر درخواست موضوع جدید کرد، آن موضوع domain مستقل با curriculum beginner تا expert، progress مستقل و review هفتگی داشته باشد.

اگر درباره‌ی حافظه یا duplicate سؤال شد، `my_ai/db.py` و `my_ai/memory.py` بررسی شوند.

اگر درباره‌ی کیفیت پاسخ یا مدل سؤال شد، `my_ai/agent.py`، `my_ai/llm.py` و `my_ai/config.py` بررسی شوند.

این سند باید بعد از هر update مهم، bug fix، تغییر معماری، تغییر curriculum، تغییر وضعیت تست‌ها یا تغییر milestone به‌روزرسانی شود.
