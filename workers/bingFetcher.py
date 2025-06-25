import asyncio
import base64
import requests
import time
from datetime import datetime
from PyPDF2 import PdfReader
from io import BytesIO
from bs4 import BeautifulSoup
from openai import OpenAI


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
        messages = list(self.context)
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
        self.context.extend([{"role": "user", "content": prompt}])
        response = self.aiclient.chat.completions.create(
            model=self.config.OPENAI_GPT_MODEL,
            messages=list(self.context)
        )
        content = response.choices[0].message.content
        self.config.logprint.info("= extract_keywords ============================================")
        self.config.logprint.info(f"response: {content}")
        self.config.logprint.info("= End of extract_keywords =====================================")
        return content

    def _search_bing(self, query, count=None):
        return simulate_bing_grounding_via_rest(query, self.config)

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

        return await asyncio.to_thread(blocking_fetch)


def simulate_bing_grounding_via_rest(query, config):
    endpoint = config.AZURE_PROJECT_ENDPOINT.rstrip("/")
    api_key = config.AZURE_PROJECT_API_KEY
    agent_id = config.AZURE_AGENT_ID
    api_version = "2024-05-15-preview"

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    # 1. Create thread
    thread_resp = requests.post(f"{endpoint}/threads?api-version={api_version}", headers=headers)
    thread_resp.raise_for_status()
    thread_id = thread_resp.json()["id"]

    # 2. Add message
    msg_resp = requests.post(
        f"{endpoint}/threads/{thread_id}/messages?api-version={api_version}",
        headers=headers,
        json={"role": "user", "content": query}
    )
    msg_resp.raise_for_status()

    # 3. Run agent
    run_resp = requests.post(
        f"{endpoint}/threads/{thread_id}/runs?api-version={api_version}",
        headers=headers,
        json={"assistant_id": agent_id}
    )
    run_resp.raise_for_status()
    run_id = run_resp.json()["id"]

    # 4. Poll status
    while True:
        status_resp = requests.get(
            f"{endpoint}/threads/{thread_id}/runs/{run_id}?api-version={api_version}",
            headers=headers
        )
        status_resp.raise_for_status()
        if status_resp.json()["status"] in ["succeeded", "failed", "cancelled"]:
            break
        time.sleep(1)

    # 5. Fetch messages
    messages_resp = requests.get(
        f"{endpoint}/threads/{thread_id}/messages?api-version={api_version}",
        headers=headers
    )
    messages_resp.raise_for_status()
    messages = messages_resp.json().get("value", [])

    # 6. Parse Bing citations
    search_data = {"webPages": {"value": []}, "urls": []}
    for msg in messages:
        if msg["role"] != "assistant":
            continue
        text_content = msg.get("content", "")
        annotations = msg.get("annotations", [])
        for ann in annotations:
            if ann.get("type") == "citation":
                url = ann.get("url")
                title = ann.get("title", "")
                search_data["webPages"]["value"].append({
                    "name": title,
                    "url": url,
                    "snippet": text_content
                })
                search_data["urls"].append(url)

    return search_data
