import json
import requests

with open('attempt_events.json', 'r') as f:
    events = json.load(f)

print(f"Loaded {len(events)} events, sending to API...")
r = requests.post('http://localhost:9000/api/ingest/attempts', json={'events': events}, timeout=120)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))
