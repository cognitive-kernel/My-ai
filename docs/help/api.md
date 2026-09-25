# API

مستندات تعاملی API در `/docs` و `/redoc` قرار دارند.

## یادگیری

```
GET  /learning
GET  /learning/active
GET  /learning/catalog
GET  /learning/status
POST /learning/start
POST /learning/step
POST /learning/learn
POST /learning/practice
POST /learning/{language}/stop
POST /learning/{language}/resume
```

## Scheduler

```
POST /scheduler/start
GET  /scheduler/status
POST /scheduler/stop
GET  /scheduler/resources
```

## کاربران و دسترسی

احراز هویت، نقش‌ها و مجوزهای per-tool در Settings مدیریت می‌شوند. مجوزهای عملیاتی سه سطح دارند:

- `read`
- `write`
- `execute`

ابزارهای حساس مانند GitHub write، امنیت، database، code execution، self-update و self-repair باید طبق permission کاربر و سیاست فرمان اجازه داشته باشند.

## فایل و چندرسانه‌ای

```
GET  /files/roots
GET  /files/list
POST /files/inspect
POST /files/read
POST /files/upload
POST /files/analyze
POST /files/prerequisites
POST /files/generate/docx
POST /files/generate/xlsx
POST /files/generate/pdf
POST /files/generate/pptx
```
