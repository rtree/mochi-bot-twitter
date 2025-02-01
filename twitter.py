import os
import tweepy
from dotenv import load_dotenv
from openai import OpenAI
import tweepy
import pandas as pd
from datetime import datetime

# Twitter API Credentials (Replace with your own)

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



# Authenticate with Twitter API
auth = tweepy.OAuth1UserHandler(TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True)

# Get trending topics (Worldwide WOEID = 1)
worldwide_woeid = 1
try:
    trends = api.get_place_trends(worldwide_woeid)
    trending_topics = [trend['name'] for trend in trends[0]['trends']]
except tweepy.TweepError as e:
    print(f"Error fetching trends: {e}")
    trending_topics = []

# Log file setup
log_file = f"twitter-trends-{datetime.now().strftime('%Y-%m-%d')}.log"

# Function to fetch tweets for a given topic
def fetch_tweets(topic):
    query = f"{topic} -is:retweet"
    try:
        tweets = api.search_tweets(q=query, count=100, tweet_mode='extended')
        tweet_data = []
        
        for tweet in tweets:
            tweet_info = {
                'username': tweet.user.screen_name,
                'content': tweet.full_text,
                'likes': tweet.favorite_count,
                'retweets': tweet.retweet_count,
                'quotes': tweet.quote_count if hasattr(tweet, 'quote_count') else 0,
                'created_at': tweet.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            tweet_data.append(tweet_info)

        return tweet_data

    except e:
        print(f"Error fetching tweets for {topic}: {e}")
        return []

# Fetch tweets for each trending topic and save to log file
all_tweets = []
for topic in trending_topics:
    tweets = fetch_tweets(topic)
    all_tweets.extend(tweets)

# Save data to log file
if all_tweets:
    df = pd.DataFrame(all_tweets)
    with open(log_file, 'a') as f:
        df.to_csv(f, header=f.tell() == 0, index=False)

    print(f"Data saved to {log_file}")
else:
    print("No tweets found for the trending topics.")


