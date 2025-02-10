from collections import deque
from config import Config
from workers.redditFetcher import RedditFetcher
import asyncio

if __name__ == "__main__":
    config = Config()  # Instantiate Config
    context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
    fetcher = RedditFetcher(context, config)
    summaries, urls = asyncio.run(fetcher.fetch())
    #print(summaries)  # Print summarized Reddit posts
    print(urls)       # Print extracted post URLs
    print("Done.")    # Print completion message