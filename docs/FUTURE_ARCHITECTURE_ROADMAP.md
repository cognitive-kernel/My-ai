# Future Architecture & Capability Roadmap

این سند roadmap توسعه پیشرفته My-AI است. در هر مرحله implementation باید با تست، benchmark و evidence همراه باشد.

## وضعیت اجرا

### Implemented foundation — 2026-10-01
- Model Router پایه با محدودیت RAM/VRAM/context/capability
- Context Budget Manager قطعی و قابل تست
- Capability Registry
- Policy/Permission Engine با approval برای عملیات حساس و online
- Runtime modes: offline/local/online
- Knowledge Version Store
- Evidence Store و conflict detection پایه
- Evidence/Trace Graph
- Resource Scheduler
- Evidence-based Completion Report
- Evaluation Harness با latency و failure reporting
- Regression tests برای تمام primitiveهای بالا

این foundation عمداً dependency-light است تا روی سخت‌افزار محدود نیز قابل اجرا باشد. این موارد فعلاً به‌صورت primitives مستقل اضافه شده‌اند و ادغام کامل هر primitive در همه مسیرهای runtime باید در مراحل بعدی با regression benchmark انجام شود.

## 1. Model Router
- انتخاب مدل بر اساس complexity، context، capability و RAM/VRAM
- fallback و ثبت دلیل انتخاب
- مدل سبک برای کارهای ساده و مدل قوی‌تر برای کارهای پیچیده
- ادغام کامل با provider lifecycle

## 2. Context Budget Manager
- token budget واقعی متناسب با model
- اولویت current request، state، evidence و relevant history
- summarization و compaction
- جلوگیری از context overflow

## 3. Knowledge Versioning
- نسخه‌بندی knowledge/research/decisions
- provenance، rollback و superseded state
- lifecycle و freshness

## 4. Conflict Resolution
- تشخیص conflict
- مقایسه source/version/freshness/confidence
- resolution قابل توضیح
- حفظ evidence متناقض بدون مخلوط‌کردن آن‌ها

## 5. Evidence Graph
requirement → research → source → claim → decision → artifact → validation را traceable نگه می‌دارد.

## 6. Automatic Regression Knowledge Tests
- queryهای مرجع
- precision/recall/ranking
- isolation و conflict tests
- اجرای CI

## 7. Categorized Long-Term Memory
- User Preferences
- Project Facts
- Technical Decisions
- Lessons Learned
- Research Evidence
- Known Failures
- Successful Patterns
- Temporary Context

## 8. Resource-Aware Scheduler
- CPU/RAM/VRAM awareness
- concurrency limits
- interactive priority
- background maintenance

## 9. Offline / Local / Online Modes
هر mode باید policy، permission و fallback مستقل داشته باشد.

## 10. Personal Benchmark
Benchmark برای conversation، coding، retrieval، planning، tools، repair، research، conflict و resource-awareness.

## 11. Semantic Retrieval Evolution
FTS5 → lexical ranking → local embeddings → semantic similarity → hybrid scoring → reranking → provenance/confidence-aware ranking.

## 12. Knowledge Freshness & Maintenance
scheduled re-validation، archive، superseded state و research مجدد برای knowledge مهم.

## 13. Evaluation Harness
- scenario evaluation
- regression detection
- latency/resource metrics
- failure classification
- model/provider comparison

## 14. Resource-Aware Model Selection
Model Router و Scheduler باید یک policy مشترک برای model/context/concurrency/timeout/fallback داشته باشند.

## 15. Evidence-Based Completion
هیچ success claim بدون validation evidence؛ گزارش باید goal، requirements، acceptance criteria، artifacts، research، tests و limitations را پوشش دهد.

## 16. Capability Registry
هر capability باید availability، permission، platform constraints، validation، risk و fallback داشته باشد.

## 17. Policy & Permission Layer
least privilege، approval، audit، project-level permission، online control و sandboxing.

## 18. Secure Self-Update
inspect → diagnose → proposal → approval → snapshot → isolated worktree → implementation → validation → activation → health check → rollback.

## 19. Personal Learning Loop
lesson extraction → validation → provenance → regression test → lifecycle/retirement.

## 20. Research-to-Code Traceability
requirement → query → source → finding → decision → implementation → validation.

## 21. Multi-Session & Backup
session isolation، persistent state، backup/restore، export/import و crash recovery.

## 22. Knowledge Management UI
search/filter، provenance، confidence، version history، conflicts، archive/delete و retrieval inspection.

## 23. Model Management
model metadata، health، capability profile، context limit، resource profile، benchmark و fallback policy.

## 24. Personal Software-Agent Benchmark Suite
سناریوهای end-to-end برای Python، PHP، Web، MQL4/MQL5، repair، wording variation، conflicts، missing tools، failed tests، research و offline-only.

