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
        self.aiclient = OpenAI(api_key=config.OPENAI_API_KEY)  # OpenAI API
        self.headers = {"User-Agent": "YourApp/1.0 (by YourRedditUsername)"}
        self.access_token = None

    async def fetch(self):
        """ Fetch Reddit trending posts, extract key content, and summarize. """
        today = datetime.today().strftime('%Y-%m-%d')
        msg = f"今日のRedditのトレンド ({today}) をまとめます。ジャンル: 経済・テクノロジー"

        self.config.logprint.info("-User input------------------------------------------------------------------")
        self.config.logprint.info(f"  Message content: '{msg}'")

        # Get OAuth Token
        await self._authenticate()

        # Fetch Reddit Data
        reddit_data = await self._search_reddit()
        if not reddit_data:
            self.config.logprint.error("No data fetched from Reddit.")
            return "Redditからデータを取得できませんでした。"

        fetched_summaries = await self._summarize_results_with_pages_async(reddit_data)
        urls = reddit_data['urls']
        return fetched_summaries, urls

    async def _authenticate(self):
        """ Get OAuth token for Reddit API. """
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
        """ Fetch top posts from Reddit API with authentication. """
        url = "https://oauth.reddit.com/r/technology/top"
        params = {"limit": 10}
        
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
                        "selftext": post_data.get("selftext", ""),
                        "comments_url": f"https://www.reddit.com{post_data.get('permalink')}",
                    })
                    urls.append(post_data.get("url"))

                return {"posts": extracted_posts, "urls": urls}

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
                self.config.elogprint.error(f"Error fetching {url}: {str(e)}")
                return None, "Error"

        content, ctype = await asyncio.to_thread(blocking_fetch)
        return content, ctype

    async def _summarize_text(self, text):
        """ Uses AI to summarize text asynchronously. """
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
