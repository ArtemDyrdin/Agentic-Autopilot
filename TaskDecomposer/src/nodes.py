from utilities import *
from state import ArchitectState

MAX_QA_RETRIES = 2


def analyze_document(state: ArchitectState, llm) -> dict:
    print("\n🔍 Анализирую документ...")
    prompt = load_prompt("analyze_document")
    response = llm.invoke(prompt + "\n\n" + state["raw_document"])
    semantic_map = safe_json_parse(response.content)
    print_section("📋 Семантическая карта", semantic_map)
    return {"semantic_map": semantic_map}


def handle_clarifying_questions(state: ArchitectState, llm) -> dict:
    open_questions = state["semantic_map"].get("open_questions", [])
    if not open_questions:
        print("\n✅ Открытых вопросов нет, продолжаем...")
        return {"clarifying_questions": None}

    prompt = fill_prompt("clarifying_questions",
        open_questions=json.dumps(open_questions, ensure_ascii=False),
        semantic_map=json.dumps(state["semantic_map"], ensure_ascii=False),
    )
    questions = safe_json_parse(llm.invoke(prompt).content)
    print_section("❓ Уточняющие вопросы", questions)

    all_q = [q for g in questions.get("question_groups", []) for q in g.get("questions", [])]
    high  = [q for q in all_q if q.get("criticality") == "high"]

    answers = {}
    if high:
        print("\n⚠️  Есть критичные вопросы — без ответов декомпозиция будет неточной.")
        if ask_user("Ответить сейчас?", ["y", "n"]) == "y":
            for q in high:
                print(f"\n[{q['id']}] {q['question']}")
                print(f"    Почему важно: {q['why_important']}")
                ans = input("    Ваш ответ (Enter — пропустить): ").strip()
                if ans:
                    answers[q["id"]] = ans

    semantic_map = state["semantic_map"].copy()
    if answers:
        semantic_map["clarifications"] = answers
    return {"clarifying_questions": questions, "semantic_map": semantic_map}


def generate_epics(state: ArchitectState, llm) -> dict:
    print("\n⚙️  Генерирую эпики...")
    context  = json.dumps(state["semantic_map"], ensure_ascii=False)
    feedback = state.get("user_feedback")
    suffix   = f"\n\nФидбек от заказчика: {feedback}" if feedback else ""
    response = llm.invoke(load_prompt("generate_epics") + "\n\n" + context + suffix)
    parsed   = safe_json_parse(response.content)
    print_section("🗂️  Эпики", parsed["epics"])
    return {"epics": parsed["epics"], "user_feedback": None}


def qa_epics(state: ArchitectState, llm) -> dict:
    print("\n🔍 QA эпиков...")
    prompt = fill_prompt("qa_epics",
        semantic_map=json.dumps(state["semantic_map"], ensure_ascii=False),
        epics=json.dumps(state["epics"], ensure_ascii=False),
    )
    parsed = safe_json_parse(llm.invoke(prompt).content)
    print_section("🔍 Результат QA", parsed)
    return {"qa_result": parsed}


def decide_after_qa_epics(state: ArchitectState) -> str:
    qa      = state["qa_result"]
    retries = state.get("qa_retries", 0)

    if qa["status"] == "fail" and retries < MAX_QA_RETRIES:
        print(f"\n⚠️  QA не прошёл (попытка {retries + 1}/{MAX_QA_RETRIES}):")
        for issue in qa.get("issues", []):
            print(f"   • [{issue['type']}] {issue['description']}")
        print("\n🔄 Перегенерирую автоматически...")
        return "regenerate_epics"

    if qa["status"] == "fail":
        print("\n⚠️  Лимит QA-попыток исчерпан.")

    print("\n  y — утвердить и перейти к User Stories")
    print("  e — переделать (опишите что не так)")
    print("  q — выйти")
    choice = ask_user("Ваш выбор:", ["y", "e", "q"])

    if choice == "y":
        return "generate_stories"
    elif choice == "e":
        feedback = input("Что нужно изменить: ").strip()
        state["semantic_map"]["epic_feedback"] = feedback
        return "regenerate_epics"
    else:
        return "end"


def increment_qa_retries(state: ArchitectState) -> dict:
    return {"qa_retries": state.get("qa_retries", 0) + 1}


