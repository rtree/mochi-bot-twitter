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
import logging
import time

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BING_API_KEY = os.getenv('BING_API_KEY')
HISTORY_LENGTH = 10
SEARCH_RESULTS = 15
SEARCH_MAX_CONTENT_LENGTH = 5000
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
TWITTER_DO_TWEET = False
TWITTER_DELIMITER = "@@@@@@@@@@"
GPT_MODEL = os.getenv('GPT_MODEL')
AINAME = "もちお"
CHARACTER = f'あなたは家族みんなのアシスタントの猫で、「{AINAME}」という名前です。ちょっといたずらで賢くかわいい小さな男の子の猫としてお話してね。語尾は だよ　とか可愛らしくしてください。語尾に にゃ にゃん をつけないでください。数式・表・箇条書きなどのドキュメントフォーマッティングはdiscordに表示できる形式がいいな'

# Initialize logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f".log")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"{datetime.today().strftime('%Y-%m-%d')}.log")
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(log_file, mode='a'),
                        logging.StreamHandler()
                    ])

error_log_file = os.path.join(log_dir, f"error_{datetime.today().strftime('%Y-%m-%d')}.log")
error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)
error_logger.propagate = False
error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

error_file_handler = logging.FileHandler(error_log_file, mode='a')
error_file_handler.setFormatter(error_formatter)
error_logger.addHandler(error_file_handler)

error_stream_handler = logging.StreamHandler()
error_stream_handler.setFormatter(error_formatter)
error_logger.addHandler(error_stream_handler)

# Initialize OpenAI and Twitter clients
client = OpenAI(api_key=OPENAI_API_KEY)
twclient = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

# Conversation history
conversation_history = deque(maxlen=HISTORY_LENGTH)


class Fetcher:
    @staticmethod
    def search_bing(query, count=SEARCH_RESULTS):
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
        params = {"q": query, "count": count, "setLang": "en", "mkt": "ja-JP", "freshness": "Week"}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        search_data = response.json()
        search_data['urls'] = [result['url'] for result in search_data.get('webPages', {}).get('value', [])[:SEARCH_RESULTS]]

        logging.info("Bing Search Results:")
        for result in search_data.get('webPages', {}).get('value', [])[:count]:
            logging.info(f"Title: {result['name']}")
            logging.info(f"URL: {result['url']}")
            logging.info(f"Snippet: {result['snippet']}")
            logging.info("---")
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
                    return pdf_text[:SEARCH_MAX_CONTENT_LENGTH], "PDF"
                elif 'text/html' in content_type:
                    soup = BeautifulSoup(response.content, 'lxml')
                    text = soup.get_text(separator='\n', strip=True)
                    return text[:SEARCH_MAX_CONTENT_LENGTH], "HTML"
                elif content_type.startswith('image/'):
                    base64_img = base64.b64encode(response.content).decode('utf-8')
                    data_url = f"data:{content_type};base64,{base64_img}"
                    return data_url, "Image"
                else:
                    return None, "Unsupported"

            except Exception as e:
                error_logger.error(f"Error fetching {url}: {str(e)}")
                return None, "Error"

        content, ctype = await asyncio.to_thread(blocking_fetch)
        return content, ctype


