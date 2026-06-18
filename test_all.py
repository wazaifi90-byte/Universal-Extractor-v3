"""
Comprehensive test for Universal Extractor v3.0
Tests all new features added in this session
"""
import sys, os, json, tempfile
sys.path.insert(0, '.')

results = {'pass': 0, 'fail': 0, 'errors': []}

def check(name, ok, msg=''):
    if ok:
        results['pass'] += 1
    else:
        results['fail'] += 1
        results['errors'].append(f'{name}: {msg}')
    print(f'  {"OK" if ok else "FAIL"} {name}')

print("=== Universal Extractor v3.0 Comprehensive Test ===\n")

# 1. i18n
print("[i18n]")
from core.i18n import load_language, t, available_languages
check('load EN', load_language('en'))
check('load AR', load_language('ar'))
check('t() returns string', len(t('app_name')) > 0)
langs = available_languages()
check('2+ languages', len(langs) >= 2)

# 2. Database
print("\n[Database]")
from core.database import init_db, log_operation, get_stats
init_db()
check('extractor.db exists', os.path.exists('extractor.db'))
log_operation('test.bin', 'deflate', 100, 'success', duration_ms=50)
s = get_stats()
check('stats total >= 1', s['total'] >= 1)
check('stats success >= 1', s['success'] >= 1)

# 3. Decoder registration
print("\n[Decoder Registration]")
from registry import registry
modes = registry.list_modes()
for d in ['cryengine', 'source_vpk', 'renpy_rpa', 'rgss']:
    check(f'  registered: {d}', d in modes)

# 4. Signature entries
print("\n[Signatures]")
with open('signatures.json') as f:
    sigs = json.load(f)
for s in ['cryengine', 'cryengine_chunk', 'source_vpk', 'source_bsp', 'renpy_rpa', 'rgss', 'rgd']:
    check(f'signature: {s}', s in sigs)

# 5. AI SmartClassifier
print("\n[AI SmartClassifier]")
from ai.fingerprint import SmartClassifier
clf = SmartClassifier()
check('classifier created', True)
clf.train('test_png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
label, conf = clf.classify(b'\x89PNG\r\n\x1a\n' + b'\x01' * 50)
check('classify returns label', isinstance(label, str))
check('confidence is float', isinstance(conf, float))

# 6. Container carving
print("\n[Container Carving]")
from core.container import quick_carve
td = tempfile.mkdtemp()
test_data = (
    b'\x89PNG\r\n\x1a\n' + b'\x00' * 100 +
    b'RIFF' + b'\x00' * 20 +
    b'PK\x03\x04' + b'\x01' * 50
)
quick_carve(test_data, td, 'test_carve')
carved = os.listdir(td)
check('carved at least 1 file', len(carved) > 0)

# 7. Progress
print("\n[Progress]")
from core.progress import ProgressTracker
pt = ProgressTracker(total=100, desc='test')
check('progress created', True)
pt.update(50)
check('progress update 50', pt.current == 50)
pt.finish()
check('progress finish', pt.current == pt.total)

# 8. Error Assistant
print("\n[Error Assistant]")
from core.error_assistant import ErrorAssistant
ea = ErrorAssistant()
url = ea.get_search_url('LZ4 decompression failed', 'unity_bundle')
check('generates google URL', 'google.com/search' in url)

# 9. PWA
print("\n[PWA]")
pwa_files = [
    'web_app/static/manifest.json',
    'web_app/static/sw.js',
    'web_app/static/favicon.png',
    'web_app/static/icons/icon-192x192.png',
    'web_app/static/icons/icon-512x512.png',
]
for f in pwa_files:
    check(f'PWA file: {os.path.basename(f)}', os.path.exists(f))

# 10. pyproject.toml
print("\n[Build System]")
check('pyproject.toml', os.path.exists('pyproject.toml'))
check('setup.py not needed', not os.path.exists('setup.py'))

print(f'\n{"="*40}')
print(f'Results: {results["pass"]} passed, {results["fail"]} failed, {results["pass"]+results["fail"]} total')
if results['errors']:
    print('Errors:')
    for e in results['errors']:
        print(f'  - {e}')
