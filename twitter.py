import os
import tweepy
from dotenv import load_dotenv
from openai import OpenAI
import tweepy
import pandas as pd
from datetime import datetime
import requests

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

# Define headers for authentication
HEADERS = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}

# Define log file
log_file = f"twitter-trends-{datetime.now().strftime('%Y-%m-%d')}.log"

# Trending topics (Manually set tech & economy-related topics)
trending_topics = ["Artificial Intelligence", "Crypto", "Stock Market", "Tech News", "Bitcoin", "Startup", "Elon Musk", "Finance"]

# Function to fetch tweets for a topic
def fetch_tweets(topic):
    url = "https://api.twitter.com/2/tweets/search/recent"
    
    # Search query: Exclude retweets, limit results
    params = {
        "query": f"{topic} -is:retweet lang:en",
        "max_results": 100,
        "tweet.fields": "created_at,public_metrics,text,author_id",
        "expansions": "author_id",
        "user.fields": "username"
    }
    
    response = requests.get(url, headers=HEADERS, params=params)
    
    if response.status_code != 200:
        print(f"Error fetching tweets for {topic}: {response.json()}")
        return []
    
    data = response.json()
    tweets = data.get("data", [])
    users = {user["id"]: user["username"] for user in data.get("includes", {}).get("users", [])}
    
    tweet_data = []
    for tweet in tweets:
        metrics = tweet["public_metrics"]
        tweet_data.append({
            "username": users.get(tweet["author_id"], "Unknown"),
            "content": tweet["text"],
            "likes": metrics["like_count"],
            "retweets": metrics["retweet_count"],
            "quotes": metrics.get("quote_count", 0),
            "created_at": tweet["created_at"]
        })
    
    return tweet_data

# Fetch tweets for each trending topic and save to log file
all_tweets = []
for topic in trending_topics:
    print(f"Fetching tweets for: {topic}")
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