## اولویت بعدی
1. ادغام Model Router و Resource Scheduler در runtime واقعی
2. Context Budget واقعی بر اساس context window مدل
3. Knowledge Versioning/Conflict به storage اصلی
4. Evaluation Harness مرکزی و benchmark dataset
5. Evidence Graph در execution trace
6. Freshness/maintenance
7. completion/traceability
8. multi-session/backup
9. management UI
10. model management
11. learning loop
12. secure self-update و benchmarkهای end-to-end

## اصل اجرایی
هر قابلیت جدید باید design، acceptance criteria، test/benchmark، failure handling، provenance و evidence موفقیت داشته باشد. قابلیت‌های جدید نباید با trigger-wordهای brittle جایگزین semantic reasoning شوند.

## وضعیت تکمیل معماری — 2026-10-01

تمام 24 محور roadmap اکنون دارای implementation یا integration عملی در runtime هستند:

| محور | implementation |
|---|---|
| 1 Model Router | persistent runtime selection + agent integration |
| 2 Context Budget | budget + context-window-aware packing |
| 3 Knowledge Versioning | knowledge_versions + version history API |
| 4 Conflict Resolution | conflict records + explicit resolution |
| 5 Evidence Graph | persistent nodes/edges |
| 6 Regression Knowledge Tests | retrieval regressions + roadmap tests |
| 7 Categorized Memory | knowledge categories + learning lessons |
| 8 Resource Scheduler | shared runtime scheduler |
| 9 Runtime Modes | offline/local/online authorization |
| 10 Personal Benchmark | persistent benchmark cases/results |
| 11 Semantic Retrieval | hybrid retrieval + candidate validation |
| 12 Freshness | scheduled maintenance/review records |
| 13 Evaluation Harness | evaluation primitive + persistent reports |
| 14 Resource-Aware Selection | RAM/VRAM/context/capability selection |
| 15 Evidence Completion | completion report with validation/limitations |
| 16 Capability Registry | persistent capability registry |
| 17 Policy Layer | approval + online permission boundary |
| 18 Secure Self-Update | snapshot/worktree/validation/watchdog/rollback |
| 19 Personal Learning Loop | lessons with provenance/regression case |
| 20 Research-to-Code | persistent research_trace |
| 21 Multi-Session & Backup | session isolation + existing backup/restore preserved |
| 22 Knowledge UI | roadmap knowledge management page |
| 23 Model Management | model/resource APIs and management page |
| 24 Agent Benchmark Suite | personal_agent_suite.json |

### Runtime acceptance surface

Roadmap APIs cover profile, model selection, resources, capabilities/authorization, knowledge versions/conflicts, evidence graph, execution trace, maintenance, lessons, research trace, completion reports and benchmark reporting.

این لایه‌ها additive هستند و storage دانش، conversation و backup موجود را حذف یا بازنویسی نمی‌کنند.

## Gap closure audit — 2026-10-01

بازبینی implementation نشان داد که چند مورد در جدول قبلی فقط به‌صورت primitive یا API بودند و ادغام runtime آن‌ها ناقص بود. این موارد اکنون تکمیل شده‌اند:

- **Context compaction:** در ContextBudgetManager فشرده‌سازی deterministic زیر فشار budget اضافه شد؛ داده‌های high-priority حفظ می‌شوند.
- **Evidence Graph runtime:** درخواست، model decision و knowledge provenance در مسیر chat/stream به node/edgeهای پایدار متصل می‌شوند.
- **Research-to-Code runtime:** اجرای software agent، sourceهای research را به requirement و artifact در research_trace و evidence graph متصل می‌کند.
- **Resource-aware maintenance:** maintenance با همان scheduler مشترک اجرا می‌شود و در زمان اشغال interactive slot به‌جای رقابت، deferred می‌شود.
- **Scheduled freshness:** maintenance به lifecycle برنامه اضافه شد و به‌صورت دوره‌ای در runtime اجرا می‌شود؛ archive همچنان explicit و non-destructive است.
- **Capability metadata:** platform constraints، validation و fallback برای capabilityها در storage و API قابل ثبت هستند.
- **Conflict inspection:** علاوه بر resolution، دو نسخه، source و confidence قابل مقایسه و inspection هستند.
- **Learning lifecycle:** lessonها lifecycle صریح candidate → validated → retired دارند.
- **Model management:** resource-fit/health profile و model-selection benchmark در runtime/API اضافه شدند.
- **Personal benchmark execution:** suite علاوه بر schema validation، runner اجرایی برای retrieval/toolchain readiness و گزارش blocked/failed/ready دارد؛ سناریوهای live-agent به‌صراحت به اجرای live نیاز دارند.
- **Knowledge management UI/API:** inventory/search، category filtering، archive، version history و retrieval inspection در سطح roadmap اضافه شدند.
- **Roadmap API security:** تمام endpointهای roadmap زیر احراز هویت موجود برنامه قرار گرفتند.

موارد زیر عمداً destructive/automatic نشده‌اند: حذف خودکار knowledge، بازنویسی backup، و activation خودکار self-update بدون approval. این‌ها مطابق اصل local-first و حفاظت از داده باقی می‌مانند.
