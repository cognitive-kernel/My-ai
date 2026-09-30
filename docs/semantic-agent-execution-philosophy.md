# فلسفه و اصول Semantic Agent در My-AI

## هدف
هدف این سند ثبت فلسفه تصمیم‌گیری و اجرای Agent است تا توسعه‌های بعدی به سمت یک Semantic Agent قابل اتکا باقی بماند.
هدف کپی‌کردن کد یا معماری داخلی ChatGPT نیست؛ هدف، پیاده‌سازی همان الگوی رفتاری مهندسی است: فهم معنای درخواست، استفاده از context، برنامه‌ریزی action، جداسازی تشخیص از مجوز اجرا، و جلوگیری از side effect ناشی از خطای مدل.

## 1. تصمیم‌گیری باید Semantic باشد
Agent نباید برای تشخیص intent یا action به فهرست keywordها و trigger phraseها وابسته باشد. درخواست‌هایی با wording متفاوت اما معنای یکسان باید به نتیجه یکسان برسند.

اصل: Meaning > Keywords

## 2. Router فقط تشخیص می‌دهد
Semantic Router وظیفه دارد intent، action، goal، target، context و confidence را استخراج کند؛ اما خروجی Router به‌تنهایی اجازه اجرای side effect نیست.

مثلاً create_artifact فقط یعنی مدل تشخیص داده احتمالاً کاربر artifact می‌خواهد، نه اینکه Project Builder مجاز به اجراست.

## 3. Execution Authorization مستقل از Router است
قبل از هر عملیات دارای side effect باید یک Execution Policy مستقل تصمیم بگیرد.

این policy باید پیام فعلی کاربر، conversation history، current task، conversation state، intent، action، target artifact، confirmation state، سطح ریسک و محدودیت‌های امنیتی را در نظر بگیرد.

Router می‌تواند اشتباه کند؛ خطای Router نباید مستقیماً به اجرای ناخواسته تبدیل شود.

## 4. پیام فعلی کاربر بالاترین اولویت را دارد
History برای حل referenceها و ادامه task استفاده می‌شود، اما نباید یک درخواست یا پاسخ قدیمی را به دستور جدید تبدیل کند.

مثلاً اگر کاربر قبلاً پروژه ساخته و اکنون فقط بگوید «سلام»، پیام فعلی نباید باعث ادامه build یا modification شود.

## 5. Context برای فهم است، نه ساختن دستور جدید
Conversation history، memory و knowledge می‌توانند معنای پیام فعلی را کامل کنند؛ اما retrieved knowledge یا پاسخ قبلی assistant نباید خودش تبدیل به user instruction شود.

Context may clarify intent; context must not invent authorization.

## 6. Side Effect باید یک مرز مشخص داشته باشد
هر عملی که محیط را تغییر می‌دهد باید از Execution Boundary عبور کند؛ از جمله ساخت پروژه، تغییر فایل، اجرای کد، Git write، self-update، database operation و عملیات خارجی.

مسیر مطلوب:
User Message → Semantic Understanding → Action Planning → Execution Authorization → Executor

نه:
User Message → keyword/intent → immediate side effect

## 7. Project Builder فقط با مجوز معنایی اجرا شود
Project Builder نباید مستقیماً بر اساس coding یا create_artifact اجرا شود.

شرط منطقی:
Router says create_artifact + Execution Policy confirms current user intent + no blocking policy = Project Builder may execute

این policy باید semantic باشد، نه وابسته به markerهایی مانند «بساز»، «create» یا «build».

## 8. خطای Router نباید side effect ایجاد کند
این یک invariant مهم است.

اگر Router برای «سلام» به‌اشتباه coding + create_artifact برگرداند، Execution Policy باید ناسازگاری را تشخیص دهد و side effect را block کند.

## 9. Continue Task باید semantic باشد
پیام‌هایی مانند «ادامه بده»، «همون قبلی رو کامل کن»، «برو مرحله بعد» و «نسخه قبلی رو اصلاح کن» ممکن است task قبلی را ادامه دهند.

Continuation باید با conversation state و task context تفسیر شود؛ اما بدون task معتبر و authorization مناسب نباید side effect ایجاد کند.

