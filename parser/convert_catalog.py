import json
import json5
from pathlib import Path

# Папка, где лежит этот скрипт (parser/)
SCRIPT_DIR = Path(__file__).parent.resolve()
# Корень проекта — на уровень выше
PROJECT_ROOT = SCRIPT_DIR.parent

JS_FILE = PROJECT_ROOT / "catalog-courses.js"
JSON_FILE = SCRIPT_DIR / "catalog-courses.json"

print(f"📂 Скрипт: {SCRIPT_DIR}")
print(f"📂 Корень проекта: {PROJECT_ROOT}")
print(f"📂 Ищу файл: {JS_FILE}")
print(f"   Существует: {JS_FILE.exists()}")

print(f"📖 Читаем {JS_FILE}...")

with open(JS_FILE, encoding="utf-8") as f:
    content = f.read()

# Находим начало JSON-объекта (первая {)
start = content.find("{")
# Находим конец (последняя })
end = content.rfind("}")

if start == -1 or end == -1:
    print("❌ Не удалось найти JSON-объект в файле")
    raise SystemExit(1)

json_str = content[start:end+1]

print(f"   Извлечено {len(json_str)} символов")

try:
    data = json5.loads(json_str)
    print("✅ Парсинг успешен")
except Exception as e:
    print(f"❌ Ошибка парсинга: {e}")
    raise SystemExit(1)

# Сохраняем
with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Статистика
categories = list(data.get("data", {}).keys())
dpo_count = len(data.get("DPO_RAW", []))

print(f"\n📊 Статистика:")
print(f"   Категорий: {len(categories)}")
print(f"   ДПО-курсов: {dpo_count}")
print(f"   Всего компетенций в data: {sum(len(data['data'][c]) for c in categories)}")
print(f"\n📄 Сохранено: {JSON_FILE}")