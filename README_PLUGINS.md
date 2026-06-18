# Plugin System - Universal Extractor

## كيف تعمل الـ Plugins

ضع أي ملف `.py` في مجلد `plugins/` مع دالة `register(registry)` → يتحمل تلقائياً عند بدء التشغيل.

## أبسط مثال

```python
# plugins/my_decoder.py

def register(registry):
    registry.register_type("my_format", my_decode)

def my_decode(data, output_dir, filename):
    import os
    out = os.path.join(output_dir, f"{filename}.myfmt")
    with open(out, 'wb') as f:
        f.write(data)
    print(f"  My decoder: {filename}")
    return True
```

## إضافة بصمة في signatures.json

```json
"my_format": {
    "magic": ["0xAA 0xBB 0xCC 0xDD"],
    "extension": ".myfmt",
    "engine": "generic"
}
```

## API المتاحة

| الدالة | الشرح |
|--------|-------|
| `registry.register_type(name, func)` | تسجيل دالة جديدة |
| `registry.register_class(cls)` | تسجيل كلاس (يحتاج `extract()` و `identify()`) |
| `registry.list_modes()` | عرض كل المسجلين |

## توقيع الدالة

أي دالة decoder تستقبل:
```python
def decode(data: bytes, output_dir: str, filename: str) -> bool:
```

- `data`: محتوى الملف كـ bytes
- `output_dir`: مسار مجلد المخرجات
- `filename`: اسم الملف الأصلي
- تُرجع `True` عند النجاح

## مثال متقدم

```python
def register(registry):
    registry.register_type("my_custom", decode_my)

def decode_my(data, output_dir, filename):
    import os, struct
    magic = data[:4]
    if magic != b'MY\x00\x00':
        print(f"  Invalid magic")
        return False
    version = struct.unpack_from('<I', data, 4)[0]
    count = struct.unpack_from('<I', data, 8)[0]
    info = f"My Format v{version}, {count} entries"
    base = os.path.join(output_dir, f"{filename}_myfmt")
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, "info.txt"), 'w') as f:
        f.write(info)
    print(f"  My format: {info}")
    return True
```

## ملاحظات

- الـ plugins تتحمل قبل معالجة أي ملف
- إذا فشل تحميل plugin، الأداة تكمل عادي
- كل plugin له namespace منفصل (no conflict)
