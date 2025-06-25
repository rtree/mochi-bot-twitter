# bingFetcher.py
import asyncio
import base64
import requests
import time
from datetime import datetime
from PyPDF2 import PdfReader
from io import BytesIO
from bs4 import BeautifulSoup
from openai import OpenAI
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import BingGroundingTool, AgentThreadCreationOptions, ListSortOrder
from azure.core.credentials import AzureKeyCredential

class BingFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.aiclient = OpenAI(api_key=config.OPENAI_API_KEY)
        self.srcname = "Bing"

    async def fetch(self):
        msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。目先の細かな動きよりも、世の中を大きく動かす可能性があるものやインパクトが大きいものを知りたいです。"
        self.config.logprint.info("-User input------------------------------------------------------------------")
        self.config.logprint.info(f"  Message content: '{msg}'")
        self.context.extend([{"role": "user", "content": msg}])

        parsed_result = self._parse_prompt()
        keywords = self._extract_keywords(parsed_result)
        self.config.logprint.info(f"keyword: {keywords}")

        search_results = self._search_bing(keywords)
        fetched = await self._summarize_results_with_pages_async(search_results)

        urls = [result['url'] for result in search_results.get('webPages', {}).get('value', [])]
        return fetched, urls

    def _parse_prompt(self):
        prompt = (
            "あなたはユーザーのプロンプトを分析し、主題、サブテーマ、関連キーワードを抽出するアシスタントです。"
            "会話履歴を分析し、直近のユーザ入力への回答を満たす主題、サブテーマ、関連キーワードを抽出してください。英語で出力してください"
        )
        # Use extend instead of concatenation
        messages = list(self.context)  # Convert deque to list
        messages.append({"role": "user", "content": prompt})
        response = self.aiclient.chat.completions.create(
            model=self.config.OPENAI_GPT_MODEL,
            messages=messages
        )
        content = response.choices[0].message.content
        self.config.logprint.info("= parse_prompt ============================================")
        self.config.logprint.info(f"response: {content}")
        self.config.logprint.info("= End of parse_prompt =====================================")
        return content

    def _extract_keywords(self, parsed_text):
        prompt = (
            f"あなたは解析されたプロンプト情報から簡潔な検索キーワードを抽出します。"
            f"会話履歴を踏まえつつ、このテキストから会話の目的を最も達成する検索キーワードを抽出してください。"
            f"結果は検索キーワードのみを半角スペースで区切って出力してください。検索キーワードは英語で出力してください:{parsed_text}"
        )
        # Use extend to add the new message to the deque
        self.context.extend([{"role": "user", "content": prompt}])
        response = self.aiclient.chat.completions.create(
            model=self.config.OPENAI_GPT_MODEL,
            messages=list(self.context)  # Convert deque to list for API call
        )
        content = response.choices[0].message.content
        self.config.logprint.info("= extract_keywords ============================================")
        self.config.logprint.info(f"response: {content}")
        self.config.logprint.info("= End of extract_keywords =====================================")
        return content

    def _search_bing(self, query, count=None):
        count = count or self.config.BING_SEARCH_RESULTS

        credential = AzureKeyCredential(self.config.AZURE_PROJECT_API_KEY)
        client = AgentsClient(endpoint=self.config.AZURE_PROJECT_ENDPOINT, credential=credential)

        # Use predefined agent ID from configuration
        predefined_agent_id = self.config.AZURE_AGENT_ID

        thread = AgentThreadCreationOptions(messages=[{"role": "user", "content": query}])
        run = client.create_thread_and_run(agent_id=predefined_agent_id, thread=thread)

        while run.status not in ["completed", "failed", "canceled", "cancelled"]:
            time.sleep(1)
            run = client.runs.get(run_id=run.id, thread_id=run.thread_id)

        messages = list(client.messages.list(thread_id=run.thread_id, order=ListSortOrder.ASCENDING))

        search_data = {"webPages": {"value": []}, "urls": []}
        for msg in messages:
            if msg.role != "agent":
                continue
            text_content = "\n".join(t.text.value for t in msg.text_messages)
            for ann in msg.url_citation_annotations or []:
                url = ann.url_citation.url
                title = ann.url_citation.title or ""
                search_data["webPages"]["value"].append({"name": title, "url": url, "snippet": text_content})
                search_data["urls"].append(url)

        self.config.logprint.info("Bing Search Results:")
        for result in search_data["webPages"]["value"][:count]:
            self.config.logprint.info(f"Title: {result['name']}")
            self.config.logprint.info(f"URL: {result['url']}")
            self.config.logprint.info(f"Snippet: {result['snippet']}")
            self.config.logprint.info("---")

        return search_data

    async def _summarize_results_with_pages_async(self, search_results):
        content_list = []
        web_results = search_results.get("webPages", {}).get("value", [])[:self.config.BING_SEARCH_RESULTS]
        tasks = [self._fetch_page_content_async(r["url"]) for r in web_results]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

        for r, page_result in zip(web_results, pages):
            title = r["name"]
            snippet = r["snippet"]
            url = r["url"]

            if isinstance(page_result, Exception):
                content_list.append(f"{self.config.FETCHER_START_OF_CONTENT}\nタイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\nSRC: {self.srcname}\n{self.config.FETCHER_END_OF_CONTENT}\n")
                continue

            page_content, content_type = page_result
            if content_type in ("HTML", "PDF") and page_content:
                content_list.append(f"{self.config.FETCHER_START_OF_CONTENT}\nタイトル: {title}\nURL: {url}\n内容:\n{page_content}\nSRC: {self.srcname}\n{self.config.FETCHER_END_OF_CONTENT}\n")
            else:
                content_list.append(f"{self.config.FETCHER_START_OF_CONTENT}\nタイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\nSRC: {self.srcname}\n{self.config.FETCHER_END_OF_CONTENT}\n")
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

