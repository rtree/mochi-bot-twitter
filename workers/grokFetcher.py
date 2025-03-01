import os
from datetime import datetime
from openai import OpenAI

class GrokFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        os.environ["XAI_API_KEY"] = self.config.get("GROK_API_KEY")
        self.client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")

    async def fetch(self):
        msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。目先の細かな動きよりも、世の中を大きく動かす可能性があるものやインパクトが大きいものを知りたいです。検索する場合はニュースの期間指定もお願いします"
        self.config.logprint.info("-User input------------------------------------------------------------------")
        self.config.logprint.info(f"  Message content: '{msg}'")
        discIn = [{"role": "user", "content": msg}]
        self.context.extend(discIn)

        response = self.client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": "You are a social media analyst."},
                {"role": "user", "content": msg}
            ]
        )
        
        fetched_content = response.choices[0].message['content']
        urls = self._extract_urls(fetched_content)
        
        return fetched_content, urls

    def _extract_urls(self, content):
        # Dummy implementation to extract URLs from the content
        # You can replace this with actual URL extraction logic
        return [""]