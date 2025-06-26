# Sample script using Azure Agents SDK
import time
import os
from dotenv import load_dotenv
from config import Config
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import AgentThreadCreationOptions, ListSortOrder
from azure.identity import DefaultAzureCredential

# 1) .env をロード（現在の作業ディレクトリ or 指定パスから）
load_dotenv()
config = Config()

# 2) 環境変数を取得
ENDPOINT = config.AZURE_PROJECT_ENDPOINT.rstrip("/") if config.AZURE_PROJECT_ENDPOINT else ""
AGENT_ID = config.AZURE_AGENT_ID

if config.AZURE_CLIENT_ID:
    os.environ["AZURE_CLIENT_ID"] = config.AZURE_CLIENT_ID
if config.AZURE_CLIENT_SECRET:
    os.environ["AZURE_CLIENT_SECRET"] = config.AZURE_CLIENT_SECRET
if config.AZURE_TENANT_ID:
    os.environ["AZURE_TENANT_ID"] = config.AZURE_TENANT_ID

print(f"ENDPOINT: {ENDPOINT}")
print(f"AGENT_ID: {AGENT_ID}")

if not (ENDPOINT and AGENT_ID):
    raise RuntimeError(".env に ENDPOINT / AGENT_ID が設定されていません")

credential = DefaultAzureCredential()
client = AgentsClient(endpoint=ENDPOINT, credential=credential)

def create_run(prompt: str):
    thread = AgentThreadCreationOptions(messages=[{"role": "user", "content": prompt}])
    run = client.create_thread_and_run(agent_id=AGENT_ID, thread=thread)
    return run.thread_id, run.id

def wait_run(thread_id, run_id):
    while True:
        run = client.runs.get(run_id=run_id, thread_id=thread_id)
        if run.status in ("completed", "failed", "canceled", "cancelled"):
            return run.status
        time.sleep(1)

def list_messages(thread_id):
    return client.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

if __name__ == "__main__":
    prompt = "今日のニュースをまとめて。今日は (2025-06-25) です。ジャンルは経済・テクノロジーでお願いします。"
    tid, rid = create_run(prompt)
    status = wait_run(tid, rid)
    if status == "completed":
        for m in list_messages(tid):
            if m.role == "agent":
                text = "\n".join(t.text.value for t in m.text_messages)
                print(text)
