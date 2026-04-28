from fastapi import FastAPI, HTTPException, Query
from typing import Annotated
from pydantic import TypeAdapter
from pathlib import Path

from datetime import date
import re
from geopy.distance import distance

from app.models.models import *

app = FastAPI()

def get_all_events():  
    input = Path('input.json').read_text()
    eventin_list_adapter = TypeAdapter(list[EventIn])
    input_events = eventin_list_adapter.validate_json(input)
    return input_events

def transform_events(input_events):
    return [EventOut(
        pk=input_event.pk,
        **input_event.model_dump()['fields']
        ) for input_event in input_events]

def find_base_event(events, base_event_id):
    base_event = next((event for event in events if event.pk == base_event_id), None)
    if base_event is None:
        raise HTTPException(status_code=404, detail="Base event not found")
    return base_event

def parse_lng_lat(input: str) -> tuple[float, float]:
    match = re.search(r'POINT \(([0-9.-]+) ([0-9.-]+)\)', input)
    if not match:
        raise HTTPException(status_code=400, detail="Could not parse geolocation")
    lng, lat = float(match.group(1)), float(match.group(2))
    # reverse Latitude and Longitude, as GeoPy expects it that way
    return lat, lng

@app.get("/events/{event_id}/nearby_events")
async def get_nearby_events(event_id: int, radius: Annotated[int, Query(ge=0)], date: date | None = None) -> list[EventOut]:

    input_events = get_all_events()
    events = transform_events(input_events)
    base_event = find_base_event(events, event_id)
    events.remove(base_event)

    if date:
        events = [event for event in events if event.timestamp.date() == date]

    base_event_geolocation = parse_lng_lat(base_event.device_coordinates)
    events = [
        event for event in events
        if distance(base_event_geolocation, parse_lng_lat(event.device_coordinates)).km * 1000 <= radius
    ]

    return events