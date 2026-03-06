from nodes import *
from langgraph.graph import StateGraph, END
import functools


def build_graph(llm):
    def node(fn):
        return functools.partial(fn, llm=llm)

    wf = StateGraph(ArchitectState)

    wf.add_node("analyze",          node(analyze_document))
    wf.add_node("clarify",          node(handle_clarifying_questions))
    wf.add_node("generate_epics",   node(generate_epics))
    wf.add_node("qa_epics",         node(qa_epics))
    wf.add_node("inc_retries",      increment_qa_retries)
    wf.add_node("generate_stories", node(generate_stories))
    wf.add_node("generate_tasks",   node(generate_tasks))
    wf.add_node("finalize",         finalize_and_export)

    wf.set_entry_point("analyze")

    wf.add_edge("analyze",        "clarify")
    wf.add_edge("clarify",        "generate_epics")
    wf.add_edge("generate_epics", "qa_epics")

    wf.add_conditional_edges("qa_epics", decide_after_qa_epics, {
        "regenerate_epics": "inc_retries",
        "generate_stories": "generate_stories",
        "end":              END,
    })
    wf.add_edge("inc_retries", "generate_epics")

    wf.add_conditional_edges("generate_stories", decide_after_stories, {
        "generate_tasks":   "generate_tasks",
        "generate_stories": "generate_stories",
        "finalize":         "finalize",
    })

    wf.add_conditional_edges("generate_tasks", decide_next_epic, {
        "generate_stories": "generate_stories",
        "finalize":         "finalize",
    })

    wf.add_edge("finalize", END)
    return wf.compile()