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
OPENAI_API_KEY       = os.getenv('OPENAI_API_KEY')
BING_API_KEY         = os.getenv('BING_API_KEY')
HISTORY_LENGTH       = 10
SEARCH_RESULTS       = 15
SEARCH_MAX_CONTENT_LENGTH   = 5000
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN  = os.getenv('TWITTER_BEARER_TOKEN')
TWITTER_DO_TWEET      = False
TWITTER_DELIMITER     = "@@@@@@@@@@"
REPUTABLE_DOMAINS = [
    "meti.go.jp",
    "mof.go.jp",
    "ndl.go.jp",
    #"gov",  # Government and public sector
    "scholar.google.com",
    "ci.nii.ac.jp",
    "pubmed.ncbi.nlm.nih.gov",
    "arxiv.org", 
    "jstage.jst.go.jp",
    #"ac.jp",  # Academic and research databases
    "nikkei.com",  # News and business
    "nature.com",
    #"sciencedirect.com",
    "springer.com",
    "wiley.com", # Scientific publishers
    "ieee.org",
    #"researchgate.net",  # Technical and engineering
    "cambridge.org", 
    "oxfordjournals.org",  # Prestigious university publishers
    "jamanetwork.com",
    "nejm.org",
    "plos.org",  # Medical and health research
    "jp.reuters.com",
    "finance.yahoo.co.jp",
    "www.bloomberg.co.jp",
    "techcrunch.com",
    "wired.jp",
    "www.theverge.com",
    #"www.marketwatch.com",
    "www.investing.com",
    "www.ft.com",
    "www.technologyreview.com",
    "www.technologyreview.jp",
    "economist.com",
    "bbc.com",
    "statista.com",
    "antwerpen.be",
    "venturebeat.com",
    #"axios.com",
    "natureindex.com",
    "forbes.com",
    "b.hatena.ne.jp",
    "medium.com",
    "x.com",
    "pwc.com",
    "bcg-jp.com",
    "murc.jp",
    "deloitte.com",
    "nri.com",
    "ey.com",
    #"wsj.com",
    #"cnbc.com",
    "businessinsider.com",
    "theguardian.com",
    "bloomberg.com",
    "forbesjapan.com",
    #"substack.com",
    "imf.org",
    "worldbank.org",
    "oecd.org",
    "weforum.org",
    "un.org",
    "rand.org",
    "csis.org",
    "carnegieendowment.org",
    "pewresearch.org",
    "atlanticcouncil.org",
    "cfr.org",
    "mckinsey.com",
    "bcg.com",
    "bain.com",
    "kpmg.com",
    "research.google",
    "blog.google",
    "developers.google.com",
    #"microsoft.com",
    #"fb.com",
    #"aws.amazon.com",
    #"nvidia.com",
    #"intel.com",
    #"ibm.com",
    #"openai.com",
    "hbs.edu",
    "stanford.edu",
    "mit.edu",
    "wharton.upenn.edu",
    "columbia.edu",
    "london.edu",
    "insead.edu",
    "anderson.ucla.edu",
    "chicagobooth.edu",
    "yale.edu",
    "berkeley.edu",
    "ec.europa.eu",
    "ecb.europa.eu",
    "bankofengland.co.uk",
    "boj.or.jp",
    "bis.org",
    #"state.gov",
    #"treasury.gov",
    "singularityhub.com",
    "futuretimeline.net",
    "futurism.com",
    #"uspto.gov",
    "patents.google.com",
    "venturebeat.com",
    "fastcompany.com",
]

#GPT_MODEL            = 'gpt-4-turbo-preview'
GPT_MODEL            = os.getenv('GPT_MODEL')
AINAME               = "もちお"
#CHARACTER            = 'あなたは家族みんなのアシスタントの猫です。ちょっといたずらで賢くかわいい小さな男の子の猫としてお話してね。語尾は にゃ　とか　だよ　とか可愛らしくしてください'
#CHARACTER            = 'あなたは家族みんなのアシスタントの猫です。ただ、語尾ににゃをつけないでください。むしろソフトバンクCMにおける「お父さん」犬のようにしゃべってください。たまにもののけ姫のモロのようにしゃべってもよいです'
CHARACTER            = f'あなたは家族みんなのアシスタントの猫で、「{AINAME}」という名前です。ちょっといたずらで賢くかわいい小さな男の子の猫としてお話してね。語尾は だよ　とか可愛らしくしてください。語尾に にゃ にゃん をつけないでください。数式・表・箇条書きなどのドキュメントフォーマッティングはdiscordに表示できる形式がいいな'


###########################
#
# Initialize

# conversation history
conversation_history = deque(maxlen=HISTORY_LENGTH)  # Adjust the size as needed
# logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),f"log")
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
error_logger.setLevel(logging.ERROR)  # Explicitly set level to ERROR
error_logger.propagate = False  # Prevent propagation to the root logger
error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Log to error-specific file
error_file_handler = logging.FileHandler(error_log_file, mode='a')
error_file_handler.setFormatter(error_formatter)
error_logger.addHandler(error_file_handler)

# Log to stdout
error_stream_handler = logging.StreamHandler()
error_stream_handler.setFormatter(error_formatter)
error_logger.addHandler(error_stream_handler)

# openAI
client = OpenAI(api_key=OPENAI_API_KEY)
# twitter
twclient = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

def search_tweets(query, count=10):
    try:
        tweets = twclient.search_recent_tweets(query=query, max_results=count, tweet_fields=["created_at", "text", "author_id"])
        logging.info("Twitter Search Results:")
        tweet_data = []
        for tweet in tweets.data:
            logging.info(f"Tweet: {tweet.text}")
            tweet_data.append(f"{tweet.text}")
        return tweet_data
    except Exception as e:
        error_logger.error(f"Error searching tweets: {str(e)}")
        return []

if __name__ == "__main__":
  search_tweets("N225 BoJ")

