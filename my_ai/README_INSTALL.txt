My-AI inference fix (context-aware multi-turn)
==============================================

فایل اصلی که باید جایگزین شود:
  my_ai/agent.py  ←  همین پوشه: agent.py

router.py فعلی پروژه شما (با _is_continuation) نیاز به تعویض ندارد مگر نسخه قدیمی دارید.
memory.py تغییر API ندارد؛ فقط از recall با query بهتر استفاده می‌شود.

نصب:
  1. از پروژه بکاپ بگیرید
  2. فایل agent.py را کپی کنید روی:
       my_ai/agent.py
  3. تست:
       python -m pytest tests/test_context_aware_inference.py -q
       python -m compileall -q my_ai/agent.py

تغییرات (بدون شکستن API عمومی Agent):
  - _conversation_state: خلاصه موضوع جاری از history
  - recall با query ترکیبی (پیام + موضوع) + فیلتر دانش نامرتبط
  - قوانین MULTI-TURN در SYSTEM prompt
  - یکسان‌سازی chat و stream_chat (ترتیب early-exit و pipeline مشترک _prepare_inference)
  - پشتیبانی attachments در stream_chat
  - پسوند .mq4/.mq5 در attachment text detection

بخش‌هایی که عمداً دست نخورده‌اند:
  - auth, api routes, learning, scheduler, self-update logic
  - signature متدهای chat / stream_chat / plan_project
