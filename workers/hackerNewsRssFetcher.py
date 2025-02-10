import asyncio
import base64
import requests
from openai import OpenAI
from datetime import datetime
from PyPDF2 import PdfReader
from io import BytesIO
from bs4 import BeautifulSoup
import aiohttp
import feedparser

class HackerNewsRssFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.aiclient = OpenAI(api_key=config.OPENAI_API_KEY)
        self.headers = {"User-Agent": "YourApp/1.0 (by YourHackerNewsUsername)"}
        self.srcname = "Hacker News"

    async def fetch(self):
        """Fetch trending Hacker News posts, extract key content, and summarize."""
        today = datetime.today().strftime('%Y-%m-%d')
        msg = f"今日のHacker Newsのトレンド ({today}) をまとめます。"

        self.config.logprint.info(f"-User input: '{msg}'")

        hacker_news_data = await self._fetch_hacker_news()  # Fetch posts

        if not hacker_news_data:
            self.config.logprint.error("No data fetched from Hacker News.")
            return "Hacker Newsからデータを取得できませんでした。"

        fetched_summaries = await self._summarize_posts_async(hacker_news_data)
        return fetched_summaries, hacker_news_data['urls']

    async def _fetch_hacker_news(self):
        """Fetch top posts from Hacker News RSS feed."""
        url = "https://hnrss.org/frontpage"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    self.config.logprint.error(f"Failed to fetch Hacker News posts. Status: {response.status}")
                    return None

                feed = feedparser.parse(await response.text())
                extracted_posts = []
                urls = []
                for entry in feed.entries:
                    extracted_posts.append({
                        "title": entry.title,
                        "url": entry.link,
                        "selftext": entry.summary,  # Fetch post content
                    })
                    urls.append(entry.link)

                self.config.logprint.info("Hacker News Search Results:")
                for entry in feed.entries:
                    self.config.logprint.info(f"Title: {entry.title}")
                    self.config.logprint.info(f"URL: {entry.link}")
                    self.config.logprint.info(f"Snippet: {entry.summary}")
                    self.config.logprint.info("---")

                return {"posts": extracted_posts, "urls": urls}

    async def _summarize_posts_async(self, hacker_news_data):
        """Summarizes Hacker News posts using AI."""
        content_list = []
        tasks = [self._summarize_text(post["title"], post["selftext"], post["url"]) for post in hacker_news_data["posts"]]
        summaries = await asyncio.gather(*tasks, return_exceptions=True)

        for summary in summaries:
            content_list.append(summary)

        return "\n".join(content_list)

    async def _summarize_text(self, title, text, url):
        """Uses AI to summarize post content asynchronously."""
        if not text:
            text, content_type = await self._fetch_page_content_async(url)
            if not text:
                return f"Title: {title}\nURL: {url}\nSRC: {self.srcname}\nSnippet: - \n"
        try:
            return f"{self.config.FETCHER_START_OF_CONTENT}\nTitle: {title}\nURL: {url}\nSRC: {self.srcname}\nSnippet: {text}\n{self.config.FETCHER_END_OF_CONTENT}\n"

        except Exception as e:
            self.config.logprint.error(f"Error summarizing text: {str(e)}")
            return f"{self.config.FETCHER_START_OF_CONTENT}\nTitle: {title}\nURL: {url}\nSRC: {self.srcname}\nSnippet: - \n{self.config.FETCHER_END_OF_CONTENT}\n"

    async def _fetch_page_content_async(self, url):
        def blocking_fetch():
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '')

                if 'application/pdf' in content_type:
                    pdf_reader = PdfReader(BytesIO(response.content))
                    pdf_text = "".join(page.extract_text() for page in pdf_reader.pages)
                    return pdf_text[:self.config.BING_SEARCH_MAX_CONTENT_LENGTH], "PDF"
                elif 'text/html' in content_type:
                    soup = BeautifulSoup(response.content, 'lxml')
                    text = soup.get_text(separator='\n', strip=True)
                    return text[:self.config.BING_SEARCH_MAX_CONTENT_LENGTH], "HTML"
                elif content_type.startswith('image/'):
                    base64_img = base64.b64encode(response.content).decode('utf-8')
                    data_url = f"data:{content_type};base64,{base64_img}"
                    return data_url, "Image"
                else:
                    return None, "Unsupported"

            except Exception as e:
                self.config.logprint.error(f"Error fetching {url}: {str(e)}")
                return None, "Error"

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, blocking_fetch)