## 10. Actionها باید از هم تفکیک شوند
حداقل تفاوت این actionها باید حفظ شود:
answer، explain، analyze، create_artifact، modify_artifact، execute، inspect، save، report، remediate، continue_task، confirm_high_risk

شباهت کلمات نباید باعث یکی‌شدن actionها شود. مثلاً «چطور یک پروژه Python بسازم؟» با «یک پروژه Python بساز» از نظر action یکسان نیست.

## 11. Confidence مجوز اجرا نیست
حتی confidence بالا نباید authorization محسوب شود. Confidence برای ارزیابی کیفیت تشخیص است؛ Authorization تصمیمی مستقل است.

## 12. عملیات پرریسک confirmation جداگانه دارند
برای actionهای پرریسک باید policy مخصوص وجود داشته باشد. وجود intent به‌تنهایی کافی نیست.

## 13. Streaming نباید bypass باشد
stream_chat و مسیر معمول chat باید از Execution Policy یکسان استفاده کنند. هیچ مسیر جایگزینی نباید policy را دور بزند.

## 14. Persistence بخشی از correctness است
ثبت user message، assistant response، session state و task state باید مالک مشخص داشته باشد. یک turn نباید دوبار ذخیره، ناقص ذخیره یا پس از refresh ناپدید شود.

## 15. Test Matrix باید بر اساس معنا باشد
برای هر action باید wordingهای متفاوت، فارسی و انگلیسی، درخواست مستقیم و غیرمستقیم، context قبلی، continuation، درخواست مبهم، پیام عادی، خطای Router و confidence بالا با intent اشتباه آزمایش شود.

هدف: رفتار درست باید نسبت به تغییر wording پایدار بماند.

## معماری مرجع
User Message
  ↓
Conversation + State
  ↓
Semantic Router
  ↓
Intent + Action + Goal + Target + Context
  ↓
Action Planner
  ↓
Execution Authorization
  ├─ Block
  ├─ Ask / Confirm
  └─ Allow → Executor / Tool → Result → Persistence / State → Final Response

## قانون طلایی
مدل می‌تواند پیشنهاد بدهد؛ مدل به‌تنهایی نباید side effect را مجاز کند.

کلمات می‌توانند evidence باشند، اما نباید policy تصمیم‌گیری باشند.

## معیار موفقیت
1. تغییر wording نباید intent را شکننده کند.
2. context باید به فهم درخواست کمک کند.
3. context نباید بدون درخواست فعلی action جدید ایجاد کند.
4. Router نباید مستقیماً executor را فعال کند.
5. side effect فقط از Execution Authorization عبور کند.
6. اشتباه Router نباید باعث ساخت، اجرا یا تغییر ناخواسته شود.
7. chat و streaming policy یکسان داشته باشند.
8. persistence deterministic و قابل تست باشد.
9. regression testها رفتارهای بحرانی را محافظت کنند.
10. افزودن action جدید نباید نیازمند افزودن keyword به یک لیست مرکزی باشد.

## وضعیت فعلی My-AI
Router فعلی پروژه از نظر فلسفه semantic پایه مناسبی دارد و prompt آن صراحتاً از trigger-word routing منع شده است.

قسمتی که باید تکامل پیدا کند، مرز بین Semantic Router و Execution است.

گیت keyword-based فعلی برای جلوگیری از ساخت ناخواسته پروژه یک راهکار حفاظتی موقت است و نباید معماری نهایی باشد.

هدف توسعه:
Semantic Router → Execution Planner → Semantic Authorization → Executor

## دستور توسعه برای آینده
هر قابلیت جدید Agent باید قبل از merge بررسی کند:
1. آیا تشخیص semantic است یا keyword-based؟
2. آیا Router فقط intent را تشخیص می‌دهد؟
3. آیا execution authorization مستقل است؟
4. آیا side effect بدون authorization ممکن است؟
5. آیا context می‌تواند ناخواسته action جدید ایجاد کند؟
6. آیا streaming همان policy را رعایت می‌کند؟
7. آیا برای wordingهای متفاوت test وجود دارد؟
8. آیا خطای Router با test پوشش داده شده است؟
9. آیا persistence deterministic است؟
10. آیا قابلیت جدید bypass برای Execution Policy ایجاد می‌کند؟

اگر پاسخ هرکدام منفی باشد، قابلیت قبل از merge نیاز به بازبینی معماری دارد.