def generate_stories(state: ArchitectState, llm) -> dict:
    idx   = state.get("current_epic_index", 0)
    epics = state["epics"]

    if idx >= len(epics):
        return {}

    epic = epics[idx]
    print(f"\n📖 User Stories — эпик [{idx + 1}/{len(epics)}]: {epic['title']}")

    base_prompt = fill_prompt("generate_stories",
        epic_id=epic["id"],
        epic=json.dumps(epic, ensure_ascii=False),
        semantic_map=json.dumps(state["semantic_map"], ensure_ascii=False),
    )
    prompt = base_prompt

    while True:
        stories = safe_json_parse(llm.invoke(prompt).content)["stories"]
        print_section(f"📝 User Stories — {epic['title']}", stories)

        print("\n  y    — утвердить")
        print("  r    — переделать")
        print("  skip — пропустить эпик")
        choice = ask_user("Ваш выбор:", ["y", "r", "skip"])

        if choice == "y":
            return {
                "stories":     stories,
                "all_stories": state.get("all_stories", []) + stories,
                "current_epic_index": idx + 1,
            }
        elif choice == "skip":
            return {"stories": [], "current_epic_index": idx + 1}
        else:
            feedback = input("Что нужно исправить: ").strip()
            prompt = base_prompt + f"\n\nФидбек: {feedback}"


def decide_after_stories(state: ArchitectState) -> str:
    idx     = state.get("current_epic_index", 0)
    stories = state.get("stories", [])
    if not stories:
        return "finalize" if idx >= len(state["epics"]) else "generate_stories"
    return "finalize" if idx >= len(state["epics"]) else "generate_tasks"


def generate_tasks(state: ArchitectState, llm) -> dict:
    idx  = state.get("current_epic_index", 1)
    epic = state["epics"][idx - 1]
    print(f"\n⚙️  Задачи для эпика: {epic['title']}")

    prompt = fill_prompt("generate_tasks",
        story_id=epic["id"],
        stories=json.dumps(state.get("stories", []), ensure_ascii=False),
        epic=json.dumps(epic, ensure_ascii=False),
    )
    tasks = safe_json_parse(llm.invoke(prompt).content)["tasks"]
    print_section(f"✅ Задачи — {epic['title']}", tasks)

    return {
        "tasks":     tasks,
        "all_tasks": state.get("all_tasks", []) + tasks,
    }


def decide_next_epic(state: ArchitectState) -> str:
    idx = state.get("current_epic_index", 0)
    return "generate_stories" if idx < len(state["epics"]) else "finalize"


def finalize_and_export(state: ArchitectState) -> dict:
    epics       = state.get("epics", [])
    all_stories = state.get("all_stories", [])
    all_tasks   = state.get("all_tasks", [])

    stories_by_epic  = {}
    for s in all_stories:
        stories_by_epic.setdefault(s.get("epic_id", "?"), []).append(s)

    tasks_by_story = {}
    for t in all_tasks:
        tasks_by_story.setdefault(t.get("story_id", "?"), []).append(t)

    print("\n" + "=" * 60)
    print("🎉  ИТОГОВАЯ ДЕКОМПОЗИЦИЯ")
    print("=" * 60)

    for epic in epics:
        print(f"\n📦 [{epic['id']}] {epic['title']}")
        print(f"   {epic['description']}")
        print(f"   Ценность: {epic['business_value']}")

        for story in stories_by_epic.get(epic["id"], []):
            print(f"\n   📝 [{story['id']}] {story['title']}")
            print(f"       Как {story['as_a']}, я хочу {story['i_want']},")
            print(f"       чтобы {story['so_that']}")
            for ac in story.get("acceptance_criteria", []):
                print(f"         ✓ {ac}")

            for task in tasks_by_story.get(story["id"], []):
                print(f"\n       ⚙️  [{task['id']}] [{task['type'].upper()}] {task['title']}")
                print(f"           {task['description']}")
                print(f"           Оценка: {task['estimate_hours']}ч  |  DoD: {task['definition_of_done']}")

    print("\n" + "=" * 60)
    print(f"Итого: {len(epics)} эпиков | {len(all_stories)} stories | {len(all_tasks)} задач")
    print("=" * 60)
    return {}