# Future Architecture & Capability Roadmap

این سند فهرست پیشنهادهای توسعه‌ای است که برای مراحل بعدی My-AI نگه داشته می‌شوند. این موارد فعلاً به‌عنوان roadmap و design backlog ثبت شده‌اند و اجرای آن‌ها باید مرحله‌به‌مرحله و همراه با تست و ارزیابی انجام شود.

## 1. Model Router

یک لایه هوشمند برای انتخاب مدل مناسب بر اساس نوع کار، پیچیدگی، زبان، نیاز به reasoning، latency و منابع سخت‌افزاری.

### اهداف
- انتخاب بین مدل‌های local و online
- انتخاب مدل سبک برای کارهای ساده و مدل قوی‌تر برای کارهای پیچیده
- امکان fallback در صورت failure
- ثبت دلیل انتخاب مدل برای audit و evaluation
- جلوگیری از مصرف غیرضروری RAM/VRAM/CPU

## 2. Context Budget Manager

مدیریت هوشمند context به‌جای قرار دادن تمام تاریخچه و knowledge در prompt.

### اهداف
- محاسبه budget توکن بر اساس مدل
- اولویت‌بندی current request، conversation state، relevant knowledge و evidence
- حذف اطلاعات کم‌ارتباط
- خلاصه‌سازی تاریخچه قدیمی
- جلوگیری از context overflow
- اندازه‌گیری کیفیت retrieval قبل و بعد از فشرده‌سازی

## 3. Knowledge Versioning

برای knowledge، research result، تصمیم‌های فنی و اسناد داخلی versioning ایجاد شود.

### اهداف
- نگهداری نسخه‌های قبلی
- ثبت زمان و منبع تغییر
- امکان rollback
- تشخیص knowledge قدیمی
- جلوگیری از جایگزینی بی‌ردپای اطلاعات

## 4. Conflict Resolution

یک لایه رسمی برای تشخیص و مدیریت evidence یا knowledge متعارض.

### اهداف
- تشخیص conflict بین منابع
- مقایسه provenance، freshness و confidence
- نگهداری هر دو evidence به‌جای حذف کورکورانه
- تولید resolution قابل توضیح
- جلوگیری از تبدیل یک منبع متناقض به حقیقت قطعی

## 5. Evidence Graph

ایجاد گراف ارتباط بین requirement، research، source، claim، decision، artifact و validation result.

### اهداف
- traceability کامل از درخواست تا نتیجه
- مشخص بودن اینکه هر تصمیم بر اساس چه evidenceای گرفته شده
- نمایش dependency بین claimها و منابع
- کمک به self-review و debugging
- پشتیبانی از گزارش completion مبتنی بر evidence

## 6. Automatic Regression Knowledge Tests

برای knowledge و retrieval نیز مانند کد، regression test ساخته شود.

### اهداف
- مجموعه queryهای مرجع
- expected relevant knowledge
- تست precision/recall و ranking
- تست عدم نشت knowledge نامرتبط
- تست conflict retrieval
- اجرای خودکار در CI

## 7. Categorized Long-Term Memory

حافظه بلندمدت از یک مجموعه ساده knowledge به دسته‌های مشخص تقسیم شود.

### دسته‌های پیشنهادی
- User Preferences
- Project Facts
- Technical Decisions
- Lessons Learned
- Research Evidence
- Known Failures
- Successful Patterns
- Temporary Context

هر دسته باید retention، confidence، provenance و lifecycle مناسب خود را داشته باشد.

## 8. Resource-Aware Scheduler

Scheduler با توجه به منابع واقعی سیستم تصمیم بگیرد چه کاری چه زمانی اجرا شود.

### اهداف
- CPU/RAM/VRAM awareness
- محدود کردن concurrent jobs
- اولویت‌بندی interactive task نسبت به background task
- زمان‌بندی learning و maintenance در زمان کم‌مصرف
- توقف یا کاهش workload هنگام فشار منابع
- ثبت resource usage برای evaluation

## 9. Offline / Local / Online Modes

سه حالت عملیاتی شفاف تعریف شود:
- Offline: فقط local model، local knowledge و ابزارهای محلی
- Local: سرویس‌های محلی به‌همراه امکانات سیستم
- Online: استفاده کنترل‌شده از web و remote model/provider

هر mode باید policy و permission مشخص داشته باشد.

## 10. Personal Benchmark

یک benchmark اختصاصی برای اندازه‌گیری پیشرفت My-AI ساخته شود.

### دسته‌های پیشنهادی
- Persian/English conversation
- Coding و software engineering
- SQL
- Retrieval
- Context continuation
- Planning
- Tool use
- Error diagnosis و repair
- Web research
- Knowledge conflict
- Resource-aware execution

هر تغییر مهم باید قبل و بعد از خود benchmark شود.

## 11. Semantic Retrieval Evolution

Retrieval از keyword/FTS به یک hybrid retrieval بالغ‌تر تبدیل شود.

### مسیر پیشنهادی
1. FTS5
2. lexical ranking
3. local embeddings
4. semantic similarity
5. hybrid score
6. reranking
7. provenance/confidence-aware ranking

برای هر مرحله باید regression benchmark وجود داشته باشد.

## 12. Knowledge Freshness & Maintenance

برای knowledge یک lifecycle خودکار تعریف شود.

