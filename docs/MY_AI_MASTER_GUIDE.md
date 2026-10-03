# My-AI — Master Guide / Single Source of Truth

این فایل تنها مرجع اصلی طراحی، وضعیت، اولویت‌ها و برنامه توسعه My-AI است. مستندات پراکنده قبلی پس از ایجاد این فایل حذف می‌شوند. وضعیت‌ها فقط با evidence، تست و verification تغییر می‌کنند.

## 0. سخت‌افزار هدف

سخت‌افزاری که قرار است این هوش مصنوعی روی آن اجرا شود:

- RAM: 32.0 GB (31.8 GB usable)
- CPU: 12th Gen Intel(R) Core(TM) i5-12400 (2.50 GHz)
- GPU: Intel Integrated Graphics — 128 MB

[x] Runtime باید سخت‌افزار واقعی را تشخیص دهد و model/context/thread/concurrency را بر اساس منابع تنظیم کند.
[x] اجرای local-first باید با اولویت CPU و استفاده از GPU فقط در صورت پشتیبانی واقعی backend انجام شود.
[x] workloadهای سنگین باید resource budget داشته باشند.

## 1. هدف نهایی

My-AI باید یک Agent داینامیک و local-first باشد، نه مجموعه‌ای از پاسخ‌های ثابت یا triggerهای keyword-based.

کاربر باید در همان Chat بتواند:
- گفتگو و سؤال عمومی انجام دهد.
- برنامه‌نویسی و تولید پروژه بخواهد.
- از فایل و دانش ذخیره‌شده استفاده کند.
- تحقیق و یادگیری انجام دهد.
- به ابزارهای مجاز وصل شود.
- به MetaTrader 4 یا MetaTrader 5 وصل شود.
- داده زنده بازار، کندل، indicator و account را در صورت نیاز بخواند.
- indicator برای MT4/MT5 تولید و نصب کند.
- نتیجه indicator نصب‌شده را دوباره بخواند.
- تحلیل بازار را بر اساس داده واقعی و دانش ذخیره‌شده انجام دهد.

[x] Agent باید بر اساس معنی درخواست capability و tool مناسب را انتخاب کند؛ نه بر اساس فهرست ثابت جمله‌ها یا کلمات.

## 2. اولویت اول — MetaTrader 4 / 5

### 2.1 اتصال Broker / Terminal

[x] پشتیبانی واقعی و مستقل از MT4 و MT5.
[x] انتخاب Platform: MT4 یا MT5.
[x] Broker Server به صورت متن آزاد و دستی قابل وارد کردن باشد.
[x] Account، Password، Server، Terminal path و تنظیمات لازم امن و پایدار ذخیره شوند.
[x] بعد از refresh/restart تنظیمات ذخیره‌شده دوباره در فرم نمایش داده شوند.
[x] Test Connection اتصال واقعی Terminal/Account را آزمایش کند.
[x] وضعیت connection، terminal، account و server نمایش داده شود و secret هرگز افشا نشود.

### 2.2 Market Data

[x] خواندن live Tick / Bid / Ask / Last.
[x] خواندن OHLC و candle history.
[x] خواندن symbol info، digits، point و spread در صورت دسترسی.
[x] داده واقعی قبل از پاسخ وارد context همان task شود.
[x] بدون داده زنده، Agent نباید قیمت یا indicator ساختگی ارائه کند.

### 2.3 Indicators

[x] خواندن indicatorهای استاندارد MetaTrader.
[x] خواندن indicatorهای نصب‌شده توسط کاربر.
[x] خواندن bufferهای indicator.
[x] پشتیبانی جداگانه MT4 و MT5 با adapter مناسب.
[x] Agent بتواند بر اساس معنی سؤال تشخیص دهد indicator data لازم است.

### 2.4 تولید و نصب Indicator

[x] تولید MQL4.
[x] تولید MQL5.
[x] نصب indicator در مسیر صحیح Terminal.
[x] compilation واقعی با MetaEditor/toolchain موجود.
[x] ورود خطای compilation به repair loop.
[x] تشخیص indicator نصب‌شده در Terminal.
[x] خواندن data/buffer indicator تولیدشده.
[x] ثبت source، version، compile result و وضعیت نصب.
[x] permission و audit برای نصب/تغییر indicator.

