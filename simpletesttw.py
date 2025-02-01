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


load_dotenv()

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



BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
twclient = tweepy.Client(bearer_token=BEARER_TOKEN)


def search_tweets(query, count=500, sort_order="relevancy"):
    """
    Search for tweets based on the query.
    - sort_order="relevancy" → Finds the most relevant/popular tweets
    - sort_order="recency" → Finds the most recent tweets
    """
    try:
        tweets = twclient.search_recent_tweets(
            query=query,
            max_results=count,
            tweet_fields=["created_at", "text", "author_id", "public_metrics"],
            sort_order=sort_order  # NEW: Use 'relevancy' for popular tweets
        )
        
        logging.info("Twitter Search Results:")
        tweet_data = []
        if tweets.data:
            for tweet in tweets.data:
                metrics = tweet.public_metrics  # Get engagement metrics (likes, retweets)
                logging.info(f"Tweet: {tweet.text} | Likes: {metrics['like_count']} | Retweets: {metrics['retweet_count']}")
                tweet_data.append(f"{tweet.text} (Likes: {metrics['like_count']}, Retweets: {metrics['retweet_count']})")
        return tweet_data
    except tweepy.errors.TooManyRequests as e:
        reset_time       = e.response.headers.get('x-rate-limit-reset')
        reset_time_human = datetime.utcfromtimestamp(int(reset_time)).strftime('%Y-%m-%d %H:%M:%S')
        error_logger.error(f"search_tweets: Rate limit exceeded.: ")
        error_logger.error(f" Try again at           : {reset_time_human}")
        error_logger.error(f" x-rate-limit-limit     : {e.response.headers.get('x-rate-limit-limit')}")
        error_logger.error(f" x-rate-limit-remaining : {e.response.headers.get('x-rate-limit-remaining')}")
    except Exception as e:
        print(f"Error: {e}")


search_tweets("OpenAI", 100, "relevancy")

