# General Software Engineering Agent

## هدف

My-AI باید بتواند یک درخواست نرم‌افزاری را مستقل از واژه‌های ثابت درک کند، درباره فناوری‌های لازم تحقیق کند، از دانش محلی و منابع وب استفاده کند، معماری و برنامه اجرا بسازد، پروژه را مرحله‌به‌مرحله پیاده‌سازی کند، آن را اجرا و اعتبارسنجی کند، خطاها را تحلیل و اصلاح کند و فقط وقتی معیارهای اتمام برآورده شدند نتیجه را کامل اعلام کند.

این معماری محدود به یک زبان، framework یا نوع پروژه نیست. یک بازی کوچک، API، وب‌سایت، برنامه دسکتاپ، ابزار CLI، سرویس backend، پروژه mobile یا artifactهای تخصصی باید از یک چرخه عمومی استفاده کنند و فقط ابزارهای validation متناسب با پروژه تغییر کنند.

## چرخه استاندارد

```text
درخواست کاربر
  ↓
درک معنایی + context
  ↓
استخراج نیازمندی‌ها و معیار موفقیت
  ↓
تحقیق دانش محلی + تحقیق وب
  ↓
تصمیم فنی و معماری
  ↓
برنامه اجرایی قابل پیگیری
  ↓
ساخت skeleton
  ↓
پیاده‌سازی مرحله‌ای
  ↓
Build / Run
  ↓
Unit / Integration / API / E2E / Runtime validation
  ↓
تحلیل خطا
  ├── اطلاعات ناکافی → تحقیق مجدد
  └── خطای پیاده‌سازی → اصلاح
  ↓
بازآزمایی
  ↓
Self-review و بررسی کامل requirements
  ↓
پاک‌سازی artifactهای موقت و dependencyهای غیرضروری
  ↓
Git status / diff / commit
  ↓
گزارش نهایی با شواهد تست
```

## اجزای Agent

### 1. Semantic Understanding

Router باید intent را از معنی درخواست استخراج کند و به عبارت‌هایی مانند «بساز»، «بنویس»، «ایجاد کن» یا معادل انگلیسی آن‌ها وابسته نباشد. پیام فعلی اولویت دارد و تاریخچه فقط برای resolve کردن referenceها و context استفاده می‌شود.

### 2. Requirements Extractor

خروجی باید شامل هدف، ورودی‌ها، خروجی‌ها، محدودیت‌ها، محیط اجرا، فناوری‌های صریح، فناوری‌های قابل انتخاب، مسیر پروژه و معیارهای پذیرش باشد. اگر requirement مبهم ولی قابل تحقیق باشد، Agent ابتدا تحقیق می‌کند؛ اگر واقعاً اطلاعات حیاتی وجود نداشته باشد، فقط همان مورد را از کاربر می‌پرسد.

### 3. Knowledge Retrieval

دانش داخلی curriculum و memory فقط زمانی وارد prompt می‌شود که به مسئله فعلی مرتبط باشد. دانش بازیابی‌شده جایگزین درخواست کاربر نیست.

### 4. Web Research

Agent می‌تواند برای انتخاب فناوری، API، syntax، نسخه‌ها، محدودیت‌های runtime و روش‌های صحیح implementation تحقیق کند. منابع ترجیحی به ترتیب مستندات رسمی، specificationها، repositoryهای اصلی و منابع فنی معتبر هستند. نتایج تحقیق باید با URL و خلاصه قابل ردیابی در project context ذخیره شوند.

### 5. Technical Planner

Planner باید یک plan ساختاریافته بسازد که شامل architecture، technology decisions، file plan، implementation phases، validation strategy، risks و acceptance criteria باشد.

### 6. Implementation Agent

ساخت پروژه باید مرحله‌ای باشد. هر مرحله باید artifact تولید کند و بعد از آن validation انجام شود. تولید یک JSON عظیم بدون validation مرحله‌ای معیار کافی نیست.

### 7. Validation Matrix