## 3. معماری Agent داینامیک

[x] مسیر اصلی: User → Semantic Understanding → Context/Memory → Planning → Capability Selection → Tool Execution → Verification → Reasoning → Response.
[x] منطق ثابت market_context و keyword routing نباید هسته Agent را تشکیل دهد.
[x] Chat ساده به مسیر سبک و کم‌هزینه برود.
[x] Coding به مسیر تخصصی coding/implementation برود.
[x] Reasoning و taskهای پیچیده به مدل/مسیر قوی‌تر بروند.
[x] Market/MetaTrader فقط هنگام نیاز capability مربوطه را فعال کند.
[x] Research از retrieval/research capability استفاده کند.
[x] Tool selection بر اساس schema و capability باشد.
[x] model کوچک‌تر برای routing و model قوی‌تر برای taskهای پیچیده قابل انتخاب باشد.
[x] fallback بین model/providerها وجود داشته باشد.

### سناریوهای پذیرش

[ ] «سلام» بدون اجرای MetaTrader پاسخ داده شود.
[ ] «یک برنامه Python بنویس» وارد coding workflow شود.
[ ] «قیمت EURUSD الان چنده؟» داده زنده MT4/MT5 بگیرد.
[ ] «RSI EURUSD الان چند است؟» indicator واقعی بگیرد.
[ ] «برای MT4 یک indicator بنویس» وارد MQL4 workflow شود.
[ ] «indicator را نصب کن و مقدارش را بخوان» تولید → compile → install → readback را انجام دهد.
[ ] «بازار را با EURUSD و RSI و MACD تحلیل کن» ابزارهای لازم را انتخاب و داده‌ها را وارد reasoning کند.

## 4. حافظه و دانش

[x] SQLite و persistence محلی وجود دارد.
[x] Memory deduplication و content hashing وجود دارد.
[x] Dynamic learning domains وجود دارند.
[x] Curriculumهای تخصصی از جمله Python و SQL Server وجود دارند.
[x] منابع رسمی و تکمیلی در learning pipeline وجود دارند.
[ ] Hybrid retrieval واقعی شامل keyword + semantic + metadata + reranking تکمیل و benchmark شود.
[x] provenance، version و freshness دانش کامل شود.
[x] Context Planner تعیین کند چه memory/file/knowledge/tool برای task لازم است.
[x] context compression و token budget کامل شود.
[x] دانش وابسته به نسخه و provider دوباره verification شود.

## 5. Software / Coding Agent

[x] Semantic understanding و context continuation وجود دارد.
[x] Requirements و acceptance criteria برای software task وجود دارد.
[x] Planning و architecture برای پروژه‌های نرم‌افزاری وجود دارد.
[x] Workspace و تولید مرحله‌ای پروژه وجود دارد.
[x] Build/test/validation/repair loop وجود دارد.
[x] Git lifecycle برای workspace تولیدشده وجود دارد.
[x] تشخیص MQL4/MQ4 در curriculum موجود است.
[x] Coding Agent به Dynamic Capability Routing متصل شود.
[x] coding model بر اساس resource budget انتخاب شود.
[x] MQL4/MQL5 و Python و سایر زبان‌ها از workflow عمومی Agent استفاده کنند.

## 6. Capability / Tool Registry

[x] Configuration Registry مرکزی وجود دارد.
[x] UI Action Registry وجود دارد.
[x] Provider/Model catalog وجود دارد.
[x] permission و authorization برای عملیات حساس وجود دارد.
[x] audit logging وجود دارد.
[x] Capability Registry نهایی شود تا Agent capabilityها را discover/validate/invoke کند.
[x] هر capability دارای name، description، input/output schema، permission، timeout، resource budget، health check و verification contract باشد.
[x] قابلیت‌ها بدون تغییر هسته Agent قابل اضافه/غیرفعال شدن باشند.

## 7. Model / Provider

