import os
import tweepy
from dotenv import load_dotenv
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
from collections import deque
import asyncio
from datetime import datetime
import lxml
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

# Conversation history
conversation_history = deque(maxlen=Config.HISTORY_LENGTH)


class Fetcher:
    def __init__(self):
        self.conversation_history = deque(maxlen=Config.HISTORY_LENGTH)

    async def fetch(self):
        msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。検索する場合はニュースの期間指定もお願いします"
        img_url = None
        Config.logprint.info("-User input------------------------------------------------------------------")
        Config.logprint.info(f"  Message content: '{msg}'")
        discIn = []
        discIn.append({"role": "user", "content": msg})
        self.conversation_history.extend(discIn)

        Config.logprint.info("searching... ---------------------------------------------")
        parsed_result  = self.parse_prompt()
        keywords       = self.extract_keywords(parsed_result)
        Config.logprint.info(f"keyword: {keywords}")
        search_results = self.search_bing(keywords)
        search_results = await self.summarize_results_with_pages_async(search_results)

        return search_results

    def parse_prompt(self):
        p_src = f"あなたはユーザーのプロンプトを分析し、主題、サブテーマ、関連キーワードを抽出するアシスタントです。"
        p_src = f"{p_src} 会話履歴を分析し、直近のユーザ入力への回答を満たす主題、サブテーマ、関連キーワードを抽出してください。英語で出力してください"
        messages = []
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=messages
        )
        Config.logprint.info("= parse_prompt ============================================")
        Config.logprint.info(f"response: {response.choices[0].message.content}")
        Config.logprint.info("= End of parse_prompt =====================================")

        return response.choices[0].message.content

    def extract_keywords(self, parsed_text):
        p_src = f"あなたは解析されたプロンプト情報から簡潔な検索キーワードを抽出します。"
        p_src = f"会話履歴を踏まえつつ、このテキストから会話の目的を最も達成する検索キーワードを抽出してください。結果は検索キーワードのみを半角スペースで区切って出力してください。検索キーワードは英語で出力してください:{parsed_text}"
        messages = []
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=messages
        )
        Config.logprint.info("= extract_keywords ============================================")
        Config.logprint.info(f"response: {response.choices[0].message.content}")
        Config.logprint.info("= End of extract_keywords =====================================")

        return response.choices[0].message.content

    def search_bing(self, query, count=Config.SEARCH_RESULTS):
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

    async def fetch_page_content_async(self, url):
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
    
    async def summarize_results_with_pages_async(self, search_results):
        content_list = []
        web_results = search_results.get('webPages', {}).get('value', [])[:Config.SEARCH_RESULTS]
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
    def __init__(self):
        self.conversation_history = deque(maxlen=Config.HISTORY_LENGTH)

    async def summarize_results_async(self, snippets):
        p_src = (
            f"{Config.CHARACTER}。あなたは検索結果を要約し、調査報告として回答を作成します。"
            f" 会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で、検索結果を要約し回答を作ってください。"
            f" 仮に検索結果が英語でも回答は日本語でお願いします。"
            f" なお、回答がより高品質になるのならば、あなたの内部知識を加味して回答を作っても構いません。"
            f" 回答のフォーマットはこちら:"
            f" - 書き出しは 今日のニュースだよ！ "
            f" - 書き出しに続き全記事のまとめのコメントをし一度{Config.TWITTER_DELIMITER}で切る"
            f" - 投稿先はX(Twitter)なので、Markdownは使わないでください"
            f" - 区切りは1記事ごと{Config.TWITTER_DELIMITER}の区切り文字のみ。180文字ごとに区切ること。区切り文字は文字数に含めない。また、要約の冒頭に箇条書きなどの ・ は含めないでください"
            f" - 参考記事のURLは要約に含めない"
            f" - 要約が終わった後に{Config.TWITTER_DELIMITER}で切ったのち、締めのコメントをする。締めのコメントは内容からいきなり書き始めてください。つまり、 締めのコメント などの見出しはつけないでください"
            f" - 要約の文体も{Config.AINAME}になるように気をつけてください"
            f" - 最後に参考記事のURLを投稿する"
            f" - 参考記事の各URKの前に必ず{Config.TWITTER_DELIMITER}と書き、次の行にリンクを記載"
            f" 以下が要約対象の検索結果です:"
            f"  {snippets}"
        )

        def blocking_chat_completion():
            messages = [{"role": "system", "content": Config.CHARACTER}]
            messages.extend(self.conversation_history)
            messages.append({"role": "user", "content": p_src})

            return client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=messages
            )

        response = await asyncio.to_thread(blocking_chat_completion)
        summary = response.choices[0].message.content

        return f"{summary}"


class Dispatcher:
    def __init__(self):
        self.twclient = tweepy.Client(
            bearer_token=Config.TWITTER_BEARER_TOKEN,
            consumer_key=Config.TWITTER_API_KEY,
            consumer_secret=Config.TWITTER_API_SECRET,
            access_token=Config.TWITTER_ACCESS_TOKEN,
            access_token_secret=Config.TWITTER_ACCESS_SECRET
        )

    def post_to_twitter(self, content):
        tweets = content.split(Config.TWITTER_DELIMITER)
        trimmed_tweets = [tweet[:199] for tweet in tweets]

        try:
            first_tweet = self.twclient.create_tweet(text=trimmed_tweets[0])
            Config.logprint.info("First tweet posted successfully.")

            for tweet in trimmed_tweets[1:]:
                time.sleep(2)
                self.twclient.create_tweet(text=tweet)
                Config.logprint.info("Other tweet posted successfully.")
            Config.logprint.info("Tweet thread posted successfully!")

        except tweepy.errors.TooManyRequests as e:
            reset_time = e.response.headers.get('x-rate-limit-reset')
            reset_time_human = datetime.utcfromtimestamp(int(reset_time)).strftime('%Y-%m-%d %H:%M:%S')
            Config.elogprint.error(f"post_to_twitter: Rate limit exceeded.: ")
            Config.elogprint.error(f" Try again at           : {reset_time_human}")
            Config.elogprint.error(f" x-rate-limit-limit     : {e.response.headers.get('x-rate-limit-limit')}")
            Config.elogprint.error(f" x-rate-limit-remaining : {e.response.headers.get('x-rate-limit-remaining')}")
            return

async def run_bot():
    try:
        fetcher = Fetcher()  # Instantiate Fetcher
        search_results = await fetcher.fetch()  # Call instance method
        processor = Processor()  # Instantiate Processor
        summary = await processor.summarize_results_async(search_results)

        conversation_history.append({"role": "assistant", "content": summary})
        Config.logprint.info("-Agent summary--------------------------------------------------------------")
        Config.logprint.info(f"  Response content:'{summary}'")

        if Config.TWITTER_DO_TWEET:
            dispatcher = Dispatcher()  # Instantiate Dispatcher
            dispatcher.post_to_twitter(summary)

    except Exception as e:
        Config.elogprint.error(f"API Call Error: {str(e)}")
        return f"Error: {str(e)}"


if __name__ == "__main__":
    if not ('test' in sys.argv):
        Config.TWITTER_DO_TWEET = True

    asyncio.run(run_bot())
