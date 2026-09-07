from enum import Enum


class QuestionType(str, Enum):
    single_choice = "single_choice"
    multiple_choice = "multiple_choice"
    fill_blank = "fill_blank"
    coding = "coding"
    essay = "essay"


class QuestionStatus(str, Enum):
    active = "active"
    archived = "archived"


class SessionMode(str, Enum):
    practice = "practice"
    exam = "exam"
    mistake = "mistake"
    category = "category"


class SessionStatus(str, Enum):
    active = "active"
    paused = "paused"
    submitted = "submitted"
    abandoned = "abandoned"


class OrderBy(str, Enum):
    created_at = "created_at"
    updated_at = "updated_at"
    difficulty = "difficulty"
    code = "code"


class BatchAction(str, Enum):
    delete = "delete"
    set_category = "set_category"
    add_tags = "add_tags"
    set_difficulty = "set_difficulty"


QUESTION_TYPES: tuple[str, ...] = tuple(t.value for t in QuestionType)