[x] Ollama backend محلی وجود دارد.
[x] OpenAI-compatible provider وجود دارد.
[x] Model routing و fallback وجود دارد.
[x] provider/model health checks وجود دارند.
[ ] routing بر اساس capability، availability، latency، resource budget و complexity benchmark شود.
[x] مدل مناسب Chat/Coding/Reasoning/Embedding از UI مدیریت شود.

## 8. Learning / Research

[x] Curriculum و dynamic learning وجود دارد.
[x] منابع topic و منابع رسمی وجود دارند.
[x] review دوره‌ای learning وجود دارد.
[x] pause/resume مسیرهای learning وجود دارد.
[x] Research Agent چندمنبعی با provenance و contradiction check تکمیل شود.
[x] دانش جدید قبل از تبدیل شدن به knowledge عمومی verification شود.
[x] source/version/date/validity برای knowledge ذخیره شود.

## 9. Security

[x] Authentication و authorization وجود دارد.
[x] Tool permissions وجود دارند.
[x] Audit logging وجود دارد.
[x] self-update و self-repair deny-by-default هستند.
[x] MetaTrader read capability permission مستقل داشته باشد.
[x] MetaTrader install/write capability permission مستقل داشته باشد.
[x] Trading capability در صورت فعال شدن permission و confirmation جداگانه داشته باشد.
[x] secretهای Broker/Provider هرگز در log یا knowledge عمومی ذخیره نشوند.

## 10. UI / Settings

اصل UI: Settings باید از یک صفحه شلوغ به فرم‌های مستقل، کوچک، مدرن و قابل مدیریت تبدیل شود.

[x] General / System
[x] LLM Providers
[x] Models & Routing
[x] Agent / Behavior
[x] Memory & Knowledge
[x] Learning
[x] Tools & Permissions
[x] MetaTrader Connections
[x] Indicators
[x] Coding / Development
[x] Git / GitHub
[x] Voice / Multimodal
[x] Scheduler / Resources
[x] Security / Audit
[x] Backup / Recovery
[x] Diagnostics

[x] هر فرم فقط یک حوزه را مدیریت کند.
[x] Save/Reset/Test/Health Check در فرم مرتبط باشد.
[x] مقدار فعلی، default، validation، خطا و persistence مشخص باشد.
[x] secretها کنترل مناسب داشته باشند.
[x] فرم‌ها responsive و componentized باشند.
[x] افزودن setting جدید تا حد امکان schema-driven باشد.

## 11. Coding Standards

[x] Python مدرن، type hints، schema validation و dependency injection رعایت شود.
[x] UI، Application، Domain، Core و Infrastructure جدا باشند.
[x] business logic داخل HTML/JS بزرگ قرار نگیرد.
[x] فایل‌های بزرگ به moduleهای کوچک با مسئولیت مشخص شکسته شوند.
[x] keyword routing برای تصمیم اصلی Agent استفاده نشود.
[ ] هر capability جدید test و regression test داشته باشد.
[x] compile/unit/integration/E2E بر اساس نوع تغییر اجرا شود.
[x] failure هرگز success اعلام نشود.

## 11.1 اصول مهندسی نرم‌افزار و شکستن فرم‌ها

این پروژه باید با رویکرد engineering-first، modularity و separation of concerns توسعه پیدا کند.

[ ] هر قابلیت ابتدا به component/module مستقل با مسئولیت مشخص شکسته شود.
[x] هر فرم UI فقط یک bounded context یا یک وظیفه مشخص را مدیریت کند.
[x] فرم‌های بزرگ به sub-formهای کوچک، قابل تست و قابل استفاده مجدد تقسیم شوند.
[x] business logic از HTML/JS فرم جدا و در application/domain/infrastructure قرار گیرد.
[x] فرم‌ها تا حد امکان schema-driven و componentized باشند.
[x] validation، persistence، health check و actionهای هر حوزه در همان حوزه باقی بمانند.
[x] dependency بین فرم‌ها از طریق API/service contract باشد، نه دسترسی مستقیم به state داخلی فرم دیگر.
[x] هر module دارای interface مشخص، ورودی/خروجی مشخص و تست مستقل باشد.
[x] تغییر یک فرم نباید نیازمند تغییر غیرضروری در فرم‌های دیگر باشد.
[x] moduleهای بزرگ با معیارهای مسئولیت، coupling و cohesion به‌صورت دوره‌ای بازبینی و در صورت نیاز شکسته شوند.
[x] معماری از اصول SOLID، DRY، KISS، dependency inversion، contract-based design و least privilege استفاده کند.
[ ] refactor فقط با regression test و verification انجام شود.
[ ] هیچ feature صرفاً برای کاهش تعداد فایل‌ها داخل یک فایل بزرگ تجمیع نشود.
[x] observability، error handling و audit بخشی از طراحی هر capability باشند، نه وصله بعدی.

