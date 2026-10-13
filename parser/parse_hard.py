import openpyxl
import json

FILE = "test_case/hard_skills_matrix.xlsx"
wb = openpyxl.load_workbook(FILE, data_only=True)
ws = wb["Чеклист"]

# Собираем все строки в список
rows = []
for r in range(1, ws.max_row + 1):
    rows.append({
        "r": r,
        "a": ws.cell(row=r, column=1).value,
        "b": ws.cell(row=r, column=2).value,
        "c": ws.cell(row=r, column=3).value,
        "d": ws.cell(row=r, column=4).value,
    })

def next_significant(idx):
    """Следующая строка, у которой есть текст в C или число в B."""
    for j in range(idx + 1, len(rows)):
        row = rows[j]
        if row["c"] is not None or (isinstance(row["b"], int) and row["b"] in (2, 3, 4, 5)):
            return row
    return None

SKIP_PREFIXES = ("Другое:", "Зоны роста:", "!После", "Количество респондентов", "% - от общего")
SKIP_EXACT = ("Сотрудник", "Я", "Junior", "Middle", "Senior", "Lead", "TeamLead",
              "Сбор и анализ требований", "Проектирование и разработка", "Тестирование",
              "Анализ данных", "Работа с документами", "Макетирование и основы UI/UX",
              "Участие в Presale", "Управление ожиданиями и изменениями",
              "Управление проектом", "HR и развитие сотрудников", "Презентации и обучение")

# Но эти же названия могут быть и компетенциями! Поэтому просто не пропускаем их,
# а смотрим на контекст.

competencies = []
current_category = None
current_competency = None
current_items = []

for i, row in enumerate(rows):
    b, c, d = row["b"], row["c"], row["d"]

    # Подпункт: B = число 2-5 и C = описание
    if isinstance(b, int) and b in (2, 3, 4, 5) and c:
        current_items.append({
            "level": b,
            "description": str(c).strip()[:200],
            "checked": bool(d) if d is not None else False,
        })
        continue

    # Название: C заполнено, B пусто
    if c and b is None:
        c_str = str(c).strip()

        # Пропускаем служебное
        if any(c_str.startswith(p) for p in SKIP_PREFIXES):
            continue
        if c_str in ("Сотрудник", "Я"):
            continue
        if len(c_str) < 2:
            continue

        # Смотрим, что идёт следом
        nxt = next_significant(i)
        if nxt is None:
            continue

        next_has_level = isinstance(nxt["b"], int) and nxt["b"] in (2, 3, 4, 5)

        if next_has_level:
            # Следующая строка — подпункт → это КОМПЕТЕНЦИЯ
            if current_competency and current_items:
                competencies.append({
                    "category": current_category,
                    "competency": current_competency,
                    "items": current_items,
                })
            # Если категория ещё не задана или предыдущая компетенция завершена
            current_competency = c_str
            current_items = []
        else:
            # Следующая — тоже название → это КАТЕГОРИЯ
            # Но только если перед ней не идёт уже набранная компетенция
            if current_competency and current_items:
                # Завершаем предыдущую
                competencies.append({
                    "category": current_category,
                    "competency": current_competency,
                    "items": current_items,
                })
                current_competency = None
                current_items = []

            # Если это известное название категории — обновляем
            if c_str in SKIP_EXACT:
                current_category = c_str
            else:
                # Иначе — тоже категория (но, возможно, неизвестная)
                current_category = c_str

# Последняя
if current_competency and current_items:
    competencies.append({
        "category": current_category,
        "competency": current_competency,
        "items": current_items,
    })

# Считаем уровни
result = []
for comp in competencies:
    achieved = [item["level"] for item in comp["items"] if item["checked"]]
    max_level = max(achieved) if achieved else 0
    result.append({
        "category": comp["category"],
        "competency": comp["competency"],
        "max_level": max_level,
        "achieved_levels": sorted(achieved),
    })

with open("hard_skills.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"=== Всего компетенций: {len(result)} ===\n")
for r in result:
    print(f"[{r['max_level']}] {r['category']} → {r['competency']}")