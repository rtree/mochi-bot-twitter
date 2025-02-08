import asyncio
import base64
import requests
from datetime import datetime
from PyPDF2 import PdfReader
from io import BytesIO
from bs4 import BeautifulSoup

class RedditFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config

    async def fetch(self):
        msg = f"今日のRedditのトレンドをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。"
        self.config.logprint.info("-User input------------------------------------------------------------------")
        self.config.logprint.info(f"  Message content: '{msg}'")
        discIn = []
        discIn.append({"role": "user", "content": msg})
        self.context.extend(discIn)

        search_results = self.search_reddit()
        search_results = await self.summarize_results_with_pages_async(search_results)

        return search_results

    def search_reddit(self):
        url = "https://www.reddit.com/r/technology/top/.json?count=10"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        search_data = response.json()
        search_data['urls'] = [post['data']['url'] for post in search_data['data']['children']]

        self.config.logprint.info("Reddit Search Results:")
        for post in search_data['data']['children']:
            self.config.logprint.info(f"Title: {post['data']['title']}")
            self.config.logprint.info(f"URL: {post['data']['url']}")
            self.config.logprint.info(f"Snippet: {post['data']['selftext']}")
            self.config.logprint.info("---")
        return search_data

    async def fetch_page_content_async(self, url):
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
    
    async def summarize_results_with_pages_async(self, search_results):
        content_list = []
        web_results = search_results['urls']
        tasks = [self.fetch_page_content_async(url) for url in web_results]
        pages = await asyncio.gather(*tasks, return_exceptions=True)
        for (url, page_result) in zip(web_results, pages):
            title = url
            snippet = ""
            if isinstance(page_result, Exception):
                content_list.append(f"タイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\n")
                continue
            page_content, content_type = page_result
            if content_type in ("HTML", "PDF") and page_content:
                content_list.append(f"タイトル: {title}\nURL: {url}\n内容:\n{page_content}\n")
            else:
                content_list.append(f"タイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\n")
        return "\n".join(content_list)