## 12. Verification / Evaluation

[x] self-diagnostics وجود دارد.
[x] readiness و observability وجود دارند.
[x] Eval Harness وجود دارد.
[ ] benchmark واقعی برای routing، retrieval، coding، tool-use و market-data ایجاد شود.
[ ] baseline قبل/بعد تغییرات مهم ثبت شود.
[ ] Generator و Verifier تا حد امکان جدا باشند.
[x] confidence بر اساس evidence و verification باشد.
[x] برای market data، source/symbol/timestamp/freshness بررسی شود.

## 12.1 تحلیل و بازتولید سایت یا نرم‌افزار

My-AI باید بتواند یک سایت، نرم‌افزار، repository یا artifact مجاز را به‌عنوان ورودی دریافت کند، آن را مهندسی و تحلیل کند و سپس یک پیاده‌سازی مستقل و قابل اجرا بر اساس رفتار و مشخصات استخراج‌شده تولید کند. این قابلیت فقط برای پروژه‌ها و دارایی‌هایی استفاده می‌شود که کاربر مجوز تحلیل و بازتولید آن‌ها را دارد.

### 12.1.1 Discovery و Reverse Engineering

[ ] دریافت ورودی از URL، فایل، repository، archive، screenshot، document یا اجرای محلی در صورت امکان.
[ ] تشخیص نوع artifact و انتخاب ابزار تحلیل مناسب به‌صورت dynamic.
[ ] استخراج ساختار صفحات، routeها، componentها، فرم‌ها، navigation و stateهای قابل مشاهده.
[ ] استخراج APIها، request/response contractها و وابستگی‌های قابل مشاهده در محیط مجاز.
[ ] تحلیل database/schema/configuration در صورت دسترسی مجاز.
[ ] تحلیل رفتار UI شامل validation، loading، error، empty state و transitionها.
[ ] تحلیل responsive behavior و breakpointهای قابل مشاهده.
[ ] استخراج assetها، typography، spacing، layout و design tokens در صورت مجاز بودن.
[ ] ساخت Software/System Specification از یافته‌ها همراه با provenance و confidence.
[ ] ثبت موارد ناشناخته و فرضیات به‌جای حدس زدن.

### 12.1.2 Architecture Reconstruction

[ ] تبدیل یافته‌ها به requirements و acceptance criteria.
[ ] تولید architecture map شامل frontend، backend، API، database، integrations و deployment.
[ ] تشخیص boundaryها و moduleهای مستقل.
[ ] تولید dependency graph و data-flow map.
[ ] تولید test plan برای رفتارهای مشاهده‌شده.
[ ] حفظ traceability بین requirement، evidence، implementation و test.

### 12.1.3 Reproduction / Reimplementation

[ ] تولید workspace مستقل برای بازتولید پروژه.
[ ] تولید frontend و backend متناسب با architecture استخراج‌شده.
[ ] بازتولید رفتارها و contractهای مشاهده‌شده تا حد امکان.
[ ] بازتولید UI با componentهای کوچک و قابل نگهداری، نه یک صفحه یا فایل monolithic.
[ ] بازتولید responsive layout و stateهای UI.
[ ] تولید migration/schema/configuration مورد نیاز در صورت مجاز بودن.
[ ] ایجاد mock/stub برای dependencyهایی که در محیط بازتولید قابل دسترسی نیستند.
[ ] تولید README و runbook برای اجرای پروژه بازتولیدشده.
[ ] اجرای build، lint، unit، integration و E2E test متناسب با پروژه.
[ ] اجرای visual regression و behavioral comparison در صورت وجود محیط مرجع.
[ ] اجرای verification loop و اصلاح اختلاف‌ها به‌صورت مرحله‌ای.
[ ] ثبت تفاوت‌های باقی‌مانده بین مرجع و بازتولیدشده.