### اهداف
- تشخیص مطالب قدیمی
- scheduled re-validation
- research مجدد برای knowledge مهم
- archive کردن موارد منسوخ
- حفظ provenance و تاریخ اعتبار

## 13. Evaluation Harness

یک Eval Harness مرکزی برای سنجش کل Agent ایجاد شود.

### اهداف
- benchmark ثابت
- scenario-based evaluation
- regression detection
- latency/resource measurement
- quality metrics
- failure classification
- مقایسه model/provider/configurationهای مختلف

## 14. Resource-Aware Model Selection

Model Router و Resource Scheduler در یک policy مشترک تصمیم بگیرند.

### ورودی‌ها
- task complexity
- required context size
- available RAM/VRAM
- CPU load
- latency budget
- offline/online policy

### خروجی
- model
- context size
- concurrency
- timeout
- fallback strategy

## 15. Evidence-Based Completion

گزارش نهایی Agent باید به evidence قابل بررسی متصل باشد.

### Completion Report
- goal
- requirements
- acceptance criteria
- files/artifacts
- research sources
- validation results
- test results
- unresolved limitations
- Git status/diff
- known blocked capabilities

هیچ success claimای بدون evidence معتبر ثبت نشود.

## 16. Capability Registry

یک registry مرکزی برای capabilityهای Agent ایجاد شود.

### نمونه capability
- web research
- local retrieval
- code generation/execution
- browser testing
- Git
- database
- learning
- self-update

برای هر capability این موارد ثبت شود:
- availability
- permission
- platform constraints
- required tools
- validation method
- risk level
- fallback

## 17. Policy & Permission Layer

تمام toolها و capabilityها از یک permission/policy layer عبور کنند.

### اهداف
- least privilege
- approval برای عملیات حساس
- audit log
- per-tool و project-level permissions
- online access control
- execution sandboxing

## 18. Secure Self-Update

Self-update به یک pipeline کاملاً قابل rollback تبدیل شود.

### مراحل
inspect → diagnose → proposal → user approval → snapshot → isolated worktree → implementation → validation → activation → health check → watchdog → rollback

هیچ self-update ناموفق نباید وضعیت سالم قبلی را از بین ببرد.

## 19. Personal Learning Loop

یادگیری Agent از failure و successهای واقعی پروژه به‌صورت کنترل‌شده انجام شود.

### اهداف
- استخراج lesson
- اعتبارسنجی lesson
- ذخیره با provenance
- جلوگیری از memory pollution
- تبدیل lessonهای پایدار به regression test
- حذف یا کاهش وزن lessonهای منسوخ

## 20. Research-to-Code Traceability

هر تصمیم فنی مهم باید بتواند به research evidence خود برگردد.

### زنجیره
requirement → research query → source → finding → decision → implementation → validation

این زنجیره باید در project context و در صورت امکان در Evidence Graph قابل مشاهده باشد.

## 21. Multi-Session & Backup

مدیریت sessionهای متعدد و backup قابل بازیابی.

### اهداف
- چند پروژه هم‌زمان
- session isolation
- persistent project state
- backup/restore
- export/import
- recovery بعد از crash

## 22. Knowledge Management UI

یک UI مدیریتی برای مشاهده و کنترل knowledge و memory.

### قابلیت‌ها
- search/filter
- provenance/confidence
- verification status
- version history
- conflict view
- delete/archive
- manual correction
- retrieval inspection

## 23. Model Management

مدیریت مدل‌ها از داخل خود پروژه.

### قابلیت‌ها
- نصب/حذف model
- health check
- model metadata
- capability profile
- context limit
- resource profile
- benchmark results
- default/fallback policy

## 24. Personal Software-Agent Benchmark Suite

یک مجموعه سناریوی end-to-end ثابت بر اساس نیازهای واقعی پروژه ایجاد شود.

### سناریوها
- ساخت پروژه Python
- ساخت PHP
- ساخت Web
- MQL4/MQL5
- اصلاح پروژه موجود
- ادامه کار با wording متفاوت
- conflicting requirements
- missing tool/compiler
- failed test و repair
- research-required task
- offline-only task

## 25. اولویت اجرای پیشنهادی

برای جلوگیری از پراکندگی، اجرای آینده بهتر است تقریباً با این ترتیب انجام شود:

1. Capability Registry + Policy/Permission Layer
2. Context Budget Manager
3. Model Router + Resource-Aware Model Selection
4. Knowledge Versioning + Categorized Long-Term Memory
5. Conflict Resolution + Evidence Graph
6. Automatic Regression Knowledge Tests + Evaluation Harness
7. Knowledge Freshness & Maintenance
8. Evidence-Based Completion + Research-to-Code Traceability
9. Multi-Session & Backup
10. Knowledge Management UI
11. Model Management
12. Personal Learning Loop
13. Secure Self-Update
14. توسعه benchmarkهای end-to-end و بهبود مستمر

## اصل اجرایی

هر قابلیت جدید باید:
- ابتدا با design و acceptance criteria مشخص شود؛
- یک test یا benchmark قابل اندازه‌گیری داشته باشد؛
- با architecture فعلی سازگار باشد؛
- failure و blocked state را صریحاً مدیریت کند؛
- provenance و audit مناسب داشته باشد؛
- بدون evidence موفقیت را اعلام نکند.

این سند roadmap است و اجرای هر مورد باید در یک تغییر مستقل و قابل ارزیابی انجام شود.
