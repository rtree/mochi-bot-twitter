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

from config import Config
from workers.dispatcher import Dispatcher
from workers.processor  import Processor
from workers.redditFetcher import RedditFetcher
from workers.bingFetcher import BingFetcher

# # Initialize OpenAI and Twitter clients
# client = OpenAI(api_key=Config.OPENAI_API_KEY)
# twclient = tweepy.Client(
#     bearer_token=Config.TWITTER_BEARER_TOKEN,
#     consumer_key=Config.TWITTER_API_KEY,
#     consumer_secret=Config.TWITTER_API_SECRET,
#     access_token=Config.TWITTER_ACCESS_TOKEN,
#     access_token_secret=Config.TWITTER_ACCESS_SECRET
# )

async def run_bot():
    try:
        config = Config()  # Instantiate Config
        context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
        fetchers = [BingFetcher(context, config),
                    #RedditFetcher(context, config),
                  ]

        combined_search_results = ""
        for fetcher in fetchers:
            try:
                search_results = await fetcher.fetch()
                combined_search_results += search_results + "\n\n"
            except Exception as e:
                config.elogprint.error(f"Error in fetcher {fetcher.__class__.__name__}: {str(e)}")

        processor = Processor(context, config)  # Instantiate Processor with context and config
        summary = await processor.summarize_results_async(combined_search_results)

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