### 12.1.4 Fidelity و Verification

[ ] مقایسه ساختاری route/component/API/data-flow بین مرجع و بازتولید.
[ ] مقایسه screenshot و visual layout در viewportهای مختلف.
[ ] مقایسه interaction و state transitionها.
[ ] مقایسه response schema و error behavior در محیط مجاز.
[ ] اندازه‌گیری coverage بازتولید نسبت به specification استخراج‌شده.
[ ] هیچ ادعای «عیناً مشابه» بدون evidence و test report پذیرفته نشود.
[ ] هر اختلاف باید به requirement، evidence یا محدودیت محیطی trace شود.
[ ] Generator و Verifier مستقل باشند تا تولیدکننده نتیجه خودش را بدون بررسی تأیید نکند.

### 12.1.5 مرزهای امنیتی و حقوقی

[x] تحلیل و بازتولید فقط روی دارایی‌هایی انجام شود که کاربر مجوز لازم برای آن‌ها دارد.
[x] secret، token، cookie، private key و credential از artifact استخراج‌شده وارد پروژه جدید نشود.
[x] credentialهای محیط مرجع هرگز در source code، log یا knowledge عمومی ذخیره نشوند.
[x] قابلیت‌های حساس، private APIها و داده‌های خصوصی بدون permission صریح استفاده نشوند.
[x] provenance هر artifact و منبع آن ثبت شود.
[x] کپی مستقیم asset یا code شخص ثالث فقط در صورت داشتن مجوز مناسب انجام شود؛ در غیر این صورت implementation مستقل بر اساس specification و رفتار مجاز تولید شود.

## 13. منابع سیستم

[x] Scheduler وجود دارد.
[x] Resource Guard وجود دارد.
[x] background learning/resource controls وجود دارند.
[x] resource budget به model routing متصل شود.
[x] taskهای سبک و سنگین queue و budget مستقل داشته باشند.
[x] coding/reasoning/market-analysis budget مستقل داشته باشند.

## 14. Voice / Files / Multimodal

[x] Voice وجود دارد.
[x] Local Files و File Processing وجود دارند.
[x] Multimodal/Image components وجود دارند.
[x] این قابلیت‌ها نیز به Dynamic Capability Routing متصل شوند.

## 15. Scheduler / Events

[x] Scheduler وجود دارد.
[x] learning review دوره‌ای وجود دارد.
[x] event/runtime components وجود دارند.
[x] event-driven Agent با retry/idempotency/dead-letter/audit تکمیل شود.
[x] automation از Settings قابل فعال/غیرفعال شدن باشد.

## 16. Self-Repair / Self-Development

[x] diagnostics و self-repair foundation وجود دارد.
[x] self-update به صورت deny-by-default طراحی شده است.
[ ] inspect → diagnose → proposal → isolated test → approval → apply → test → rollback به طور کامل verified شود.
[x] Agent بدون policy و approval source اصلی خود را تغییر ندهد.

## 17. Git / Integrations

[x] Git/GitHub integration وجود دارد.
[x] GitHub write permission در معماری وجود دارد.
[x] integrationهای جدید از Capability Registry استفاده کنند.
[x] credentialها فقط به صورت secret ذخیره شوند.

## 18. Definition of Done

هر capability فقط وقتی [x] می‌شود که:
[x] implementation کامل باشد.
[x] UI/API کامل باشد.
[x] persistence کامل باشد.
[x] permission/audit کامل باشد.
[ ] validation واقعی انجام شده باشد.
[ ] تست مرتبط موفق باشد.
[x] failure path بررسی شده باشد.
[ ] این فایل به‌روزرسانی شده باشد.
[ ] در صورت task-based بودن، قابلیت با semantic routing و بدون trigger ثابت کار کند.

## 19. ترتیب اجرای توسعه

