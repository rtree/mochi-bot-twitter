# testRest.py
import os
import requests
from dotenv import load_dotenv

# Load env values
load_dotenv()

api_key = os.getenv("AZURE_PROJECT_API_KEY")
endpoint = os.getenv("AZURE_PROJECT_ENDPOINT").rstrip("/")
agent_id = os.getenv("AZURE_AGENT_ID")
api_version = "2024-05-15-preview"

headers = {
    "api-key": api_key,
    "Content-Type": "application/json"
}

def run_agent():
    # Step 1: Create a thread
    thread_resp = requests.post(f"{endpoint}/threads?api-version={api_version}", headers=headers)
    thread_resp.raise_for_status()
    thread_id = thread_resp.json()["id"]
    print("✅ Thread ID:", thread_id)

    # Step 2: Post user message
    message = {"role": "user", "content": "Summarize today's top tech and economy news"}
    msg_resp = requests.post(f"{endpoint}/threads/{thread_id}/messages?api-version={api_version}", headers=headers, json=message)
    msg_resp.raise_for_status()

    # Step 3: Run agent
    run_body = {"assistant_id": agent_id}
    run_resp = requests.post(f"{endpoint}/threads/{thread_id}/runs?api-version={api_version}", headers=headers, json=run_body)
    run_resp.raise_for_status()
    run_id = run_resp.json()["id"]
    print("⏳ Run ID:", run_id)

    # Step 4: Poll for completion
    while True:
        status_resp = requests.get(f"{endpoint}/threads/{thread_id}/runs/{run_id}?api-version={api_version}", headers=headers)
        status_resp.raise_for_status()
        status = status_resp.json()["status"]
        print("  Run status:", status)
        if status in ["succeeded", "failed", "cancelled"]:
            break

    # Step 5: Get agent messages
    messages_resp = requests.get(f"{endpoint}/threads/{thread_id}/messages?api-version={api_version}", headers=headers)
    messages_resp.raise_for_status()
    messages = messages_resp.json().get("value", [])
    for m in messages:
        if m["role"] == "assistant":
            print("\n🤖 Assistant reply:\n", m["content"])
            if "annotations" in m:
                for ann in m["annotations"]:
                    print("📎 Citation:", ann.get("url"))

if __name__ == "__main__":
    run_agent()
