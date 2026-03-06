from typing import TypedDict, Optional

class ArchitectState(TypedDict):
    raw_document:         str
    semantic_map:         Optional[dict]
    clarifying_questions: Optional[dict]
    epics:                Optional[list[dict]]
    stories:              Optional[list[dict]]
    all_stories:          list[dict]
    tasks:                Optional[list[dict]]
    all_tasks:            list[dict]
    qa_result:            Optional[dict]
    qa_retries:           int
    current_epic_index:   int
    user_feedback:        Optional[str]