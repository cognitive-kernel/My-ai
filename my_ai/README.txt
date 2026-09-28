My-AI inference fix v2 — مسیر دقیق فایل‌ها
==========================================

1) my_ai/agent.py
   منبع در این بسته:  agent.py
   مقصد روی پروژه:    my_ai\agent.py

2) my_ai/domain/router.py
   منبع در این بسته:  domain/router.py
   مقصد روی پروژه:    my_ai\domain\router.py

3) my_ai/router.py  (فقط اگر خراب شده)
   منبع: router_FACCADE.py
   مقصد: my_ai\router.py
   این فایل باید با خط زیر شروع شود:
   """Public compatibility facade for the application-layer router."""

تغییرات v2:
- جلوگیری از اشتباه database_import برای ساخت/دانلود اندیکاتور
- تشخیص بهتر continuation (لینک دانلود، از کجا ذخیره، همون اندیکاتور)
- ذخیره واقعی فایل .mq4 در data/files/indicators وقتی کاربر فایل/لینک بخواهد
- حذف import بلااستفاده build_router_service

بعد از کپی:
  python -m compileall -q my_ai/agent.py my_ai/domain/router.py
  uvicorn my_ai.api:app --host 127.0.0.1 --port 8000
