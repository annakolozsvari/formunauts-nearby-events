from pydantic import BaseModel, HttpUrl
from datetime import datetime

class BrowserLocation(BaseModel):
    current: HttpUrl
    referrer: HttpUrl

class EventContext(BaseModel):
    reason: str | None = None
    duration: float | None = None
    tag_name: str | None = None
    source_id: str
    target_id: str | None = None
    source_category: str

class EventFields(BaseModel):
    customer: int
    fundraiser: int
    name: str
    event_type: str
    timestamp: datetime
    event_context: EventContext
    browser_location: BrowserLocation
    device_coordinates: str

class EventIn(BaseModel):
    model: str
    pk: int
    fields: EventFields

class EventOut(EventFields):
    pk: int