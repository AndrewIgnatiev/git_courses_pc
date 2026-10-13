import json
import docx
from catalog import load_catalog, get_courses_for

# === Читаем все источники ===

with open("parsed_data.json", encoding="utf-8") as f:
    soft = json.load(f)

with open("hard_skills.json", encoding="utf-8") as f:
    hard = json.load(f)

doc = docx.Document("test_case/transcript_BOR.docx")
transcript = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
transcript_lower = transcript.lower()

# === Маппинг уровней и грейдов ===

LEVEL_TO_GRADE = {2: "Junior", 3: "Middle", 4: "Senior", 5: "Lead"}
GRADE_TO_NEXT = {"Junior": "Middle", "Middle": "Senior", "Senior": "Lead", "Lead": "TeamLead"}
POSITION_TO_GRADE = {
    "младший": "Junior", "младший аналитик": "Junior", "младший ба": "Junior",
    "ба": "Middle", "аналитик": "Middle",
    "старший": "Senior", "старший ба": "Senior",
    "ведущий": "Lead", "ведущий ба": "Lead",
}


def get_current_grade(position):
    pos_lower = position.lower()
    for key in ["младший", "старший", "ведущий"]:
        if key in pos_lower:
            return POSITION_TO_GRADE[key]
    return "Junior"


current_grade = get_current_grade(soft['main_info']['position'])
target_grade = GRADE_TO_NEXT.get(current_grade, "Middle")

print(f"=== Грейды ===")
print(f"  Текущий: {current_grade}")
print(f"  Целевой: {target_grade}")

# === Настройки ===

NOT_CRITICAL_HARD = {
    "Участие в Presale",
    "Развитие сотрудников",
    "Найм и оценка уровня кандидатов/сотрудников",
    "UX-паттерны",
    "Основы статистики",
    "Анализ рисков",
}

TRANSCRIPT_MENTIONS = {
    "sql": "SQL",
    "модель данных": "Модель данных",
    "модели данных": "Модель данных",
}


