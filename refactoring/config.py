from dotenv import load_dotenv
import logging
import os

# Load environment variables
load_dotenv()
OPENAI_API_KEY              = os.getenv('OPENAI_API_KEY')
BING_API_KEY                = os.getenv('BING_API_KEY')
HISTORY_LENGTH              = 10
SEARCH_RESULTS              = 15
SEARCH_MAX_CONTENT_LENGTH   = 5000
TWITTER_API_KEY       = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET    = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN  = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN  = os.getenv('TWITTER_BEARER_TOKEN')
TWITTER_DO_TWEET      = False
TWITTER_DELIMITER     = "@@@@@@@@@@"
GPT_MODEL            = os.getenv('GPT_MODEL')
AINAME               = "もちお"
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


