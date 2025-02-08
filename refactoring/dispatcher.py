import os
import tweepy
import time
from dotenv import load_dotenv
from config import Config

load_dotenv()
TWITTER_API_KEY       = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET    = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN  = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN  = os.getenv('TWITTER_BEARER_TOKEN')

class Dispatcher:
    """Handles posting summaries to Twitter."""

    @staticmethod
    def post_to_twitter(content):
        tweets = content.split(Config.TWITTER_DELIMITER)
        trimmed_tweets = [tweet[:199] for tweet in tweets]

        try:
            first_tweet = twclient.create_tweet(text=trimmed_tweets[0])
            Config.logprint.info("First tweet posted successfully.")

            for tweet in trimmed_tweets[1:]:
                time.sleep(2)
                twclient.create_tweet(text=tweet)
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
