from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#6c8cff", pattern=HEX_COLOR_PATTERN)


class CategoryEdit(BaseModel):
    """All optional — omitted fields are left alone."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)
    position: int | None = Field(default=None, ge=0)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    position: int
    created_at: datetime
    # how many of the user's downloads currently carry this tag
    download_count: int = 0
