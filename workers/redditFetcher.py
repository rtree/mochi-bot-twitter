import asyncio
import base64
import requests
from openai import OpenAI
from datetime import datetime
from PyPDF2 import PdfReader
from io import BytesIO
from bs4 import BeautifulSoup
import aiohttp

class RedditFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.aiclient = OpenAI(api_key=config.OPENAI_API_KEY)  # OpenAI Client
        self.headers = {"User-Agent": "YourApp/1.0 (by YourRedditUsername)"}
        self.access_token = None

    async def fetch(self):
        """Fetch trending Reddit posts, extract key content, and summarize."""
        today = datetime.today().strftime('%Y-%m-%d')
        msg = f"今日のRedditのトレンド ({today}) をまとめます。ジャンル: 経済・テクノロジー"

        self.config.logprint.info(f"-User input: '{msg}'")

        await self._authenticate()  # Get OAuth token
        reddit_data = await self._search_reddit()  # Fetch posts

        if not reddit_data:
            self.config.logprint.error("No data fetched from Reddit.")
            return "Redditからデータを取得できませんでした。"

        fetched_summaries = await self._summarize_posts_async(reddit_data)
        return fetched_summaries, reddit_data['urls']

    async def _authenticate(self):
        """Get OAuth token for Reddit API."""
        auth = aiohttp.BasicAuth(self.config.REDDIT_CLIENT_ID, self.config.REDDIT_CLIENT_SECRET)
        data = {"grant_type": "password", "username": self.config.REDDIT_USERNAME, "password": self.config.REDDIT_PASSWORD}

        async with aiohttp.ClientSession() as session:
            async with session.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=self.headers) as response:
                if response.status != 200:
                    self.config.logprint.error(f"Failed to authenticate with Reddit API. Status: {response.status}")
                    return None
                token_data = await response.json()
                self.access_token = token_data.get("access_token")
                self.headers["Authorization"] = f"bearer {self.access_token}"

    async def _search_reddit(self):
        """Fetch top posts from Reddit API with authentication."""
        url = "https://oauth.reddit.com/r/technology/top"
        params = {"limit": self.config.REDDIT_SEARCH_RESULTS}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    self.config.logprint.error(f"Failed to fetch Reddit posts. Status: {response.status}")
                    return None

                data = await response.json()
                posts = data.get("data", {}).get("children", [])

                extracted_posts = []
                urls = []
                for post in posts:
                    post_data = post["data"]
                    extracted_posts.append({
                        "title": post_data.get("title"),
                        "url": post_data.get("url"),
                        "selftext": post_data.get("selftext", ""),  # ✅ Fetch post content
                        "comments_url": f"https://www.reddit.com{post_data.get('permalink')}",
                    })
                    urls.append(post_data.get("url"))

                return {"posts": extracted_posts, "urls": urls}

    async def _summarize_posts_async(self, reddit_data):
        """Summarizes Reddit posts using AI."""
        content_list = []
        tasks = [self._summarize_text(post["title"], post["selftext"], post["url"]) for post in reddit_data["posts"]]
        summaries = await asyncio.gather(*tasks, return_exceptions=True)

        for summary in summaries:
            content_list.append(summary)

        return "\n".join(content_list)

    async def _summarize_text(self, title, text, url):
        """Uses AI to summarize post content asynchronously."""
        if not text:
            return f"Title: {title}\nURL: {url}\nSnippet: No text available for summarization.\n"

        try:
            messages = [{"role": "user", "content": f"Summarize in 280 characters: {text}"}]
            response = self.aiclient.chat.completions.create(
                model=self.config.OPENAI_GPT_MODEL,
                messages=messages
            )
            summary = response.choices[0].message.content.strip()
            return f"Title: {title}\nURL: {url}\nSnippet: Summary: {summary}\n"

        except Exception as e:
            self.config.logprint.error(f"Error summarizing text: {str(e)}")
            return f"Title: {title}\nURL: {url}\nSnippet: Summary unavailable.\n"

