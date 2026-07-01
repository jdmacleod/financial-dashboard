import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MatchType = Literal["exact", "contains", "regex"]


class CategoryRuleCreate(BaseModel):
    pattern: str = Field(min_length=1, max_length=255)
    match_type: MatchType = "contains"
    category_id: uuid.UUID
    priority: int = 0
    is_active: bool = True


class CategoryRuleUpdate(BaseModel):
    pattern: str | None = Field(default=None, min_length=1, max_length=255)
    match_type: MatchType | None = None
    category_id: uuid.UUID | None = None
    priority: int | None = None
    is_active: bool | None = None


class CategoryRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    pattern: str
    match_type: str
    category_id: uuid.UUID
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RuleSuggestion(BaseModel):
    """A candidate rule mined from history: a payee that has been categorized the
    same way often enough to be worth a 'contains' rule. Never auto-created."""

    pattern: str
    match_type: MatchType = "contains"
    category_id: uuid.UUID
    category_name: str
    occurrences: int


class BackfillResponse(BaseModel):
    updated: int
