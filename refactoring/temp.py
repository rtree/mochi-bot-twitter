import tweepy
from dotenv import load_dotenv
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
from collections import deque
import asyncio
from datetime import datetime
from PyPDF2 import PdfReader
from io import BytesIO
import base64
import sys
import time
from config import Config

# Initialize OpenAI and Twitter clients
client = OpenAI(api_key=Config.OPENAI_API_KEY)
twclient = tweepy.Client(
    bearer_token=Config.TWITTER_BEARER_TOKEN,
    consumer_key=Config.TWITTER_API_KEY,
    consumer_secret=Config.TWITTER_API_SECRET,
    access_token=Config.TWITTER_ACCESS_TOKEN,
    access_token_secret=Config.TWITTER_ACCESS_SECRET
)

class Fetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    async def fetch(self):
        msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。検索する場合はニュースの期間指定もお願いします"
        img_url = None
        self.config.logprint.info("-User input------------------------------------------------------------------")
        self.config.logprint.info(f"  Message content: '{msg}'")
        discIn = []
        discIn.append({"role": "user", "content": msg})
        self.context.extend(discIn)

        parsed_result  = self.parse_prompt()
        keywords       = self.extract_keywords(parsed_result)
        self.config.logprint.info(f"keyword: {keywords}")
        search_results = self.search_bing(keywords)
        search_results = await self.summarize_results_with_pages_async(search_results)

        return search_results

    def parse_prompt(self):
        p_src = f"あなたはユーザーのプロンプトを分析し、主題、サブテーマ、関連キーワードを抽出するアシスタントです。"
        p_src = f"{p_src} 会話履歴を分析し、直近のユーザ入力への回答を満たす主題、サブテーマ、関連キーワードを抽出してください。英語で出力してください"
        messages = []
        messages.extend(self.context)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = self.client.chat.completions.create(
            model=self.config.OPENAI_GPT_MODEL,
            messages=messages
        )
        self.config.logprint.info("= parse_prompt ============================================")
        self.config.logprint.info(f"response: {response.choices[0].message.content}")
        self.config.logprint.info("= End of parse_prompt =====================================")

        return response.choices[0].message.content

    def extract_keywords(self, parsed_text):
        p_src = f"あなたは解析されたプロンプト情報から簡潔な検索キーワードを抽出します。"
        p_src = f"会話履歴を踏まえつつ、このテキストから会話の目的を最も達成する検索キーワードを抽出してください。結果は検索キーワードのみを半角スペースで区切って出力してください。検索キーワードは英語で出力してください:{parsed_text}"
        messages = []
        messages.extend(self.context)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = self.client.chat.completions.create(
            model=self.config.OPENAI_GPT_MODEL,
            messages=messages
        )
        self.config.logprint.info("= extract_keywords ============================================")
        self.config.logprint.info(f"response: {response.choices[0].message.content}")
        self.config.logprint.info("= End of extract_keywords =====================================")

        return response.choices[0].message.content

    def search_bing(self, query, count=None):
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
        web_results = search_results.get('webPages', {}).get('value', [])[:self.config.BING_SEARCH_RESULTS]
        tasks = [self.fetch_page_content_async(r['url']) for r in web_results]
        pages = await asyncio.gather(*tasks, return_exceptions=True)
        for (r, page_result) in zip(web_results, pages):
            title = r['name']
            snippet = r['snippet']
            url = r['url']
            if isinstance(page_result, Exception):
                content_list.append(f"タイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\n")
                continue
            page_content, content_type = page_result
            if content_type in ("HTML", "PDF") and page_content:
                content_list.append(f"タイトル: {title}\nURL: {url}\n内容:\n{page_content}\n")
            else:
                content_list.append(f"タイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\n")
        return "\n".join(content_list)