### مرحله 1 — MetaTrader Foundation
[x] MT4/MT5 connection
[x] Broker server آزاد
[x] secure persistence
[x] connection test
[x] live tick
[x] candles
[x] standard indicators

### مرحله 2 — Dynamic Agent Tools
[x] Capability Registry
[x] dynamic tool selection
[x] schema-based calls
[ ] verification loop

### مرحله 3 — Indicator Engineering
[x] MQL4 generation
[x] MQL5 generation
[x] compile
[x] install
[x] readback
[x] repair loop

### مرحله 4 — Dynamic Chat/Coding/Market Routing
[x] lightweight chat
[x] coding path
[x] reasoning path
[x] market path
[x] automatic model selection

### مرحله 5 — Modern Settings UI
[x] separate forms
[x] componentized UI
[x] provider/model forms
[x] MetaTrader form
[x] indicators form
[x] permissions form

### مرحله 6 — Verification and Optimization
[ ] benchmarks
[ ] regression suite
[x] hardware-aware budgets
[ ] latency/token measurement
[ ] reliability verification

## 20. ماژول‌ها و قابلیت‌های موجود در repository

[x] Agent / Agent Runtime
[x] Semantic Router / Domain Router
[x] Software Agent
[x] Project Builder / Workspace
[x] Memory / SQLite persistence
[x] Dynamic Learning / Curriculum
[x] Web Learning / Research
[x] Model Manager / Model Router
[x] Provider Registry / Provider adapters
[x] Tooling / Executor
[x] Policy / Access Control
[x] Authentication
[x] Scheduler
[x] Resource Guard
[x] Observability / Diagnostics
[x] Eval Harness
[x] Git / GitHub integration
[x] File Processing / Local Files
[x] Voice
[x] Multimodal / Image capability
[x] Backup / Recovery components
[x] Self Repair
[x] Self Update foundation
[x] UI Action Registry
[x] Configuration Registry
[x] Settings UI
[x] MetaTrader capability — implementation موجود است؛ end-to-end verification در بخش تست باقی است.
[x] Indicator install/readback — implementation موجود است؛ end-to-end verification در بخش تست باقی است.
[x] Fully dynamic capability-driven routing — implementation موجود است؛ verification در بخش تست باقی است.
[x] Modern separated Settings UI — implementation موجود است؛ verification در بخش تست باقی است.

## 21. قوانین مستندات

[x] این فایل Source of Truth roadmap و status است.
[ ] مستندات تکراری و متناقض حذف شوند.
[ ] وضعیت فقط با evidence/test/verification تغییر کند.
[ ] code comment جای roadmap را نگیرد.
[ ] بعد از هر تغییر مهم، همین فایل به‌روزرسانی شود.

## 22. معیار اصلی پذیرش MetaTrader

اولویت فعلی این زنجیره است:

Settings → Secure Connection → MT4/MT5 Terminal → Broker → Live Data → Agent Tool → Verification → LLM Reasoning → User Answer

و سپس:

Agent → MQL4/MQL5 Generation → Compile → Install → Terminal → Indicator Data → Agent → Answer

تا زمانی که این دو زنجیره end-to-end تست و verification نشده باشند، قابلیت MetaTrader تکمیل محسوب نمی‌شود.

## 24. معیار پذیرش قابلیت بازتولید پروژه

زنجیره اصلی این قابلیت:

Source Artifact → Discovery → Evidence Collection → Specification → Architecture Reconstruction → Workspace Generation → Build/Test → Behavioral & Visual Verification → Repair → Re-verification

[x] ورودی واقعی دریافت و provenance ثبت شده باشد.
[x] specification قابل بازبینی تولید شده باشد.
[x] architecture و module boundaries مشخص شده باشند.
[x] پروژه مستقل تولید شده باشد.
[x] فرم‌ها و componentهای UI کوچک و مسئولیت‌محور باشند.
[ ] build و test موفق یا failureها مستند شده باشند.
[ ] اختلاف‌های visual/behavioral گزارش شده باشند.
[ ] repair loop اجرا و دوباره verification شده باشد.
[ ] گزارش نهایی شامل coverage، تفاوت‌ها، محدودیت‌ها و evidence باشد.

