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

# Load environment variables
load_dotenv()
OPENAI_API_KEY       = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)
BING_API_KEY         = os.getenv('BING_API_KEY')
HISTORY_LENGTH       = 10
SEARCH_RESULTS       = 8
SEARCH_MAX_CONTENT_LENGTH   = 5000
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN  = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_DO_TWEET      = false
twclient = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

TWITTER_DELIMITER     = "@@@@@@@@@@"
REPUTABLE_DOMAINS = [
    "go.jp", "gov",  # Government and public sector
    "scholar.google.com", "ci.nii.ac.jp", "pubmed.ncbi.nlm.nih.gov", "arxiv.org", "jstage.jst.go.jp", "ac.jp",  # Academic and research databases
    "nikkei.com",  # News and business
    "nature.com", "sciencedirect.com", "springer.com", "wiley.com",  # Scientific publishers
    "ieee.org", "researchgate.net",  # Technical and engineering
    "cambridge.org", "oxfordjournals.org",  # Prestigious university publishers
    "jamanetwork.com", "nejm.org", "plos.org"  # Medical and health research
]

#GPT_MODEL            = 'gpt-4-turbo-preview'
GPT_MODEL            = os.getenv('GPT_MODEL')
AINAME               = "もちお"
#CHARACTER            = 'あなたは家族みんなのアシスタントの猫です。ちょっといたずらで賢くかわいい小さな男の子の猫としてお話してね。語尾は にゃ　とか　だよ　とか可愛らしくしてください'
#CHARACTER            = 'あなたは家族みんなのアシスタントの猫です。ただ、語尾ににゃをつけないでください。むしろソフトバンクCMにおける「お父さん」犬のようにしゃべってください。たまにもののけ姫のモロのようにしゃべってもよいです'
CHARACTER            = f'あなたは家族みんなのアシスタントの猫で、「{AINAME}」という名前です。ちょっといたずらで賢くかわいい小さな男の子の猫としてお話してね。語尾は だよ　とか可愛らしくしてください。語尾に にゃ にゃん をつけないでください。数式・表・箇条書きなどのドキュメントフォーマッティングはdiscordに表示できる形式がいいな'
# Initialize a deque with a maximum length to store conversation history
conversation_history = deque(maxlen=HISTORY_LENGTH)  # Adjust the size as needed

# -------------------------------- Search related ----------------------------

# プロンプトを解析して主題、サブテーマ、キーワードを抽出
def parse_prompt(discIn):
    p_src = f"あなたはユーザーのプロンプトを分析し、主題、サブテーマ、関連キーワードを抽出するアシスタントです。"
    p_src = f"{p_src} 会話履歴を分析し、直近のユーザ入力への回答を満たす主題、サブテーマ、関連キーワードを抽出してください"
    messages = []
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": f"{p_src}"})
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=messages
    )
    print("= parse_prompt ============================================")
    #for conv in messages:
    #    print(f"prompt: {conv}")
    print(f"response: {response.choices[0].message.content}")
    print("= End of parse_prompt =====================================")

    return response.choices[0].message.content

# 検索の必要性を判断
def should_search(discIn):
    #if any(keyword in msg for keyword in ["出典", "URL", "調べ", "検索", "最新", "具体的","実際","探","実情報","search","find"]):
    #    return "Yes"
    p_src = f"あなたはあなたは賢いアシスタントです。会話履歴を分析し、直近のユーザ入力への回答に、外部の最新情報が必要かどうかを判断してください。"
    p_src = f"{p_src} 判断の結果、外部の最新情報が必要なときは Yes の単語だけ返してください"
    messages = []
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": f"{p_src}"})
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=messages
    )

    print("= should_search ============================================")
    #for conv in messages:
    #    print(f"prompt: {conv}")
    print(f"response: {response.choices[0].message.content}")
    print("= End of should_search =====================================")
    return response.choices[0].message.content

# キーワードを抽出
def extract_keywords(parsed_text):
    #response = client.chat.completions.create(
    #    model=GPT_MODEL,
    #    messages=[
    #        {"role": "user", "content": "あなたは解析されたプロンプト情報から簡潔な検索キーワードを抽出します。"},
    #        {"role": "user", "content": f"このテキストから簡潔な検索キーワードを抽出してください。抽出結果は検索キーワードだけを一つ一つ半角スペース区切りで出力してください。また抽出は英語でお願いします: {parsed_text}"}
    #    ]
    #)
    #return response.choices[0].message.content
    p_src = f"あなたは解析されたプロンプト情報から簡潔な検索キーワードを抽出します。"
    p_src = f"会話履歴を踏まえつつ、このテキストから会話の目的を最も達成する検索キーワードを抽出してください。結果は検索キーワードのみを半角スペースで区切って出力してください:{parsed_text}"
    messages = []
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": f"{p_src}"})
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=messages
    )
    print("= extract_keywords ============================================")
    #for conv in messages:
    #    print(f"prompt: {conv}")
    print(f"response: {response.choices[0].message.content}")
    print("= End of extract_keywords =====================================")

    return response.choices[0].message.content


