from datetime import datetime
from pydantic import BaseModel, HttpUrl

class URLCreateRequest(BaseModel):
    url: HttpUrl


class URLCreateResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


class URLInfoResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    visit_count: int