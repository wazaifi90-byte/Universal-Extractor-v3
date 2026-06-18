# Universal Extractor v3.0

**منصة استخراج متعددة المحركات** — بنيتَ الآلة، المستخدم يشغّلها.

**102+ بصمة | 65+ مفكك | PWA | AI Fingerprint | XOR Scraper | Parallel Processing | Virtual Sandbox | Crypto Discovery**

---

## 📦 Installation — أنت تثبّت المنصة

```bash
pip install .
# أو
pip install -r requirements.txt
```

بعد التثبيت، شغّل لوحة التحكم:

```bash
python main.py --web
# أو
universal-extractor --web
```

افتح `http://127.0.0.1:5000` في المتصفح.

> **💡 نصيحة:** اضغط على ⋮ ← **تثبيت التطبيق** في شريط المتصفح لتحويل الموقع إلى تطبيق مستقل (PWA) يظهر في قائمة تطبيقات جهازك.

---

## 🔧 Usage — المستخدم يستخرج الملفات

| الخطوة | الإجراء |
|--------|---------|
| 1 | افتح التطبيق (أو زر `http://127.0.0.1:5000`) |
| 2 | اسحب وأفلت (Drag & Drop) ملفاً مضغوطاً |
| 3 | اضغط **استخراج** ← البرنامج يقوم بالباقي |
| 4 | حمّل النتائج أو افتح المجلد مباشرة |

### أمثلة سريعة (CLI)

```bash
python main.py                     # watch mode — مراقبة inputs/
python main.py --once --parallel   # معالجة كل الملفات دفعة
python main.py --single game.pak   # استخراج ملف واحد
python main.py --info              # عرض 102+ بصمة و 65+ مفكك
```

---

## 🧩 PWA — تطبيق مستقل على سطح المكتب

- الواجهة هي **حاوية** (Container) يثبتها المستخدم.
- الاستخراج هو **الوظيفة** (Function) التي يؤديها التطبيق.
- بمجرد التثبيت، يصبح المشروع تطبيقاً مستقلاً في قائمة التطبيقات.

### المميزات:

| الميزة | الوصف |
|--------|-------|
| **التثبيت** | ⋮ ← تثبيت التطبيق — يصبح App مستقلاً |
| **Dark/Light** | وضع ليلي ونهاري |
| **Service Worker** | تخزين مؤقت للسرعة |
| **Share Target** | استقبال ملفات من النظام مباشرة |
| **أيقونات** | 192×192 و 512×512 |

---

## 🌐 Web Dashboard — لوحة التحكم

```bash
python main.py --web
python main.py --web --port 8080
python main.py --web --host 0.0.0.0
```

| التبويب | الوظيفة |
|---------|---------|
| **التشفير** | كشف XOR تلقائي بتحليل الأنتروبي والارتباط الذاتي |
| **الإضافات** | متجر plugins — تثبيت/إلغاء تثبيت بنقرة واحدة |
| **الملفات** | رفع وسحب وإفلات مع معالجة فورية |
| **البصمات** | 102+ بصمة مدعومة |
| **المفككات** | 65+ مفكك مسجل |
| **السجلات** | سجل تشغيل كامل |
| **الإعدادات** | تحكم كامل بكل الإعدادات |
| **التحديثات** | فحص وجود إصدار أحدث تلقائياً |

### API Endpoints

| المسار | الطريقة | الوظيفة |
|--------|---------|---------|
| `/api/status` | GET | إحصائيات حية |
| `/api/signatures` | GET | كل البصمات |
| `/api/decoders` | GET | كل المفككات |
| `/api/logs` | GET | آخر السجلات |
| `/api/process` | POST | معالجة ملفات محددة |
| `/api/config` | GET/PUT | قراءة/تعديل الإعدادات |
| `/api/errors` | GET | الملفات الفاشلة |
| `/api/upload` | POST | رفع ملف (مع أو بدون معالجة) |
| `/api/download/<file>` | GET | تحميل ملف مخرج |
| `/api/watch` | POST | تشغيل/إيقاف المراقبة |
| `/api/ai-analyze` | POST | تحليل بالذكاء الاصطناعي |
| `/api/crypto-analyze` | POST | كشف التشفير (جديد) |
| `/api/virtual/list` | POST | معاينة الملفات بدون فك (جديد) |
| `/api/plugins` | GET | سجل الإضافات (جديد) |
| `/api/stats` | GET | إحصائيات المعالجة |

