import tweepy
import time
from datetime import datetime

class Dispatcher:
    def __init__(self, config):
        self.config = config
        self.twclient = tweepy.Client(
            bearer_token=config.TWITTER_BEARER_TOKEN,
            consumer_key=config.TWITTER_API_KEY,
            consumer_secret=config.TWITTER_API_SECRET,
            access_token=config.TWITTER_ACCESS_TOKEN,
            access_token_secret=config.TWITTER_ACCESS_SECRET
        )

    def post_to_twitter(self, content):
        tweets = content.split(self.config.TWITTER_DELIMITER)
        #tweets = [tweet[:199] for tweet in tweets]

        try:
            first_tweet = self.twclient.create_tweet(text=tweets[0])
            self.config.logprint.info("First tweet posted successfully.")

            for tweet in tweets[1:]:
                time.sleep(2)
                self.twclient.create_tweet(text=tweet)
                self.config.logprint.info("Other tweet posted successfully.")
            self.config.logprint.info("Tweet thread posted successfully!")

        except tweepy.errors.TooManyRequests as e:
            reset_time = e.response.headers.get('x-rate-limit-reset')
            reset_time_human = datetime.utcfromtimestamp(int(reset_time)).strftime('%Y-%m-%d %H:%M:%S')
            self.config.elogprint.error(f"post_to_twitter: Rate limit exceeded.: ")
            self.config.elogprint.error(f" Try again at           : {reset_time_human}")
            self.config.elogprint.error(f" x-rate-limit-limit     : {e.response.headers.get('x-rate-limit-limit')}")
            self.config.elogprint.error(f" x-rate-limit-remaining : {e.response.headers.get('x-rate-limit-remaining')}")
            return
