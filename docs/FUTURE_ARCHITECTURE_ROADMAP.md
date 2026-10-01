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