---

## CLI Commands (سطر الأوامر)

| الأمر | الوظيفة |
|-------|---------|
| `python main.py` | مراقبة مستمرة لـ inputs/ |
| `python main.py --once` | معالجة لمرة واحدة |
| `python main.py --once --parallel` | معالجة متوازية (ThreadPool) |
| `python main.py --single FILE` | فك ملف محدد |
| `python main.py --preview FILE` | معاينة رأس الملف |
| `python main.py --info` | عرض كل الفورمات المدعومة |
| `python main.py --setup` | إنشاء المجلدات |
| `python main.py --web` | تشغيل واجهة الويب |
| `python main.py --fingerprint` | عرض مجاميع الفورمات |
| `python main.py --fingerprint FILE` | تحليل ذكي لملف |
| `python main.py --ai-classify FILE` | تصنيف بالذكاء الاصطناعي |
| `python main.py --ai-train DIR` | تدريب AI على عينات |
| `python main.py --ai-info` | معلومات النموذج المدرب |
| `python main.py --scrape-keys FILE.exe` | استخراج XOR من exe |
| `python main.py --scrape-dir DIR` | مسح مجلد كامل |
| `python main.py --no-hash` | تعطيل التجزئة |
| `python main.py --no-validate` | تعطيل التحقق |
| `python main.py --lang ar` | تشغيل بالعربية |
| `python main.py --lang en` | تشغيل بالإنجليزية |
| `python main.py --languages` | عرض اللغات المتاحة |
| `python main.py --stats` | إحصائيات المعالجة |

---

## الميزات الجديدة (v3.0)

### 1. كشف التشفير التلقائي (Auto-Crypto Discovery)

يكشف مفاتيح XOR تلقائياً باستخدام الارتباط الذاتي (Autocorrelation) وتحليل NumPy:

```bash
# عبر API
POST /api/crypto-analyze
# أو من خلال واجهة الويب (تبويب التشفير)
```

- يعثر على طول المفتاح عبر مقارنة المصفوفات المزاحة
- يستنتج المفتاح عبر تحليل البايتات الأكثر تكراراً
- يحسب الأنتروبي لتقييم درجة التشفير

### 2. Virtual Sandbox (معاينة بدون فك)

تصفح محتويات الأرشيفات الضخمة دون فك ضغطها على القرص:

```bash
POST /api/virtual/list
```

- UnityFS و UnrealPak مدعومان
- معاينة Base64 فورية في المتصفح
- صفر استهلاك للقرص الصلب

### 3. Conflict Manager

إدارة تلقائية للصراعات عند وجود أسماء مكررة:

- Rename: إضافة رقم تلقائي (file_1.png, file_2.png)
- Overwrite: استبدال الملف القديم
- Skip: تخطي الملف المكرر

### 4. PWA كاملة

```json
// manifest.json
{
  "display": "standalone",
  "share_target": { "action": "/api/upload", "method": "POST" }
}
```

- تثبيت كتطبيق سطح مكتب
- Service Worker للتخزين المؤقت
- شعار مخصص (ue_logo_512.png)
- Dark/Light mode

### 5. CI/CD (GitHub Actions)

اختبار تلقائي لكل commit:

- تشغيل pytest على Python 3.9/3.10/3.11
- التحقق من تحميل جميع المفككات
- التحقق من سلامة نموذج AI
- Lint باستخدام flake8

### 6. Docker

```bash
docker build -t universal-extractor .
docker run -p 5000:5000 universal-extractor
```

---

## Project Structure

