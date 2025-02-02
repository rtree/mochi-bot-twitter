import os
import tweepy
import time
from dotenv import load_dotenv

load_dotenv()
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

class Dispatcher:
    """Handles posting summaries to Twitter."""

    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )

    def post_to_twitter(self, content):
        """Posts content to Twitter, handling thread creation."""
        tweets = [content[i:i+280] for i in range(0, len(content), 280)]
        first_tweet = self.client.create_tweet(text=tweets[0])
        
        for tweet in tweets[1:]:
            time.sleep(2)
            self.client.create_tweet(text=tweet, in_reply_to_tweet_id=first_tweet.data["id"])
