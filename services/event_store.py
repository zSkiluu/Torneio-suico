import json
from pathlib import Path


class EventStore:
    def __init__(self, path="event_store.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def append(self, event_type, data):
        events = self.load()
        event = {"type": event_type, "data": data}
        events.append(event)
        self.path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
        return event

    def load(self):
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                return []
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            self.path.write_text("[]", encoding="utf-8")
            return []

    def replay(self):
        return self.load()

    def clear(self):
        self.path.write_text("[]", encoding="utf-8")
        return []
