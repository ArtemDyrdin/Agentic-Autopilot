from langchain_ollama import ChatOllama
from graph import build_graph

def run(document_path: str, model: str = "qwen2.5:7b-instruct") -> dict:
    with open(document_path, encoding="utf-8") as f:
        document = f.read()

    print(f"\n🚀 IT Project Architect")
    print(f"   Документ : {document_path} ({len(document)} символов)")
    print(f"   Модель   : {model}\n")

    llm   = ChatOllama(model=model, temperature=0.2, format="json", num_ctx=8192, repeat_penalty=1.1)
    graph = build_graph(llm)

    return graph.invoke({
        "raw_document":         document,
        "semantic_map":         None,
        "clarifying_questions": None,
        "epics":                None,
        "stories":              None,
        "all_stories":          [],
        "tasks":                None,
        "all_tasks":            [],
        "qa_result":            None,
        "qa_retries":           0,
        "current_epic_index":   0,
        "user_feedback":        None,
    })