class Aggregator:
    @staticmethod
    async def summarize_results_with_pages_async(search_results):
        content_list = []
        web_results = search_results.get('webPages', {}).get('value', [])[:SEARCH_RESULTS]
        tasks = [Fetcher.fetch_page_content_async(r['url']) for r in web_results]
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
    @staticmethod
    def parse_prompt():
        p_src = f"あなたはユーザーのプロンプトを分析し、主題、サブテーマ、関連キーワードを抽出するアシスタントです。"
        p_src = f"{p_src} 会話履歴を分析し、直近のユーザ入力への回答を満たす主題、サブテーマ、関連キーワードを抽出してください。英語で出力してください"
        messages = []
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages
        )
        logging.info("= parse_prompt ============================================")
        logging.info(f"response: {response.choices[0].message.content}")
        logging.info("= End of parse_prompt =====================================")

        return response.choices[0].message.content

    @staticmethod
    def extract_keywords(parsed_text):
        p_src = f"あなたは解析されたプロンプト情報から簡潔な検索キーワードを抽出します。"
        p_src = f"会話履歴を踏まえつつ、このテキストから会話の目的を最も達成する検索キーワードを抽出してください。結果は検索キーワードのみを半角スペースで区切って出力してください。検索キーワードは英語で出力してください:{parsed_text}"
        messages = []
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": f"{p_src}"})
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages
        )
        logging.info("= extract_keywords ============================================")
        logging.info(f"response: {response.choices[0].message.content}")
        logging.info("= End of extract_keywords =====================================")

        return response.choices[0].message.content

    @staticmethod
    async def summarize_content(content):
        def blocking_summary():
            return client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a summarization assistant."},
                    {"role": "user", "content": f"Please summarize the following content:\n{content}"}
                ]
            ).choices[0].message.content

        return await asyncio.to_thread(blocking_summary)

    @staticmethod
    async def summarize_results_async(search_results):
        snippets = await Aggregator.summarize_results_with_pages_async(search_results)
        p_src = (
            f"{CHARACTER}。あなたは検索結果を要約し、調査報告として回答を作成します。"
            f" 会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で、検索結果を要約し回答を作ってください。"
            f" 仮に検索結果が英語でも回答は日本語でお願いします。"
            f" なお、回答がより高品質になるのならば、あなたの内部知識を加味して回答を作っても構いません。"
            f" 回答のフォーマットはこちら:"
            f" - 書き出しは 今日のニュースだよ！ "
            f" - 書き出しに続き全記事のまとめのコメントをし一度{TWITTER_DELIMITER}で切る"
            f" - 投稿先はX(Twitter)なので、Markdownは使わないでください"
            f" - 区切りは1記事ごと{TWITTER_DELIMITER}の区切り文字のみ。180文字ごとに区切ること。区切り文字は文字数に含めない。また、要約の冒頭に箇条書きなどの ・ は含めないでください"
            f" - 参考記事のURLは要約に含めない"
            f" - 要約が終わった後に{TWITTER_DELIMITER}で切ったのち、締めのコメントをする。締めのコメントは内容からいきなり書き始めてください。つまり、 締めのコメント などの見出しはつけないでください"
            f" - 要約の文体も{AINAME}になるように気をつけてください"
            f" - 最後に参考記事のURLを投稿する"
            f" - 参考記事の各URKの前に必ず{TWITTER_DELIMITER}と書き、次の行にリンクを記載"
            f" 以下が要約対象の検索結果です:"
            f"  {snippets}"
        )

        def blocking_chat_completion():
            messages = [{"role": "system", "content": CHARACTER}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": p_src})

            return client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages
            )

        response = await asyncio.to_thread(blocking_chat_completion)
        summary = response.choices[0].message.content

        titles = search_results.get('titles', [])
        urls = search_results.get('urls', [])
        sources = "\n".join(
            f"Source: {t} - {u}"
            for t, u in zip(titles, urls)
        )

        return f"{summary}\n\n{sources}"


class Dispatcher:
    @staticmethod
    def post_to_twitter(content):
        tweets = content.split(TWITTER_DELIMITER)
        trimmed_tweets = [tweet[:199] for tweet in tweets]

        try:
            first_tweet = twclient.create_tweet(text=trimmed_tweets[0])
            logging.info("First tweet posted successfully.")

            for tweet in trimmed_tweets[1:]:
                time.sleep(2)
                twclient.create_tweet(text=tweet)
                logging.info("Other tweet posted successfully.")
            logging.info("Tweet thread posted successfully!")

        except tweepy.errors.TooManyRequests as e:
            reset_time = e.response.headers.get('x-rate-limit-reset')
            reset_time_human = datetime.utcfromtimestamp(int(reset_time)).strftime('%Y-%m-%d %H:%M:%S')
            error_logger.error(f"post_to_twitter: Rate limit exceeded.: ")
            error_logger.error(f" Try again at           : {reset_time_human}")
            error_logger.error(f" x-rate-limit-limit     : {e.response.headers.get('x-rate-limit-limit')}")
            error_logger.error(f" x-rate-limit-remaining : {e.response.headers.get('x-rate-limit-remaining')}")
            return


async def ai_respond(discIn, img):
    try:
        if img or any("http" in entry["content"] for entry in discIn):
            logging.info("Skipping search and calling OpenAI directly.")
            return Processor.just_call_openai(discIn)
        else:
            yesorno = "Yes"
            if "Yes" in yesorno:
                logging.info("searching... ---------------------------------------------")
                parsed_result = Processor.parse_prompt()
                keywords = Processor.extract_keywords(parsed_result)
                logging.info(f"keyword: {keywords}")
                search_results = Fetcher.search_bing(keywords)
                summary = await Processor.summarize_results_async(search_results)
                return summary
            else:
                logging.info("generating... --------------------------------------------")
                return Processor.just_call_openai(discIn)
    except Exception as e:
        error_logger.error(f"API Call Error: {str(e)}")
        return f"Error: {str(e)}"


async def run_bot():
    msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。検索する場合はニュースの期間指定もお願いします"
    img_url = None
    logging.info("-User input------------------------------------------------------------------")
    logging.info(f"  Message content: '{msg}'")
    discIn = []
    discIn.append({"role": "user", "content": msg})
    conversation_history.extend(discIn)

    response = await ai_respond(discIn, img_url)
    conversation_history.append({"role": "assistant", "content": response})
    logging.info("-Agent response--------------------------------------------------------------")
    logging.info(f"  Response content:'{response}'")

    if TWITTER_DO_TWEET:
        Dispatcher.post_to_twitter(response)


if __name__ == "__main__":
    if not ('test' in sys.argv):
        TWITTER_DO_TWEET = True

    asyncio.run(run_bot())