```
Universal_Extractor/
├── main.py                 # CLI entry point
├── config.json             # إعدادات التشغيل
├── signatures.json         # 84 نمط توقيع
├── registry.py             # 65+ مفكك مسجل
├── requirements.txt        # الاعتماديات
├── tools_updater.py        # مدير التحديثات
├── fingerprints.json       # قاعدة بصمات AI
├── plugins_registry.json   # سجل الإضافات (جديد)
├── Dockerfile              # حاوية Docker (جديد)
├── .github/workflows/      # CI/CD (جديد)
│   └── main.yml
│
├── core/                   # النواة
│   ├── scanner.py          # كشف التوقيعات
│   ├── processor.py        # سلسلة الفك + تحقق
│   ├── validator.py        # Hash + فحص التلف
│   ├── preview.py          # معاينة + Hex dump
│   ├── container.py        # فك متداخل (carving ذكي)
│   ├── plugin_loader.py    # تحميل plugins
│   ├── key_scraper.py      # استخراج XOR
│   ├── logger.py           # تسجيل
│   ├── i18n.py             # تدويل (عربي/English)
│   ├── database.py         # SQLite إحصائيات
│   ├── progress.py         # شريط تقدم
│   ├── error_assistant.py  # مساعد أخطاء ذكي
│   ├── virtual_fs.py       # Virtual Sandbox (جديد)
│   ├── crypto_discovery.py # كشف التشفير التلقائي (جديد)
│   └── conflict_manager.py # إدارة الصراعات (جديد)
│
├── decoders/               # جميع المفككات (21+)
│   ├── deflate.py, lz4_decoder.py, xor_decoder.py
│   ├── lzss.py, yaz0.py, bres_decoder.py
│   ├── unity.py, unreal_pak.py, cocos2dx.py
│   ├── gameloft.py, konami.py
│   ├── image_helper.py, etc1.py, audio_utils.py
│   ├── godot.py, psarc.py, struct_parser.py
│   ├── cryengine.py, source_engine.py
│   ├── renpy.py, rpgmaker.py
│
├── ai/                     # الذكاء الاصطناعي
│   ├── fingerprint.py     # تحليل + كشف ذكي
│   └── train_ai.py        # تدريب + تصنيف
│
├── web_app/                # Web Dashboard + PWA
│   ├── app.py             # Flask API (15+ endpoint)
│   ├── templates/
│   │   └── index.html     # واجهة عربية/إنجليزية
│   └── static/
│       ├── manifest.json   # PWA manifest
│       ├── sw.js           # Service Worker
│       ├── ue-logo-512.png # شعار المشروع
│       ├── favicon.png     # أيقونة
│       └── icons/          # أيقونات PWA
│
├── engines/                # قواعد المحركات
├── plugins/                # إضافات (تحميل تلقائي)
├── lang/                   # en.json + ar.json
├── tests/                  # 15+ اختبار وحدة
│
├── inputs/                 # ضع ملفاتك هنا
├── outputs/                # المخرجات
├── logs/                   # سجلات التشغيل
└── errors/                 # الملفات الفاشلة
```

---

## Run Tests

```bash
python tests/test_basic.py
# 15 tests, 0 failed
```

---

## config.json

```json
{
  "active_mode": "auto",
  "paths": {
    "input_dir": "inputs",
    "output_dir": "outputs",
    "log_dir": "logs",
    "error_dir": "errors"
  },
  "settings": {
    "scan_interval_seconds": 2,
    "auto_delete_input": false,
    "process_subdirectories": true,
    "extract_nested": true,
    "xor_key": null,
    "stream_chunk_size": 1048576,
    "race_wait_seconds": 2,
    "enable_hashing": true,
    "enable_validation": true,
    "parallel": false,
    "max_workers": 4,
    "conflict_mode": "rename"
  },
  "language": "en",
  "auto_search_on_error": true,
  "search_sites": [
    "stackoverflow.com", "github.com", "reddit.com",
    "gamedev.net", "zenhax.com", "forum.xentax.com"
  ]
}
```

---

## Languages

عربي / English — اختيار اللغة في `config.json` ← `language` أو من Web Dashboard.

---

## Requirements

```
Pillow>=11.0.0       # معالجة الصور
python-lz4>=4.4.0    # فك LZ4
xxhash>=3.5.0        # تجزئة سريعة (fallback: MD5)
rich>=13.0.0         # واجهة CLI ملونة (اختياري)
flask>=3.0.0         # Web Dashboard (اختياري)
numpy>=1.24.0        # تسريع AI + كشف التشفير (اختياري)
```

---

## License

MIT
