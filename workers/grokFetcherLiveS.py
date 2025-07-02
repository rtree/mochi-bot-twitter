import os
from datetime import datetime
import requests

class GrokFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config

    async def fetch(self):
        msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。各々１０個ずつください。目先の細かな動きよりも、世の中を大きく動かす可能性があるものやインパクトが大きいものを知りたいです。検索する場合はニュースの期間指定もお願いします"
        self.config.logprint.info("-User input------------------------------------------------------------------")
        self.config.logprint.info(f"  Message content: '{msg}'")
        discIn = [{"role": "user", "content": msg}]
        self.context.extend(discIn)

        p_src = (
            f"""
            {msg}

            回答のフォーマットはこちら:
            --- Start of content ---
            Title: *ニュースの要約*
            URL: *一番関係がありそうなxまたはx以外のサイトのURL*
            SRC: X
            Snippet:
            *なるべく詳細なニュースの解説*
            --- End   of content ---

            please avoid hallucination, if you do not have the confidence of the news, please remove them from answer.

            """
        )

        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('XAI_API_KEY', self.config.GROK_API_KEY)}"
        }
        payload = {
            "messages": [
                {"role": "system", "content": "You are a social media analyst."},
                {"role": "user", "content": p_src},
            ],
            "search_parameters": {"mode": "auto"},
            "model": self.config.GROK_MODEL or "grok-3-latest",
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        fetched_content = data["choices"][0]["message"]["content"]
        urls = self._extract_urls(fetched_content)
        
        return fetched_content, urls

    def _extract_urls(self, content):
        # Dummy implementation to extract URLs from the content
        # You can replace this with actual URL extraction logic
        return [""]
