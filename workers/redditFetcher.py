import asyncio
import base64
import requests
from datetime import datetime
from PyPDF2 import PdfReader
from io import BytesIO
from bs4 import BeautifulSoup
import aiohttp
from openai import OpenAI  # Ensure you have OpenAI installed

from collections import deque
from config import Config

class RedditFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.aiclient = OpenAI(api_key=config.OPENAI_API_KEY)  # OpenAI client
        self.reddit_api_url = "https://www.reddit.com/r/technology/top/.json?limit=10"
        self.headers = {"User-Agent": "YourApp/1.0 (by YourRedditUsername)"}

    async def fetch(self):
        """ Fetch trending Reddit posts, extract key content, and summarize. """
        today = datetime.today().strftime('%Y-%m-%d')
        msg = f"今日のRedditのトレンド ({today}) をまとめます。ジャンル: 経済・テクノロジー"

        self.config.logprint.info("-User input------------------------------------------------------------------")
        self.config.logprint.info(f"  Message content: '{msg}'")

        reddit_data = await self._search_reddit()
        if not reddit_data:
            self.config.logprint.error("No data fetched from Reddit.")
            return "Redditからデータを取得できませんでした。"

        fetched_summaries = await self._summarize_results_with_pages_async(reddit_data)

        urls = reddit_data['urls']  # Extract URLs for reference
        return fetched_summaries, urls

    async def _search_reddit(self):
        """ Fetch trending posts from Reddit API asynchronously. """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.reddit_api_url, headers=self.headers) as response:
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
                            "selftext": post_data.get("selftext", ""),
                            "comments_url": f"https://www.reddit.com{post_data.get('permalink')}",
                        })
                        urls.append(post_data.get("url"))
                    
                    return {"posts": extracted_posts, "urls": urls}
            except Exception as e:
                self.config.logprint.error(f"Error fetching Reddit posts: {str(e)}")
                return None

    async def _fetch_page_content_async(self, url):
        """ Fetches page content asynchronously for summarization. """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return None, "Error"
                    
                    content_type = response.headers.get('Content-Type', '')

                    if 'application/pdf' in content_type:
                        pdf_reader = PdfReader(BytesIO(await response.read()))
                        pdf_text = "".join(page.extract_text() for page in pdf_reader.pages)
                        return pdf_text[:3000], "PDF"
                    elif 'text/html' in content_type:
                        soup = BeautifulSoup(await response.text(), 'lxml')
                        text = soup.get_text(separator='\n', strip=True)
                        return text[:3000], "HTML"
                    elif content_type.startswith('image/'):
                        base64_img = base64.b64encode(await response.read()).decode('utf-8')
                        data_url = f"data:{content_type};base64,{base64_img}"
                        return data_url, "Image"
                    else:
                        return None, "Unsupported"

            except Exception as e:
                self.config.elogprint.error(f"Error fetching {url}: {str(e)}")
                return None, "Error"

    async def _summarize_results_with_pages_async(self, search_results):
        """ Summarizes Reddit posts using AI. """
        content_list = []
        web_results = search_results['urls']
        tasks = [self._fetch_page_content_async(url) for url in web_results]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

        for (post, page_result) in zip(search_results["posts"], pages):
            title = post["title"]
            url = post["url"]
            snippet = post["selftext"][:500] if post["selftext"] else ""

            if isinstance(page_result, Exception):
                content_list.append(f"📰 {title}\n🔗 {url}\n📌 Snippet: {snippet}\n")
                continue
            
            page_content, content_type = page_result
            if content_type in ("HTML", "PDF") and page_content:
                summary = await self._summarize_text(page_content)
                content_list.append(f"📰 {title}\n🔗 {url}\n📌 Summary: {summary}\n")
            else:
                content_list.append(f"📰 {title}\n🔗 {url}\n📌 Snippet: {snippet}\n")
        
        return "\n".join(content_list)

    async def _summarize_text(self, text):
        """ Uses AI (via OpenAI) to summarize text asynchronously. """
        try:
            messages = [{"role": "user", "content": f"Summarize this article in 280 characters: {text}"}]
            response = await self.aiclient.chat.completions.create(
                model=self.config.OPENAI_GPT_MODEL,
                messages=messages
            )
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            self.config.logprint.error(f"Error summarizing text: {str(e)}")
            return "Summary unavailable."

if __name__ == "__main__":
    config = Config()  # Instantiate Config
    context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
    fetcher = RedditFetcher(context, config)
    summaries, urls = asyncio.run(fetcher.fetch())
    print(summaries)  # Print summarized Reddit posts
    print(urls)       # Print extracted post URLs
