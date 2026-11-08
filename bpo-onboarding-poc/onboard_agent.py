import os
import requests
import json
from dotenv import load_dotenv

# Load the hidden token from the .env file
load_dotenv()
WEBEX_TOKEN = os.getenv("WEBEX_TOKEN")

# Define the API headers
HEADERS = {
    "Authorization": f"Bearer {WEBEX_TOKEN}",
    "Content-Type": "application/json"
}

def create_webex_space(space_name):
    """Creates a new Webex space for the onboarding batch."""
    url = "https://webexapis.com/v1/rooms"
    payload = {"title": space_name}

    print(f"Creating Webex space: '{space_name}'...")
    response = requests.post(url, headers=HEADERS, data=json.dumps(payload))

    if response.status_code == 200:
        room_id = response.json().get("id")
        print("Success: Space created.")
        return room_id
    else:
        print(f"Failed to create space. HTTP Status: {response.status_code}")
        return None

def add_user_to_space(room_id, user_email):
    """Adds a remote agent to the Webex space."""
    url = "https://webexapis.com/v1/memberships"
    payload = {
        "roomId": room_id,
        "personEmail": user_email
    }
    
    print(f"Adding agent {user_email} to the space...")
    response = requests.post(url, headers=HEADERS, data=json.dumps(payload))
    
    if response.status_code == 200:
        print("Success: Agent added to the space.")
    elif response.status_code == 409:
        print("Notice (409 Conflict): Agent is already a member of this space (e.g., room creator).")
    else:
        print(f"Failed to add agent. HTTP Status: {response.status_code}")
        print(f"API Response: {response.text}")

if __name__ == "__main__":
    if not WEBEX_TOKEN:
        print("Error: WEBEX_TOKEN is missing. Check your .env file.")
    else:
        # Execute the onboarding workflow
        batch_name = "BPO Remote Agents - November Intake"
        agent_email = "ryujinkyouga@gmail.com" # Replace with a real Webex account email to test

        new_room_id = create_webex_space(batch_name)
        if new_room_id:
            add_user_to_space(new_room_id, agent_email)