- Python: compile, pytest, lint, type checking در صورت وجود ابزار
- Rust: cargo check/test/clippy
- JavaScript/TypeScript: package install، build، test، lint و در پروژه‌های وب browser E2E
- PHP: syntax، test، lint و در صورت وجود framework test suite
- SQL: schema/migration validation و integration tests
- Android/iOS: build و testهای موجود در محیط توسعه
- MQL4/MQL5: compiler/toolchain موجود؛ نبود compiler باید به‌عنوان validation ناقص گزارش شود
- Web: backend/API checks + browser/runtime checks در محیط محلی
- CLI/Desktop: اجرا و سناریوهای functional متناسب با artifact

### 8. Repair Loop

هر failure باید به یک diagnosis تبدیل شود. Agent باید تشخیص دهد خطا از requirements، dependency، environment، implementation یا test است؛ در صورت نیاز دوباره تحقیق کند؛ اصلاح کند؛ و همان validation شکست‌خورده را تکرار کند. تعداد تلاش‌ها محدود و قابل تنظیم است و failure نهایی نباید به‌عنوان success گزارش شود.

### 9. Self-review

قبل از اتمام، Agent باید requirements را با artifact نهایی مقایسه کند، فایل‌های placeholder/TODO غیرضروری، dependencyهای بلااستفاده و artifactهای موقت را بررسی کند و وضعیت واقعی test/build را گزارش کند.

### 10. Git

Git برای workspace تولیدشده بخشی از lifecycle است: status، diff، ثبت تغییرات meaningful و commit نهایی. Agent نباید تاریخچه یا repository اصلی My-AI را بدون مجوز تغییر دهد. عملیات Git روی پروژه تولیدشده محدود به همان workspace است.

## معیار اتمام

وضعیت `completed` فقط وقتی مجاز است که:

1. هدف کاربر resolve شده باشد.
2. plan و acceptance criteria وجود داشته باشد.
3. artifactهای لازم تولید شده باشند.
4. validationهای مرتبط با نوع پروژه موفق شده باشند یا صریحاً به‌عنوان unavailable/blocked گزارش شوند.
5. failure باقی‌مانده وجود نداشته باشد.
6. self-review انجام شده باشد.
7. workspace وضعیت Git مشخصی داشته باشد.

`generated`، `files_created` یا `build_passed` به‌تنهایی به معنی `completed` نیستند.

## سناریوهای پذیرش

این سناریوها باید در محیط محلی نیز قابل اجرای واقعی باشند:

1. درخواست طبیعی برای یک بازی ساده Python و بررسی وجود کد، اجرا و تست.
2. درخواست طبیعی برای یک پروژه PHP و بررسی dependency، syntax، test و run.
3. درخواست طبیعی برای یک وب‌سایت چندبخشی و بررسی build/API/browser در صورت فراهم بودن runtime.
4. درخواست طبیعی برای یک artifact MQL4 و بررسی تشخیص زبان، طراحی، تولید `.mq4` و compilation در صورت تنظیم MetaEditor.
5. ادامه همان پروژه در پیام بعدی با عبارتی متفاوت از triggerهای قبلی.
6. درخواست اصلاح پروژه تولیدشده و بررسی اینکه Agent artifact موجود را تغییر می‌دهد، نه اینکه پروژه جدید و نامرتبط بسازد.

## اصول مهم

- درک معنایی مقدم بر keyword matching است.
- current user request مقدم بر assistant history است.
- دانش و وب برای حل مسئله استفاده می‌شوند، نه برای تغییر هدف کاربر.
- تحقیق و اجرای ابزار باید قابل ردیابی باشند.
- failure باید قابل مشاهده باشد و هرگز به success تبدیل نشود.
- هر پروژه در workspace مستقل خود ساخته می‌شود.
- قابلیت‌های تخصصی موجود باید در همین معماری عمومی ادغام شوند، نه اینکه برای هر زبان یک مسیر شکننده و مستقل ساخته شود.
