from workers.hackerNewsRssFetcher import HackerNewsRssFetcher
import asyncio
from collections import deque
from config import Config

if __name__ == '__main__':
    config = Config()  # Instantiate Config
    context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
    fetcher = HackerNewsRssFetcher(context, config)
    summaries, urls = asyncio.run(fetcher.fetch())
    #print(summaries)  # Print summarized Hacker News posts
    print(urls)       # Print extracted post URLs
    print("Done.")    # Print completion message