def clean_comp_name(name):
    parts = name.split(" ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        name = parts[1].strip()
    name = name.strip()
    if "(" in name:
        name = name.split("(")[0].strip()
    if name:
        name = name[0].upper() + name[1:].lower()
    return name


# === Отбор компетенций ===

selected = []
seen = set()

# 1. Приоритет: транскрипт
for keyword, comp_name in TRANSCRIPT_MENTIONS.items():
    if keyword in transcript_lower and comp_name not in seen:
        for h in hard:
            if h["competency"] == comp_name:
                target = min(h["max_level"] + 1, 5)
                selected.append({
                    "competency": comp_name, "type": "hard",
                    "current": h["max_level"], "target": target,
                    "reason": "упомянута в БОР как зона роста",
                })
                seen.add(comp_name)
                break

# 2. Hard с max_level ниже целевого
target_level_num = {v: k for k, v in LEVEL_TO_GRADE.items()}.get(target_grade, 3)
for h in hard:
    comp = h["competency"]
    if comp in seen:
        continue
    if h["max_level"] < target_level_num and comp not in NOT_CRITICAL_HARD:
        selected.append({
            "competency": comp, "type": "hard",
            "current": h["max_level"], "target": h["max_level"] + 1,
            "reason": f"ниже целевого ({LEVEL_TO_GRADE.get(h['max_level'])} → {target_grade})",
        })
        seen.add(comp)

# 3. Soft ниже целевого
for s in soft["soft_skills_final"]:
    comp = clean_comp_name(s["competency"])
    if comp in seen:
        continue
    grade_order = ["Junior", "Middle", "Senior", "Lead", "TeamLead"]
    if s["level"] in grade_order and target_grade in grade_order:
        if grade_order.index(s["level"]) < grade_order.index(target_grade):
            selected.append({
                "competency": comp, "type": "soft",
                "current": s["level"], "target": target_grade,
                "reason": f"ниже целевого ({s['level']} → {target_grade})",
            })
            seen.add(comp)

# 4. Финал: 4 hard + 1 soft
hard_selected = [x for x in selected if x["type"] == "hard"]
soft_selected = [x for x in selected if x["type"] == "soft"]
final_selection = (hard_selected[:4] + soft_selected[:1])[:5]

print(f"\n=== Отобрано {len(final_selection)} компетенций для ИПР ===")
for x in final_selection:
    cur_display = LEVEL_TO_GRADE.get(x['current'], x['current']) if x['type'] == 'hard' else x['current']
    tgt_display = LEVEL_TO_GRADE.get(x['target'], x['target']) if x['type'] == 'hard' else x['target']
    print(f"  [{x['type']}] {x['competency']}: {cur_display} → {tgt_display}")
    print(f"      Причина: {x['reason']}")

# === Блок компетенций ===

competencies_block = ""
for i, x in enumerate(final_selection, 1):
    cur_display = LEVEL_TO_GRADE.get(x['current'], x['current']) if x['type'] == 'hard' else x['current']
    tgt_display = LEVEL_TO_GRADE.get(x['target'], x['target']) if x['type'] == 'hard' else x['target']
    competencies_block += f"""
{i}. Компетенция: {x['competency']}
   Тип: {x['type']}
   Текущий уровень: {cur_display}
   Целевой уровень: {tgt_display}
   Почему в ИПР: {x['reason']}
"""

# === Блок курсов с разделением КОРУС/ДАР и ДПО ===

catalog = load_catalog()
print(f"\n=== Каталог загружен: {len(catalog)} компетенций ===")

# Провайдеры, которые считаем «внутренними»
INTERNAL_PROVIDERS = {"КОРУС", "ДАР"}

courses_block = ""
for x in final_selection:
    comp_courses = get_courses_for(catalog, x["competency"], limit=20)

    courses_block += f"\n=== КУРСЫ ПО «{x['competency']}» ===\n"

    if not comp_courses:
        courses_block += "(нет курсов в каталоге)\n"
        print(f"  {x['competency']}: 0 курсов")
        continue

    kor = [c for c in comp_courses if c['provider'] in INTERNAL_PROVIDERS]
    dpo = [c for c in comp_courses if c['provider'] not in INTERNAL_PROVIDERS]

    if kor:
        courses_block += "Внутренние (КОРУС/ДАР):\n"
        for c in kor[:3]:
            courses_block += f"  - {c['name']} ({c['provider']})\n"
    if dpo:
        courses_block += "Внешние ДПО:\n"
        for c in dpo[:3]:
            courses_block += f"  - {c['name']} ({c['provider']})\n"
    if not kor and not dpo:
        courses_block += "(нет подходящих курсов)\n"

    print(f"  {x['competency']}: {len(kor)} КОРУС/ДАР + {len(dpo)} ДПО")

# === Системный промпт ===

SYSTEM_PROMPT = """Ты — HR-ассистент корпоративного университета КОРУС.
Твоя задача — написать текст для Индивидуального плана развития (ИПР).

СЕГОДНЯШНЯЯ ДАТА: 2026-10-13.
Сроки: 6 месяцев → 2027-04-13, 9 месяцев → 2027-07-13, 12 месяцев → 2027-10-13.
Распределяй сроки РАЗНООБРАЗНО.

СПИСОК КОМПЕТЕНЦИЙ ДЛЯ ИПР УЖЕ ОТОБРАН. НЕ добавляй, НЕ удаляй, НЕ переименовывай.

Для каждой компетенции заполни:
- indicator: переход уровня (hard: "3 → 4"; soft: "Junior → Middle")
- methods: методы через запятую
- actions: 3 КОНКРЕТНЫХ действия
- who_helps: Руководитель / Наставник / HR
- deadline: одна из трёх дат

ПРАВИЛА ПО КУРСАМ (ОЧЕНЬ ВАЖНО):
- В блоке "=== КУРСЫ ПО «...» ===" курсы разделены на "Внутренние (КОРУС/ДАР)" и "Внешние ДПО".
- Для каждой компетенции в actions выбери:
  * 1 курс из раздела "Внутренние (КОРУС/ДАР)" — если он есть
  * 1 курс из раздела "Внешние ДПО" — если он есть
- НЕ пиши заглушки типа «(курсы отсутствуют)», «(ДПО-курсы отсутствуют)», 
  «(внутренние курсы отсутствуют)» — ИХ НЕТ. Просто пропусти курс, если его нет.
- НЕ выдумывай названия курсов и провайдеров, которых нет в блоках.
- Если в блоке нет курсов вообще — замени действия на «Практика на проекте» 
  и «Работа с наставником».

ПРАВИЛА ПО ACTIONS:
- Каждое действие СПЕЦИФИЧНО для компетенции.
- РОВНО 3 действия.
- НЕ повторяй одинаковые фразы у разных компетенций.

ПРАВИЛА ПО ЦЕЛЯМ (section_2_goals):
- РОВНО 3 цели.
- Цель 1: переход на целевой грейд. Срок: 12 месяцев (2027-10-13).
- Цель 2: развитие ключевой hard-компетенции. Срок: 6 месяцев (2027-04-13).
- Цель 3: развитие ключевой soft-компетенции. Срок: 9 месяцев (2027-07-13).
- У КАЖДОЙ цели ОБЯЗАТЕЛЬНО есть deadline, и они РАЗНЫЕ.
- Формат цели: {id, goal, smart: {S, M, A, R, T}, comment, deadline}

ФОРМАТ ОТВЕТА — только JSON без markdown:

{
  "employee": {"name": "...", "position": "...", "manager": "...", "mentor": "...", "current_grade": "...", "target_grade": "..."},
  "section_1_results": ["...", "...", "..."],
  "section_2_goals": [
    {"id": 1, "goal": "...", "smart": {"S": "...", "M": "...", "A": "...", "R": "...", "T": "..."}, "comment": "...", "deadline": "2027-10-13"},
    {"id": 2, "goal": "...", "smart": {"S": "...", "M": "...", "A": "...", "R": "...", "T": "..."}, "comment": "...", "deadline": "2027-04-13"},
    {"id": 3, "goal": "...", "smart": {"S": "...", "M": "...", "A": "...", "R": "...", "T": "..."}, "comment": "...", "deadline": "2027-07-13"}
  ],
  "section_3_actions": [
    {
      "competency": "точно как в списке",
      "type": "hard|soft",
      "indicator": "текущий → целевой",
      "methods": "...",
      "actions": ["...", "...", "..."],
      "who_helps": "...",
      "deadline": "2027-XX-XX",
      "goal_id": 1
    }
  ]
}
"""

# === Пользовательский промпт ===

user_prompt = f"""=== ДАННЫЕ СОТРУДНИКА ===
ФИО: {soft['main_info']['name']}
Должность: {soft['main_info']['position']}
Руководитель: {soft['main_info']['manager']}
Наставник: {soft['main_info']['mentor']}
Текущий грейд: {current_grade}
Целевой грейд: {target_grade}

=== САМООЦЕНКА ===
Проекты: {soft['self_assessment']['projects']}
Успехи: {soft['self_assessment']['successes']}
Что не получилось: {soft['self_assessment']['failures']}
Куда хочет развиваться: {soft['self_assessment']['wants_to_develop']}

=== ИТОГОВЫЕ УРОВНИ SOFT SKILLS ===
"""

for item in soft["soft_skills_final"]:
    user_prompt += f"- {clean_comp_name(item['competency'])}: {item['level']}\n"

user_prompt += "\n=== HARD SKILLS ===\n"
for h in hard:
    user_prompt += f"- [{h['max_level']}] {h['competency']} ({LEVEL_TO_GRADE.get(h['max_level'], '?')})\n"

user_prompt += f"""
=== ЗОНЫ РОСТА (коллеги) ===
{soft['growth_zones']}

=== ПОХВАЛА (коллеги) ===
{soft['praise']}

=== ТРАНСКРИПТ БОР ===
{transcript}

=== КОМПЕТЕНЦИИ ДЛЯ ИПР (уже отобраны Python) ===
{competencies_block}
{courses_block}

=== ЗАДАЧА ===
Сформируй черновик ИПР в JSON. Используй РОВНО те компетенции, что в списке выше.
Курсы бери из блоков "Внутренние" и "Внешние ДПО". Заглушки НЕ пиши.
"""

# Сохраняем

with open("system_prompt.txt", "w", encoding="utf-8") as f:
    f.write(SYSTEM_PROMPT)

with open("user_prompt.txt", "w", encoding="utf-8") as f:
    f.write(user_prompt)

print(f"\n✅ Системный промпт: {len(SYSTEM_PROMPT)} символов")
print(f"✅ Пользовательский промпт: {len(user_prompt)} символов")
print(f"✅ Оценка токенов: ~{len(user_prompt) // 3}")
print("\n📄 Сохранено: system_prompt.txt, user_prompt.txt")