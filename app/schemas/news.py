from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class NewsCreate(BaseModel):
    title: str
    url: str
    country: Optional[str] = None
    published_text: Optional[str] = None
    comments: Optional[int] = Field(None, ge=0)


class NewsUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    country: Optional[str] = None
    published_text: Optional[str] = None
    comments: Optional[int] = Field(None, ge=0)


class NewsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    country: Optional[str]
    published_text: Optional[str]
    comments: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


