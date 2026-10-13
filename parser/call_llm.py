import json
import openai

# ============================================================
# Конфигурация
# ============================================================
LM_STUDIO_URL = "http://localhost:1234/v1"
MODEL_NAME = "qwen2.5-7b-instruct"

client = openai.OpenAI(
    base_url=LM_STUDIO_URL,
    api_key="lm-studio",
    timeout=1800.0,
    max_retries=0
)

# ============================================================
# Утилиты
# ============================================================
def clean_json(raw):
    """Убирает markdown-обёртку ```json ... ```."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return cleaned


def call_llm(system_file, user_file, label):
    """Отправляет запрос в LM Studio, возвращает распарсенный JSON."""
    with open(system_file, encoding="utf-8") as f:
        system_prompt = f.read()
    with open(user_file, encoding="utf-8") as f:
        user_prompt = f.read()

    print(f"\n🚀 Запрос [{label}]")
    print(f"   Системный: {len(system_prompt)} символов")
    print(f"   Пользовательский: {len(user_prompt)} символов")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=4000,
        top_p=0.9,
    )

    raw = response.choices[0].message.content
    print(f"   Ответ: {len(raw)} символов")

    with open(f"raw_{label}.txt", "w", encoding="utf-8") as f:
        f.write(raw)

    cleaned = clean_json(raw)
    return json.loads(cleaned)


# ============================================================
# Пост-обработка
# ============================================================
def find_grade_goal_id(goals):
    """Находит id цели про переход на грейд. Создаёт, если нет."""
    for g in goals:
        text = (g.get("goal", "") + " " + g.get("comment", "")).lower()
        if any(kw in text for kw in ["грейд", "middle", "переход", "аттестац"]):
            return g.get("id")
    # Если LLM забыла — добавляем
    new_id = max([g.get("id", 0) for g in goals] + [0]) + 1
    goals.append({
        "id": new_id,
        "goal": "Переход на грейд Middle",
        "smart": {
            "S": "Выполнять задачи уровня Middle и пройти аттестацию",
            "M": "Получить положительную оценку руководителя и пройти аттестацию",
            "A": "Текущий грейд Junior, есть поддержка руководителя и наставника",
            "R": "Для карьерного роста и расширения зоны ответственности",
            "T": "12 месяцев"
        },
        "comment": "Основная цель на год — переход на следующий грейд.",
        "deadline": "2027-10-12"
    })
    print(f"⚠️  Добавлена недостающая цель: Переход на грейд Middle (id={new_id})")
    return new_id


def find_communication_goal_id(goals, exclude_id=None):
    """Находит id цели про коммуникацию."""
    priorities = [
        ["переговор"],
        ["встреч"],
        ["коммуникац"],
        ["эмоциональн", "устойчив"],
    ]
    for keywords in priorities:
        for g in goals:
            if g.get("id") == exclude_id:
                continue
            text = (g.get("goal", "") + " " + g.get("comment", "")).lower()
            if any(kw in text for kw in keywords):
                return g.get("id")
    for g in goals:
        if g.get("id") != exclude_id:
            return g.get("id")
    return None


def ensure_three_goals(goals, grade_goal_id):
    """Гарантирует 3 цели: грейд + hard + soft."""
    if len(goals) >= 3:
        return
    # Ищем цель про софт
    has_soft_goal = any(
    "встреч" in (g.get("goal", "") + g.get("comment", "")).lower()
    or "презентац" in (g.get("goal", "") + g.get("comment", "")).lower()
    for g in goals
)
    if not has_soft_goal:
        new_id = max([g.get("id", 0) for g in goals] + [0]) + 1
        goals.append({
            "id": new_id,
            "goal": "Развитие навыков проведения встреч",
            "smart": {
                "S": "Пройти тренинг по мастерству презентаций и модерации встреч",
                "M": "Провести не менее 3 встреч с заказчиком с положительной ОС",
                "A": "Есть поддержка наставника и HR, доступ к тренингам КОРУС",
                "R": "Критично для роли Middle — управление коммуникацией",
                "T": "9 месяцев"
            },
            "comment": "Soft-компетенция ниже целевого грейда. Нужна для Middle.",
            "deadline": "2027-07-12"
        })
        print(f"⚠️  Добавлена недостающая цель про софт (id={new_id})")


def clean_action_stubs(action):
    """Убирает заглушки в actions и нормализует до 3-4 действий."""
    acts = action.get("actions", [])
    # Убираем заглушки
    cleaned = [
        a for a in acts
        if not any(stub in a.lower() for stub in ["отсутству", "не найдено", "не найдены"])
    ]
    # Если меньше 3 — добавляем практику
    while len(cleaned) < 3:
        cleaned.append("Практика на проекте")
    # Ограничиваем до 4
    action["actions"] = cleaned[:4]
    return action


# ============================================================
# Запрос 1: Результаты БОР + SMART-цели
# ============================================================
print("=" * 50)
try:
    result_1 = call_llm("system_prompt_1.txt", "user_prompt_1.txt", "part1")
    print(f"   ✅ section_1_results: {len(result_1.get('section_1_results', []))} пунктов")
    print(f"   ✅ section_2_goals: {len(result_1.get('section_2_goals', []))} целей")
except json.JSONDecodeError as e:
    print(f"   ❌ JSON невалидный: {e}")
    raise

# ============================================================
# Запрос 2: Развивающие действия
# ============================================================
print("=" * 50)
try:
    result_2 = call_llm("system_prompt_2.txt", "user_prompt_2.txt", "part2")
    print(f"   ✅ section_3_actions: {len(result_2.get('section_3_actions', []))} компетенций")
except json.JSONDecodeError as e:
    print(f"   ❌ JSON невалидный: {e}")
    raise

# ============================================================
# Пост-обработка
# ============================================================
print("\n🔧 Пост-обработка:")

# --- Цели ---
goals = result_1.get("section_2_goals", [])
grade_goal_id = find_grade_goal_id(goals)
ensure_three_goals(goals, grade_goal_id)
comm_goal_id = find_communication_goal_id(goals, exclude_id=grade_goal_id) or grade_goal_id

# Разные дедлайны для целей
goals_deadlines = ["2027-10-12", "2027-04-12", "2027-07-12"]
for i, g in enumerate(goals):
    if not g.get("deadline") or g.get("deadline") == "—":
        g["deadline"] = goals_deadlines[i % len(goals_deadlines)]

print(f"   Целей: {len(goals)}")
print(f"   goal_id для hard = {grade_goal_id}")
print(f"   goal_id для soft = {comm_goal_id}")

# --- Действия ---
actions_list = result_2.get("section_3_actions", [])

# Чистим заглушки
for a in actions_list:
    clean_action_stubs(a)

# Разные дедлайны для actions
deadlines_pool = ["2027-04-12", "2027-07-12", "2027-10-12"]
for i, a in enumerate(actions_list):
    a["goal_id"] = grade_goal_id if a.get("type") == "hard" else comm_goal_id
    a["deadline"] = deadlines_pool[i % len(deadlines_pool)]

print(f"   Дедлайны actions: {[a['deadline'] for a in actions_list]}")
print(f"   Цели:")
for g in goals:
    print(f"     id={g.get('id')}: {g.get('goal')} → {g.get('deadline')}")

# ============================================================
# Склейка финального JSON
# ============================================================
final = {
    "employee": {
        "name": "Ахмедова Дарья",
        "position": "Младший аналитик",
        "manager": "Бизякина Наталья",
        "mentor": "Самарцева София",
        "current_grade": "Junior",
        "target_grade": "Middle"
    },
    "section_1_results": result_1.get("section_1_results", []),
    "section_2_goals": goals,
    "section_3_actions": actions_list
}

with open("ipr_draft.json", "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 50)
print("✅ ИТОГОВЫЙ JSON собран: ipr_draft.json")
print(f"   section_1_results: {len(final['section_1_results'])} пунктов")
print(f"   section_2_goals: {len(final['section_2_goals'])} целей")
print(f"   section_3_actions: {len(final['section_3_actions'])} компетенций")
print("\n=== Полный JSON ===")
print(json.dumps(final, ensure_ascii=False, indent=2))