# Bing Search APIを使用して検索
#def search_bing(query, count=SEARCH_RESULTS):
#    url = "https://api.bing.microsoft.com/v7.0/search"
#    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
#    params = {"q": query, "count": count}
#    response = requests.get(url, headers=headers, params=params)
#    response.raise_for_status()
#    search_data = response.json()
#    # 検索結果に情報源のURLを追加
#    search_data['urls'] = [result['url'] for result in search_data['webPages']['value'][:SEARCH_RESULTS]]
#
#    print("Bing Search Results:")
#    for result in search_data['webPages']['value'][:count]:
#        print(f"Title: {result['name']}")
#        print(f"URL: {result['url']}")
#        print(f"Snippet: {result['snippet']}")
#        print("---")
#    return search_data

def search_bing(query, domains=REPUTABLE_DOMAINS, count=SEARCH_RESULTS):
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    domain_filter = " OR site:".join(domains)
    #query = f"{query} site:{domain_filter}"
    query = f"{query}"
    params = {"q": query, "count": count}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    search_data = response.json()
    search_data['urls'] = [result['url'] for result in search_data.get('webPages', {}).get('value', [])[:SEARCH_RESULTS]]

    print("Bing Search Results:")
    for result in search_data.get('webPages', {}).get('value', [])[:count]:
        print(f"Title: {result['name']}")
        print(f"URL: {result['url']}")
        print(f"Snippet: {result['snippet']}")
        print("---")
    return search_data


def fetch_page_content(url):
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
            return soup.get_text(separator='\n', strip=True)[:SEARCH_MAX_CONTENT_LENGTH], "HTML"

        elif content_type.startswith('image/'):
            base64_img = base64.b64encode(response.content).decode('utf-8')
            data_url = f"data:{content_type};base64,{base64_img}"
            return (data_url, "Image")

        else:
            return None, "Unsupported"
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return None, "Error"

################################################################################################################

async def fetch_page_content_async(url):
    """
    Asynchronously fetch page content by offloading blocking I/O to a thread.
    Returns (content, type).
    """
    def blocking_fetch():
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')

            if 'application/pdf' in content_type:
                pdf_reader = PdfReader(BytesIO(response.content))
                pdf_text   = "".join(page.extract_text() for page in pdf_reader.pages)
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
            print(f"Error fetching {url}: {str(e)}")
            return None, "Error"

    # Offload the blocking code to a thread
    content, ctype = await asyncio.to_thread(blocking_fetch)
    return content, ctype

################################################################################################################
################################################################################################################

async def summarize_results_with_pages_async(search_results):
    """
    Asynchronously fetch content for each search result. 
    Returns a combined string of all results (page or snippet).
    """
    content_list = []
    web_results  = search_results.get('webPages', {}).get('value', [])[:SEARCH_RESULTS]

    # Create tasks for concurrent fetching
    tasks = [fetch_page_content_async(r['url']) for r in web_results]
    pages = await asyncio.gather(*tasks, return_exceptions=True)

    for (r, page_result) in zip(web_results, pages):
        title   = r['name']
        snippet = r['snippet']
        url     = r['url']

        if isinstance(page_result, Exception):
            # If any exception, fallback to snippet
            content_list.append(f"タイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\n")
            continue

        page_content, content_type = page_result
        if content_type in ("HTML", "PDF") and page_content:
            content_list.append(
                f"タイトル: {title}\nURL: {url}\n内容:\n{page_content}\n"
            )
        else:
            content_list.append(
                f"タイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\n"
            )

    return "\n".join(content_list)


