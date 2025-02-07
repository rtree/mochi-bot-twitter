import os
import requests
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from io import BytesIO
import logging
from dotenv import load_dotenv

load_dotenv()
BING_API_KEY = os.getenv('BING_API_KEY')

class Fetcher:
    """Fetches information from various sources."""

    async def fetch():
        """Fetches, processes, and summarizes results."""
        search_results = await _self.fetch_bing(query)
        content_list = []

        tasks = [fetcher.fetch_page_content(url) for url in search_results['urls']]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

        for (url, page_result) in zip(search_results['urls'], pages):
            if isinstance(page_result, Exception):
                continue
            page_content, content_type = page_result
            if content_type in ("HTML", "PDF") and page_content:
                content_list.append(page_content)

        return "\n".join(content_list)

    async def fetch_bing(self, query, count=15):
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
        params = {"q": query, "count": count, "setLang": "en", "mkt": "ja-JP", "freshness": "Week"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                return await response.json()

    async def fetch_page_content(self, url):
        """Fetches content of a webpage asynchronously."""
        def blocking_fetch():
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '')

                if 'application/pdf' in content_type:
                    pdf_reader = PdfReader(BytesIO(response.content))
                    return "".join(page.extract_text() for page in pdf_reader.pages), "PDF"
                elif 'text/html' in content_type:
                    soup = BeautifulSoup(response.content, 'lxml')
                    return soup.get_text(separator='\n', strip=True), "HTML"
                else:
                    return None, "Unsupported"
            except Exception as e:
                logging.error(f"Error fetching {url}: {str(e)}")
                return None, "Error"

        return await asyncio.to_thread(blocking_fetch)
