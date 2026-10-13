import openpyxl
import json

FILE = "test_case/soft_matrica.xlsx"

def fmt_percent(v):
    """Превращает 0.833 в '83%'"""
    if v is None:
        return "—"
    if isinstance(v, (int, float)):
        return f"{round(v * 100)}%"
    return str(v)

def read_kollegi_percent(ws):
    """Читает лист Коллеги_% и возвращает список компетенций с процентами."""
    competencies = []
    # Границы блоков (заголовок → последний вопрос)
    blocks = [
        ("Устная и письменная коммуникация", 24, 33),
        ("Выстраивание долгосрочных партнёрских отношений", 39, 50),
        ("Взаимодействие в команде", 54, 70),
        ("Ответственность", 73, 84),
        ("Навыки переговоров в производственных ситуациях", 87, 93),
        ("Проведение и участие во встречах", 96, 101),
        ("Профессиональное обучение и личностное развитие", 104, 110),
        ("Проведение презентаций", 113, 117),
    ]
    
    for name, start, end in blocks:
        questions = []
        for r in range(start + 1, end + 1):
            q_text = ws.cell(row=r, column=1).value
            c = ws.cell(row=r, column=3).value  # Да
            d = ws.cell(row=r, column=4).value  # Нет
            e = ws.cell(row=r, column=5).value  # Не могу
            if q_text:
                questions.append({
                    "question": str(q_text)[:100],
                    "yes": fmt_percent(c),
                    "no": fmt_percent(d),
                    "cant": fmt_percent(e),
                })
        competencies.append({"competency": name, "questions": questions})
    return competencies

def read_soft_skills(ws):
    """Читает Матрица soft skills — итоговые уровни."""
    levels = []
    for r in range(1, 40):
        comp = ws.cell(row=r, column=1).value
        level = ws.cell(row=r, column=12).value
        if comp and level and "УРОВЕНЬ" not in str(comp) and "Индикативный" not in str(comp):
            levels.append({"competency": str(comp), "level": str(level)})
    return levels

def read_textjoin(ws, start_row=1, max_rows=15):
    """Собирает все непустые строки из листа."""
    lines = []
    for r in range(start_row, max_rows):
        v = ws.cell(row=r, column=1).value
        if v:
            lines.append(str(v))
    return "\n".join(lines)

def read_main_info(ws):
    """Читает лист Основные сведения."""
    return {
        "name": ws["B1"].value,
        "position": ws["B2"].value,
        "mentor": ws["B3"].value,
        "manager": ws["B4"].value,
    }

def read_self_assessment(ws):
    """Читает лист Самооценка сотрудника (строка 2 — ответы)."""
    return {
        "projects": ws["C2"].value,
        "satisfaction_score": ws["D2"].value,
        "successes": ws["E2"].value,
        "failures": ws["F2"].value,
        "wants_to_develop": ws["G2"].value,
        "role": ws["H2"].value,
    }

# === Главная логика ===
wb = openpyxl.load_workbook(FILE, data_only=True)

data = {
    "main_info": read_main_info(wb["Основные сведения + цели"]),
    "self_assessment": read_self_assessment(wb["Самооценка сотрудника"]),
    "kollegi_percent": read_kollegi_percent(wb["Коллеги_%"]),
    "soft_skills_final": read_soft_skills(wb["Матрица soft skills"]),
    "comments": read_textjoin(wb["Коллеги_комментарии"]),
    "growth_zones": read_textjoin(wb["Коллеги_похвала и что улучшить"], 5, 9),
    "praise": read_textjoin(wb["Коллеги_похвала и что улучшить"], 9, 15),
}

# Сохраняем в JSON для дальнейшего использования
with open("parsed_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Печатаем для проверки
print("=== ОСНОВНЫЕ СВЕДЕНИЯ ===")
for k, v in data["main_info"].items():
    print(f"  {k}: {v}")

print("\n=== САМООЦЕНКА ===")
for k, v in data["self_assessment"].items():
    print(f"  {k}: {str(v)[:100]}")

print("\n=== ИТОГОВЫЕ УРОВНИ SOFT SKILLS ===")
for item in data["soft_skills_final"]:
    print(f"  {item['competency'][:60]} → {item['level']}")

print("\n=== ПРОЦЕНТЫ КОЛЛЕГ (фрагмент) ===")
for comp in data["kollegi_percent"][:2]:
    print(f"\n  {comp['competency']}:")
    for q in comp["questions"][:3]:
        print(f"    - {q['question'][:60]}... Да={q['yes']}")

print("\n=== КОММЕНТАРИИ КОЛЛЕГ (фрагмент) ===")
print(f"  Длина: {len(data['comments'])} символов")
print(f"  Первые 200: {data['comments'][:200]}...")

print("\n=== ЗОНЫ РОСТА (фрагмент) ===")
print(f"  Первые 200: {data['growth_zones'][:200]}...")

print("\n=== ПОХВАЛА (фрагмент) ===")
print(f"  Первые 200: {data['praise'][:200]}...")

print("\n✅ Данные сохранены в parsed_data.json")