# azure_rest_sample.py
import time, requests, json, os
from dotenv import load_dotenv          # ← 追加

# 1) .env をロード（現在の作業ディレクトリ or 指定パスから）
load_dotenv()

# 2) 環境変数を取得
ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT").rstrip("/")
API_KEY  = os.getenv("AZURE_PROJECT_API_KEY")
AGENT_ID = os.getenv("AZURE_AGENT_ID")

if not (ENDPOINT and API_KEY and AGENT_ID):
    raise RuntimeError(".env に ENDPOINT / API_KEY / AGENT_ID が設定されていません")

HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}

def create_run(prompt: str):
    url = f"{ENDPOINT}/threads/runs?api-version=v1"
    body = {
        "assistant_id": AGENT_ID,
        "thread": {"messages": [{"role": "user", "content": prompt}]}
    }
    res = requests.post(url, headers=HEADERS, json=body, timeout=30)
    res.raise_for_status()
    j = res.json()
    return j["thread_id"], j["id"]

def wait_run(thread_id, run_id):
    url = f"{ENDPOINT}/threads/{thread_id}/runs/{run_id}?api-version=v1"
    while True:
        j = requests.get(url, headers=HEADERS, timeout=15).json()
        if j["status"] in ("completed", "failed", "cancelled"):
            return j["status"]
        time.sleep(1)

def list_messages(thread_id):
    url = f"{ENDPOINT}/threads/{thread_id}/messages?api-version=v1"
    return requests.get(url, headers=HEADERS, timeout=15).json()["data"]

if __name__ == "__main__":
    prompt = "今日のニュースをまとめて。今日は (2025-06-25) です。ジャンルは経済・テクノロジーでお願いします。"
    tid, rid = create_run(prompt)
    status = wait_run(tid, rid)
    if status == "completed":
        for m in list_messages(tid):
            if m["role"] == "assistant":
                print(m["content"]["text"]["value"])
