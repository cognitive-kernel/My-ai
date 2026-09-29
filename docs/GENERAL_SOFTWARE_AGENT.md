# General Software Engineering Agent

## هدف

My-AI باید یک درخواست نرم‌افزاری را مستقل از واژه‌های ثابت درک کند، درباره فناوری‌ها و محدودیت‌های واقعی تحقیق کند، از دانش محلی و منابع وب استفاده کند، نوع artifact و قابلیت‌های قابل‌اجرا را مشخص کند، معماری و برنامه اجرا بسازد، پروژه را پیاده‌سازی و اعتبارسنجی کند، خطاها را تحلیل و اصلاح کند و فقط وقتی معیارهای اتمام برآورده شدند نتیجه را کامل اعلام کند.

## چرخه استاندارد

```text
درخواست آزاد کاربر
  ↓
Semantic Understanding + Conversation Context
  ↓
Artifact / Capability Identification
  ↓
Requirements + Constraints + Acceptance Criteria
  ↓
Local Knowledge Retrieval + Web Research
  ↓
Platform Capability / Compatibility Check
  ↓
Architecture + Technology Decision
  ↓
Implementation Plan
  ↓
Generate / Modify Project
  ↓
Semantic Artifact Validation
  ↓
Build / Run
  ↓
Tests / Lint / Type / API / Browser / Runtime validation
  ↓
Failure diagnosis
  ├── requirement ambiguity → resolve from context or ask only when essential
  ├── missing knowledge → research again
  ├── platform conflict → redesign valid architecture
  └── implementation failure → repair
  ↓
Re-test
  ↓
Self-review against requirements
  ↓
Cleanup
  ↓
Git status / diff / commit
  ↓
Final evidence-based completion report
```

## Semantic understanding

Router و Planner نباید برای تشخیص عملیات به فهرست trigger word وابسته باشند. عبارت‌های متفاوتی مانند درخواست مستقیم، غیرمستقیم، محاوره‌ای یا ادامه یک کار باید بر اساس معنی یکسان resolve شوند. current user request اولویت دارد و تاریخچه فقط برای resolve کردن reference و حفظ هدف پروژه استفاده می‌شود.

## Artifact و قابلیت

قبل از تولید کد، Planner باید مشخص کند کاربر چه چیزی می‌خواهد بسازد: application، website، API، library، CLI، mobile app، indicator، expert advisor، script یا نوع دیگری از artifact. سپس باید بررسی کند که قابلیت‌های درخواستی واقعاً توسط آن artifact و platform قابل انجام هستند یا نه.

اگر دو requirement با محدودیت platform متعارض باشند، Agent نباید کد جعلی تولید کند یا یک capability را با placeholder شبیه‌سازی کند. باید از تحقیق و documentation برای تعیین محدودیت استفاده کند و نزدیک‌ترین معماری معتبر را انتخاب کند؛ در صورت نیاز artifact را به چند جزء سازگار تقسیم کند.

## تحقیق

تحقیق از دانش داخلی و WebLearner انجام می‌شود. برای مسائل تخصصی، research queries باید API رسمی، محدودیت platform، compatibility، syntax، نسخه و روش validation را پوشش دهند. منابع و خلاصه آن‌ها در project context ثبت می‌شوند تا تصمیم فنی قابل ردیابی باشد.

## Planner

Plan ساختاریافته باید حداقل شامل این موارد باشد:

- goal
- artifact_type
- language/framework
- requirements
- architecture
- phases
- acceptance_criteria
- research_queries
- validation strategy
- constraints
- ambiguities

Planner نباید قبل از تحقیق یک capability نامطمئن را قطعی فرض کند.

## Implementation و validation

Generator باید کل artifact قابل اجرا را تولید کند، نه فقط یک snippet. پس از تولید، یک semantic validation مستقل از compiler بررسی می‌کند که artifact با plan و platform سازگار است و placeholder یا API ناسازگار ندارد. سپس compiler/runtime/test/lint اجرا می‌شوند.

مثال: اگر کاربر artifact نوع custom indicator برای یک platform درخواست کند ولی یک عملیات فقط در expert advisor/script مجاز باشد، Agent نباید صرفاً نام indicator را روی یک EA با API اشتباه بگذارد. باید محدودیت را تشخیص دهد و architecture معتبر ارائه کند.

## Validation matrix

- Python: compile، pytest، lint و type checking در صورت وجود ابزار
- Rust: cargo check/test/clippy
- JavaScript/TypeScript: install، build، test، lint و browser E2E برای وب
- PHP: syntax، test، lint و framework test suite در صورت وجود
- SQL: schema/migration و integration validation
- Android/iOS: build و testهای موجود در محیط توسعه
- MQL4/MQL5: compiler/toolchain واقعی؛ نبود compiler باید blocked/incomplete گزارش شود
- Web: backend/API + browser/runtime validation
- CLI/Desktop: اجرای سناریوهای functional متناسب با artifact

## Repair loop

هر failure باید diagnosis شود و همان validation شکست‌خورده دوباره اجرا شود. در صورت نیاز Agent باید research را تکرار کند. تعداد repairها محدود است، اما پایان repair loop با خطا هرگز success محسوب نمی‌شود.

## Self-review و Git

پیش از completion، requirements، acceptance criteria، placeholderها، dependencyهای غیرضروری، فایل‌های موقت و runtime state بررسی می‌شوند. Git فقط برای workspace پروژه تولیدشده استفاده می‌شود و commit نهایی تنها پس از validation انجام می‌شود.

## معیار اتمام

`completed` فقط وقتی مجاز است که:

1. هدف و artifact موردنظر resolve شده باشد.
2. plan، requirements و acceptance criteria وجود داشته باشد.
3. research موردنیاز انجام شده باشد یا دلیل مستند برای عدم دسترسی وجود داشته باشد.
4. artifactهای لازم تولید شده باشند.
5. semantic validation موفق باشد.
6. build/test/lint/runtime validation متناسب با پروژه موفق باشد یا صریحاً blocked گزارش شود.
7. failure حل‌نشده وجود نداشته باشد.
8. self-review انجام شده باشد.
9. مسیر workspace و وضعیت Git مشخص باشد.

`generated`، `files_created` یا `build_passed` به‌تنهایی به معنی `completed` نیستند.

## سناریوهای پذیرش

1. درخواست آزاد برای یک بازی Python و بررسی ساخت، اجرا و تست.
2. درخواست آزاد برای یک پروژه PHP و بررسی dependency، syntax، test و run.
3. درخواست آزاد برای یک وب‌سایت چندبخشی و بررسی build/API/browser.
4. درخواست آزاد برای یک artifact MQL4 و بررسی تشخیص artifact، تحقیق platform، تولید `.mq4` و compilation واقعی در صورت تنظیم MetaEditor.
5. ادامه همان پروژه با جمله‌ای کاملاً متفاوت از درخواست قبلی.
6. اصلاح پروژه موجود بدون ساختن پروژه نامرتبط جدید.
7. درخواست دارای دو قابلیت متعارض و بررسی اینکه Agent به‌جای تولید کد جعلی، محدودیت را تشخیص داده و معماری معتبر انتخاب می‌کند.
