import os
from datetime import datetime
from openai import OpenAI

class GrokFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.client = OpenAI(api_key=config.GROK_API_KEY, base_url="https://api.x.ai/v1")

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
        
        fetched_content = response.choices[0].message.content
        urls = self._extract_urls(fetched_content)
        
        return fetched_content, urls

    def _extract_urls(self, content):
        # Dummy implementation to extract URLs from the content
        # You can replace this with actual URL extraction logic
        return ["https://twitter.com/sample_post_1", "https://twitter.com/sample_post_2"]

    async def fetch_news(self):
        tech_news = await self._fetch_news_by_topic("tech")
        econ_news = await self._fetch_news_by_topic("economics")
        return tech_news + econ_news

    async def _fetch_news_by_topic(self, topic):
        msg = f"Please summarize the latest news in {topic}. Provide at least 10 articles."
        self.config.logprint.info(f"Fetching news for topic: {topic}")
        discIn = [{"role": "user", "content": msg}]
        self.context.extend(discIn)

        response = self.client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": "You are a news summarizer."},
                {"role": "user", "content": msg}
            ]
        )

        fetched_content = response.choices[0].message.content
        urls = self._extract_urls(fetched_content)
        formatted_content = self._format_content(fetched_content, urls)
        
        return formatted_content

    def _format_content(self, content, urls):
        content_list = []
        for i, url in enumerate(urls):
            title = f"Article {i+1}"
            snippet = content.split('\n')[i] if i < len(content.split('\n')) else "No snippet available"
            content_list.append(f"{self.config.FETCHER_START_OF_CONTENT}\nタイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\nSRC: Grok\n{self.config.FETCHER_END_OF_CONTENT}\n")
        return "\n".join(content_list)