import os
import requests
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from io import BytesIO
import logging
from dotenv import load_dotenv
import base64
from datetime import datetime
from config import Config
from openai import OpenAI

load_dotenv()
BING_API_KEY = os.getenv('BING_API_KEY')

client = OpenAI(api_key=Config.OPENAI_API_KEY)

class Fetcher:
    """Fetches information from various sources."""

    @staticmethod
    def parse_prompt():
        p_src = f"あなたはユーザーのプロンプトを分析し、主題、サブテーマ、関連キーワードを抽出するアシスタントです。"
        p_src = f"{p_src} 会話履歴を分析し、直近のユーザ入力への回答を満たす主題、サブテーマ、関連キーワードを抽出してください。英語で出力してください"
        messages = []
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=messages
        )
        Config.logprint.info("= parse_prompt ============================================")
        Config.logprint.info(f"response: {response.choices[0].message.content}")
        Config.logprint.info("= End of parse_prompt =====================================")

        return response.choices[0].message.content

    @staticmethod
    def extract_keywords(parsed_text):
        p_src = f"あなたは解析されたプロンプト情報から簡潔な検索キーワードを抽出します。"
        p_src = f"会話履歴を踏まえつつ、このテキストから会話の目的を最も達成する検索キーワードを抽出してください。結果は検索キーワードのみを半角スペースで区切って出力してください。検索キーワードは英語で出力してください:{parsed_text}"
        messages = []
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=messages
        )
        Config.logprint.info("= extract_keywords ============================================")
        Config.logprint.info(f"response: {response.choices[0].message.content}")
        Config.logprint.info("= End of extract_keywords =====================================")

        return response.choices[0].message.content

    @staticmethod
    def search_bing(query, count=Config.SEARCH_RESULTS):
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": Config.BING_API_KEY}
        params = {"q": query, "count": count, "setLang": "en", "mkt": "ja-JP", "freshness": "Week"}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        search_data = response.json()
        search_data['urls'] = [result['url'] for result in search_data.get('webPages', {}).get('value', [])[:Config.SEARCH_RESULTS]]

        Config.logprint.info("Bing Search Results:")
        for result in search_data.get('webPages', {}).get('value', [])[:count]:
            Config.logprint.info(f"Title: {result['name']}")
            Config.logprint.info(f"URL: {result['url']}")
            Config.logprint.info(f"Snippet: {result['snippet']}")
            Config.logprint.info("---")
        return search_data

    @staticmethod
    async def fetch_page_content_async(url):
        def blocking_fetch():
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '')

                if 'application/pdf' in content_type:
                    pdf_reader = PdfReader(BytesIO(response.content))
                    pdf_text = "".join(page.extract_text() for page in pdf_reader.pages)
                    return pdf_text[:Config.SEARCH_MAX_CONTENT_LENGTH], "PDF"
                elif 'text/html' in content_type:
                    soup = BeautifulSoup(response.content, 'lxml')
                    text = soup.get_text(separator='\n', strip=True)
                    return text[:Config.SEARCH_MAX_CONTENT_LENGTH], "HTML"
                elif content_type.startswith('image/'):
                    base64_img = base64.b64encode(response.content).decode('utf-8')
                    data_url = f"data:{content_type};base64,{base64_img}"
                    return data_url, "Image"
                else:
                    return None, "Unsupported"

            except Exception as e:
                Config.elogprint.error(f"Error fetching {url}: {str(e)}")
                return None, "Error"

        content, ctype = await asyncio.to_thread(blocking_fetch)
        return content, ctype

    @staticmethod
    async def fetch(query):
        parsed_result = Fetcher.parse_prompt()
        keywords = Fetcher.extract_keywords(parsed_result)
        Config.logprint.info(f"keyword: {keywords}")
        search_results = Fetcher.search_bing(keywords)
        search_results = await Aggregator.summarize_results_with_pages_async(search_results)
        return search_results
