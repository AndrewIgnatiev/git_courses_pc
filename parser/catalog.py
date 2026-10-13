"""Парсер каталога курсов через json5."""
import json
import re
from pathlib import Path

try:
    import json5
except ImportError:
    print("WARNING: json5 не установлен. Выполни: pip install json5")
    json5 = None


def load_catalog(path=None):
    """Возвращает словарь {competency: [{name, provider}, ...]}."""
    
    if path is None:
        candidates = [
            Path(__file__).parent.parent / "catalog-courses.js",
            Path(__file__).parent / "catalog-courses.js",
        ]
        for c in candidates:
            if c.exists():
                path = c
                break
    
    if not path or not Path(path).exists():
        print(f"WARNING: catalog-courses.js не найден")
        return {}
    
    with open(path, encoding="utf-8") as f:
        content = f.read()
    
    # Убираем только обёртку window.KORUS_COURSES = ...
    content = re.sub(r'window\.KORUS_COURSES\s*=', '', content)
    content = content.rstrip(";\n \t")
    
    # Парсим через json5 (НЕ трогаем комментарии — они ломают URL)
    if json5 is None:
        return {}
    
    try:
        data = json5.loads(content)
    except Exception as e:
        print(f"WARNING: Ошибка парсинга каталога: {e}")
        return {}
    
    catalog = {}
    
    # 1. Из data
    for category, comps in data.get("data", {}).items():
        if not isinstance(comps, dict):
            continue
        for comp_name, sources in comps.items():
            if not isinstance(sources, dict):
                continue
            for src_key, provider_default in (("korpus", "КОРУС"), ("dar", "ДАР"), ("external", None)):
                for c in sources.get(src_key, []) or []:
                    if not isinstance(c, dict):
                        continue
                    provider = provider_default or c.get("provider") or "Внешний"
                    name = c.get("name", "").strip()
                    if not name:
                        continue
                    catalog.setdefault(comp_name, []).append({
                        "name": name,
                        "provider": provider,
                    })
    
    # 2. Из DPO_RAW
    for row in data.get("DPO_RAW", []):
        if not isinstance(row, list) or len(row) < 7:
            continue
        name = row[0].strip() if isinstance(row[0], str) else ""
        provider = row[2].strip() if isinstance(row[2], str) else ""
        comps = row[6] if isinstance(row[6], str) else ""
        for comp in comps.split("|"):
            comp = comp.strip()
            if comp and name:
                catalog.setdefault(comp, []).append({
                    "name": name,
                    "provider": provider,
                })
    
    return catalog


def get_courses_for(catalog, comp_name, limit=5):
    if comp_name in catalog:
        return catalog[comp_name][:limit]
    
    comp_lower = comp_name.lower()
    for key, courses in catalog.items():
        if comp_lower in key.lower() or key.lower() in comp_lower:
            return courses[:limit]
    
    return []


if __name__ == "__main__":
    cat = load_catalog()
    print(f"Загружено компетенций: {len(cat)}\n")
    for name in list(cat.keys())[:15]:
        print(f"  {name}: {len(cat[name])} курсов")
        for c in cat[name][:2]:
            print(f"     - {c['name']} ({c['provider']})")