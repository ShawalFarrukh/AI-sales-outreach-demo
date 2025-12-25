import json
from test_api import ask_ai

raw = ask_ai("Acme Logistics", "Logistics", "Manual follow-ups, Excel-based tracking")
data = json.loads(raw)

print(data["category"])
print(data["opportunity_summary"])
print(data["draft_email"])
