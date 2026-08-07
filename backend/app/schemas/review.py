from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class ReviewCreate(BaseModel):
    author_name: str = Field(min_length=1, max_length=80)
    author_title: str | None = Field(default=None, max_length=120)
    rating: int = Field(default=5, ge=1, le=5)
    body: str = Field(min_length=1, max_length=1000)
    is_published: bool = True

    @field_validator("author_name", "author_title", "body", mode="before")
    @classmethod
    def strip_text(cls, value: Any, info: ValidationInfo):
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if info.field_name == "author_title" and not cleaned:
            return None
        return cleaned


class ReviewEdit(BaseModel):
    author_name: str | None = Field(default=None, min_length=1, max_length=80)
    author_title: str | None = Field(default=None, max_length=120)
    rating: int | None = Field(default=None, ge=1, le=5)
    body: str | None = Field(default=None, min_length=1, max_length=1000)
    is_published: bool | None = None

    @field_validator("author_name", "author_title", "body", mode="before")
    @classmethod
    def strip_text(cls, value: Any, info: ValidationInfo):
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if info.field_name == "author_title" and not cleaned:
            return None
        return cleaned


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_name: str
    author_title: str | None
    rating: int
    body: str
    is_published: bool
    created_at: datetime
    updated_at: datetime