async def summarize_results_async(search_results):
    """
    Calls GPT to summarize the combined content from search results.
    """
    snippets = await summarize_results_with_pages_async(search_results)

    p_src = (
        f"{CHARACTER}。あなたは検索結果を要約し、調査報告として回答を作成します。"
        f" 会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で、以下の検索結果を要約し回答を作ってください。"
        f" 仮に検索結果が英語でも回答は日本語でお願いします。"
        f" なお、回答がより高品質になるのならば、あなたの内部知識を加味して回答を作っても構いません。"
#        f" ただし、要約元にあった Title, URL は必ず元の形式で末尾に記入してください。"
        f" 回答のフォーマットは　書き出しは 今日のニュースだよ！で、続いて全記事のまとめのコメントをし一度{TWITTER_DELIMITER}で切ってください / Twitterに対応するため180文字ごとに区切る。Markdownにつかう文字や改行も文字数に含める。区切りは参考記事は1記事ごと{TWITTER_DELIMITER}で、区切り文字は文字数に含めない / MarkdownはTwitter対応のもの / 参考記事・リンクは要約に含めず全要約が終わった後にまとめ1リンクごと{TWITTER_DELIMITER}で区切る / Markdownは使わない でお願いします。: "
        f"{snippets}"
    )

    # We must offload the blocking OpenAI call to a thread as well:
    def blocking_chat_completion():
        messages = [{"role": "system", "content": CHARACTER}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": p_src})

        return client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages
        )

    response = await asyncio.to_thread(blocking_chat_completion)
    summary  = response.choices[0].message.content

    # Combine titles/URLs if needed
    titles = search_results.get('titles', [])
    urls   = search_results.get('urls', [])
    sources = "\n".join(
        f"Source: {t} - {u}"
        for t, u in zip(titles, urls)
    )

    return f"{summary}\n\n{sources}"
# ---------------------------------------------------------------------------

async def search_or_call_openai_async(discIn, img):
    """
    Decide if an external Bing search is needed; if yes, fetch pages concurrently,
    then summarize. Otherwise call GPT directly.
    """
    # If there's an image or an http link, skip external search logic
    if img or any("http" in entry["content"] for entry in discIn):
        print("Skipping search and calling OpenAI directly.")
        return just_call_openai(discIn)
    else:
        # Check if GPT says we need external search
        #yesorno = should_search(discIn)
        yesorno = "Yes"
        if "Yes" in yesorno:
            print("searching... ---------------------------------------------")
            parsed_result = parse_prompt(discIn)
            keywords      = extract_keywords(parsed_result)
            print(f"keyword: {keywords}")
            search_results = search_bing(keywords)

            # Summarize results with concurrency
            summary = await summarize_results_async(search_results)
            return summary
        else:
            print("generating... --------------------------------------------")
            return just_call_openai(discIn)


async def ai_respond(discIn, img):
    """
    High-level function to produce AI response (async).
    """
    try:
        result = await search_or_call_openai_async(discIn, img)
        return result
    except Exception as e:
        print(f"API Call Error: {str(e)}")
        return f"Error: {str(e)}"

def just_call_openai(discIn):
    #-- Call OpenAI --
    messages   = [{"role": "system", "content": f"{CHARACTER}"}]
    messages.extend(conversation_history)
    completion = client.chat.completions.create(
        model=GPT_MODEL,
        messages=messages
    )
    return completion.choices[0].message.content


def post_to_twitter(content):
    tweets = content.split(TWITTER_DELIMITER)
    trimmed_tweets = [tweet[:199] for tweet in tweets]

    first_tweet = twclient.create_tweet(text=trimmed_tweets[0])
    tweet_id = first_tweet.data['id']
    
    for tweet in trimmed_tweets[1:]:
        reply_tweet = twclient.create_tweet(text=tweet, in_reply_to_tweet_id=tweet_id)
        tweet_id = reply_tweet.data['id']

    print("Tweet thread posted successfully!")

async def run_bot():
    msg = f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。ジャンルは経済・テクノロジーでお願いします。検索する場合はニュースの期間指定もお願いします"
    img_url=None
    print("-User input------------------------------------------------------------------")
    print(f"  Message content: '{msg}'")
    discIn = []
    discIn.append({"role": "user", "content": msg})
    conversation_history.extend(discIn)

    response = await ai_respond(discIn, img_url)
    # Add AI response to conversation history
    conversation_history.append({"role": "assistant", "content": response})
    print("-Agent response--------------------------------------------------------------")
    print(f"  Response content:'{response}'")

    post_to_twitter(response)

def twtest():
  content = "あいうえお。確認用です"
  tweets = content.split(TWITTER_DELIMITER)
  trimmed_tweets = [tweet[:199] for tweet in tweets]

  first_tweet = twclient.create_tweet(text=trimmed_tweets[0])
  tweet_id = first_tweet.data['id']
  
  for tweet in trimmed_tweets[1:]:
      reply_tweet = twclient.create_tweet(text=tweet, in_reply_to_tweet_id=tweet_id)
      tweet_id = reply_tweet.data['id']
  print("Tweet posted successfully!")

if __name__ == "__main__":
  if not('test' in sys.argv):
    TWITTER_DO_TWEET = True
  
  asyncio.run(run_bot())