class Processor:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    async def summarize_results_async(self, snippets):
        p_src = (
            f"{self.config.CHARACTER}。あなたは検索結果を要約し、調査報告として回答を作成します。"
            f" 会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で、検索結果を要約し回答を作ってください。"
            f" 仮に検索結果が英語でも回答は日本語でお願いします。"
            f" なお、回答がより高品質になるのならば、あなたの内部知識を加味して回答を作っても構いません。"
            f" 回答のフォーマットはこちら:"
            f" - 書き出しは 今日のニュースだよ！ "
            f" - 書き出しに続き全記事のまとめのコメントをし一度{self.config.TWITTER_DELIMITER}で切る"
            f" - 投稿先はX(Twitter)なので、Markdownは使わないでください"
            f" - 区切りは1記事ごと{self.config.TWITTER_DELIMITER}の区切り文字のみ。180文字ごとに区切ること。区切り文字は文字数に含めない。また、要約の冒頭に箇条書きなどの ・ は含めないでください"
            f" - 参考記事のURLは要約に含めない"
            f" - 要約が終わった後に{self.config.TWITTER_DELIMITER}で切ったのち、締めのコメントをする。締めのコメントは内容からいきなり書き始めてください。つまり、 締めのコメント などの見出しはつけないでください"
            f" - 要約の文体も{self.config.AINAME}になるように気をつけてください"
            f" - 最後に参考記事のURLを投稿する"
            f" - 参考記事の各URKの前に必ず{self.config.TWITTER_DELIMITER}と書き、次の行にリンクを記載"
            f" 以下が要約対象の検索結果です:"
            f"  {snippets}"
        )

        def blocking_chat_completion():
            messages = [{"role": "system", "content": self.config.CHARACTER}]
            messages.extend(self.context)
            messages.append({"role": "user", "content": p_src})

            return self.client.chat.completions.create(
                model=self.config.OPENAI_GPT_MODEL,
                messages=messages
            )

        response = await asyncio.to_thread(blocking_chat_completion)
        summary = response.choices[0].message.content

        return f"{summary}"


class Dispatcher:
    def __init__(self, config):
        self.config = config
        self.twclient = tweepy.Client(
            bearer_token=config.TWITTER_BEARER_TOKEN,
            consumer_key=config.TWITTER_API_KEY,
            consumer_secret=config.TWITTER_API_SECRET,
            access_token=config.TWITTER_ACCESS_TOKEN,
            access_token_secret=config.TWITTER_ACCESS_SECRET
        )

    def post_to_twitter(self, content):
        tweets = content.split(self.config.TWITTER_DELIMITER)
        trimmed_tweets = [tweet[:199] for tweet in tweets]

        try:
            first_tweet = self.twclient.create_tweet(text=trimmed_tweets[0])
            self.config.logprint.info("First tweet posted successfully.")

            for tweet in trimmed_tweets[1:]:
                time.sleep(2)
                self.twclient.create_tweet(text=tweet)
                self.config.logprint.info("Other tweet posted successfully.")
            self.config.logprint.info("Tweet thread posted successfully!")

        except tweepy.errors.TooManyRequests as e:
            reset_time = e.response.headers.get('x-rate-limit-reset')
            reset_time_human = datetime.utcfromtimestamp(int(reset_time)).strftime('%Y-%m-%d %H:%M:%S')
            self.config.elogprint.error(f"post_to_twitter: Rate limit exceeded.: ")
            self.config.elogprint.error(f" Try again at           : {reset_time_human}")
            self.config.elogprint.error(f" x-rate-limit-limit     : {e.response.headers.get('x-rate-limit-limit')}")
            self.config.elogprint.error(f" x-rate-limit-remaining : {e.response.headers.get('x-rate-limit-remaining')}")
            return

async def run_bot():
    try:
        config = Config()  # Instantiate Config
        context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
        fetcher = Fetcher(context, config)  # Instantiate Fetcher with context and config
        search_results = await fetcher.fetch()  # Call instance method
        processor = Processor(context, config)  # Instantiate Processor with context and config
        summary = await processor.summarize_results_async(search_results)

        context.append({"role": "assistant", "content": summary})
        config.logprint.info("-Agent summary--------------------------------------------------------------")
        config.logprint.info(f"  Response content:'{summary}'")

        if config.TWITTER_DO_TWEET:
            dispatcher = Dispatcher(config)  # Instantiate Dispatcher with config
            dispatcher.post_to_twitter(summary)

    except Exception as e:
        config.elogprint.error(f"API Call Error: {str(e)}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
    if not ('test' in sys.argv):
        Config.TWITTER_DO_TWEET = True

    asyncio.run(run_bot())
