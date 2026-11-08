import os
import requests
from dotenv import load_dotenv

load_dotenv()
WEBEX_TOKEN = os.getenv("WEBEX_TOKEN")

if not WEBEX_TOKEN:
    print("WEBEX_TOKEN is missing. Add it to .env to list live Webex rooms.")
    raise SystemExit(1)

headers = {"Authorization": f"Bearer {WEBEX_TOKEN}"}
try:
    response = requests.get("https://webexapis.com/v1/rooms", headers=headers, timeout=8)
    if response.status_code == 200:
        rooms = response.json().get("items", [])
        print("\n--- WEBEX ROOMS ---")
        for r in rooms:
            print(f"Title: {r.get('title')}")
            print(f"ID:    {r.get('id')}\n")
        if not rooms:
            print("No rooms found.")
    else:
        print(f"Error fetching rooms: {response.status_code} {response.text}")
except requests.RequestException as exc:
    print(f"Network/API error while fetching rooms: {exc}")