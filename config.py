import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

class Config:
    OPENAI_API_KEY        = os.getenv('OPENAI_API_KEY')
    OPENAI_GPT_MODEL      = os.getenv('OPENAI_GPT_MODEL')
    OPENAI_HISTORY_LENGTH = 10

    BING_API_KEY          = os.getenv('BING_API_KEY')
    BING_SEARCH_RESULTS   = 10
    BING_SEARCH_MAX_CONTENT_LENGTH = 5000

    TWITTER_API_KEY       = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET    = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN  = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
    TWITTER_BEARER_TOKEN  = os.getenv('TWITTER_BEARER_TOKEN')
    TWITTER_DO_TWEET      = False
    TWITTER_DELIMITER     = "@@@@@@@@@@"

    REDDIT_CLIENT_ID      = os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET  = os.getenv('REDDIT_CLIENT_SECRET')
    REDDIT_USERNAME       = os.getenv('REDDIT_USERNAME')
    REDDIT_PASSWORD       = os.getenv('REDDIT_PASSWORD')
    REDDIT_SEARCH_RESULTS = 10

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
    logprint = logging.getLogger()

    error_log_file = os.path.join(log_dir, f"error_{datetime.today().strftime('%Y-%m-%d')}.log")
    elogprint = logging.getLogger("error_logger")
    elogprint.setLevel(logging.ERROR)
    elogprint.propagate = False
    error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    error_file_handler = logging.FileHandler(error_log_file, mode='a')
    error_file_handler.setFormatter(error_formatter)
    elogprint.addHandler(error_file_handler)

    error_stream_handler = logging.StreamHandler()
    error_stream_handler.setFormatter(error_formatter)
    elogprint.addHandler(error_stream_handler)