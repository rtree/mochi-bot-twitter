import asyncio
import base64
import requests
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
        #msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。検索する場合はニュースの期間指定もお願いします"
        msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。目先の細かな動きよりも、世の中を大きく動かす可能性があるものやインパクトが大きいものを知りたいです。"
        img_url = None
        self.config.logprint.info("-User input------------------------------------------------------------------")
        self.config.logprint.info(f"  Message content: '{msg}'")
        discIn = []
        discIn.append({"role": "user", "content": msg})
        self.context.extend(discIn)

        parsed_result  = self._parse_prompt()
        keywords       = self._extract_keywords(parsed_result)
        self.config.logprint.info(f"keyword: {keywords}")
        search_results = self._search_bing(keywords)
        fetched = await self._summarize_results_with_pages_async(search_results)

        # Extract URLs from search results
        urls = [result['url'] for result in search_results.get('webPages', {}).get('value', [])]

        return fetched, urls

    def _parse_prompt(self):
        p_src = f"あなたはユーザーのプロンプトを分析し、主題、サブテーマ、関連キーワードを抽出するアシスタントです。"
        p_src = f"{p_src} 会話履歴を分析し、直近のユーザ入力への回答を満たす主題、サブテーマ、関連キーワードを抽出してください。英語で出力してください"
        messages = []
        messages.extend(self.context)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = self.aiclient.chat.completions.create(
            model=self.config.OPENAI_GPT_MODEL,
            messages=messages
        )
        self.config.logprint.info("= parse_prompt ============================================")
        self.config.logprint.info(f"response: {response.choices[0].message.content}")
        self.config.logprint.info("= End of parse_prompt =====================================")

        return response.choices[0].message.content

    def _extract_keywords(self, parsed_text):
        p_src = f"あなたは解析されたプロンプト情報から簡潔な検索キーワードを抽出します。"
        p_src = f"会話履歴を踏まえつつ、このテキストから会話の目的を最も達成する検索キーワードを抽出してください。結果は検索キーワードのみを半角スペースで区切って出力してください。検索キーワードは英語で出力してください:{parsed_text}"
        messages = []
        messages.extend(self.context)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = self.aiclient.chat.completions.create(
            model=self.config.OPENAI_GPT_MODEL,
            messages=messages
        )
        self.config.logprint.info("= extract_keywords ============================================")
        self.config.logprint.info(f"response: {response.choices[0].message.content}")
        self.config.logprint.info("= End of extract_keywords =====================================")

        return response.choices[0].message.content

    def _search_bing(self, query, count=None):
        if count is None:
            count = self.config.BING_SEARCH_RESULTS
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.config.BING_API_KEY}
        params = {"q": query, "count": count, "setLang": "en", "mkt": "ja-JP", "freshness": "Week"}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        search_data = response.json()
        search_data['urls'] = [result['url'] for result in search_data.get('webPages', {}).get('value', [])[:self.config.BING_SEARCH_RESULTS]]

        self.config.logprint.info("Bing Search Results:")
        for result in search_data.get('webPages', {}).get('value', [])[:count]:
            self.config.logprint.info(f"Title: {result['name']}")
            self.config.logprint.info(f"URL: {result['url']}")
            self.config.logprint.info(f"Snippet: {result['snippet']}")
            self.config.logprint.info("---")
        return search_data

    async def _summarize_results_with_pages_async(self, search_results):
        content_list = []
        web_results = search_results.get('webPages', {}).get('value', [])[:self.config.BING_SEARCH_RESULTS]
        tasks = [self._fetch_page_content_async(r['url']) for r in web_results]
        pages = await asyncio.gather(*tasks, return_exceptions=True)
        for (r, page_result) in zip(web_results, pages):
            title = r['name']
            snippet = r['snippet']
            url = r['url']
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

