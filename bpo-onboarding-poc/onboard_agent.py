import os
import sys
import requests
import json
from dotenv import load_dotenv

load_dotenv()
WEBEX_TOKEN = os.getenv("WEBEX_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {WEBEX_TOKEN}",
    "Content-Type": "application/json"
}


def create_webex_space(space_name):
    """Creates or returns an existing Webex space for an onboarding team."""
    url = "https://webexapis.com/v1/rooms"
    try:
        existing = requests.get(url, headers=HEADERS, timeout=8)
        if existing.status_code == 401:
            print("Webex token invalid/expired (401). Use the Flask app's simulated mode for demos.")
            return None
        if existing.status_code == 200:
            for room in existing.json().get("items", []):
                if room.get("title") == space_name:
                    print(f"Using existing Webex space: '{space_name}'.")
                    return room.get("id")

        print(f"Creating Webex space: '{space_name}'...")
        response = requests.post(url, headers=HEADERS, data=json.dumps({"title": space_name}), timeout=8)
        if response.status_code == 200:
            room_id = response.json().get("id")
            print("Success: Space created.")
            return room_id
        print(f"Failed to create space. HTTP Status: {response.status_code}")
        return None
    except requests.RequestException as exc:
        print(f"Network/API error while creating space: {exc}")
        return None


def add_user_to_space(room_id, user_email):
    """Adds a remote agent to the Webex space."""
    url = "https://webexapis.com/v1/memberships"
    payload = {"roomId": room_id, "personEmail": user_email}

    print(f"Adding agent {user_email} to the space...")
    try:
        response = requests.post(url, headers=HEADERS, data=json.dumps(payload), timeout=8)
        if response.status_code == 200:
            print("Success: Agent added to the space.")
        elif response.status_code == 409:
            print("Notice (409 Conflict): Agent is already a member of this space.")
        elif response.status_code == 401:
            print("Webex token invalid/expired (401). Agent not added.")
        else:
            print(f"Failed to add agent. HTTP Status: {response.status_code}")
            print(f"API Response: {response.text}")
    except requests.RequestException as exc:
        print(f"Network/API error while adding agent: {exc}")


if __name__ == "__main__":
    if not WEBEX_TOKEN:
        print("WEBEX_TOKEN is missing. Add it to .env for live Webex provisioning, or use the Flask portal's simulation mode.")
        sys.exit(1)

    batch_name = sys.argv[1] if len(sys.argv) > 1 else os.getenv("WEBEX_BATCH_NAME", "BPO Remote Agents - Intake")
    agent_email = sys.argv[2] if len(sys.argv) > 2 else os.getenv("AGENT_EMAIL")

    if not agent_email:
        print("Usage: python onboard_agent.py \"Team/Batch Space Name\" agent@example.com")
        print("Or set AGENT_EMAIL in the environment.")
        sys.exit(1)

    new_room_id = create_webex_space(batch_name)
    if new_room_id:
        add_user_to_space(new_room_id, agent_email)