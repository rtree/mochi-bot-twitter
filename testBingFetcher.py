#testBingFetcher.py
from collections import deque
from config import Config
from workers.bingFetcher import BingFetcher
import asyncio

if __name__ == "__main__":
    config = Config()  # Instantiate Config
    context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
    fetcher = BingFetcher(context, config)
    summaries, urls = asyncio.run(fetcher.fetch())
    # Print summarized Bing search results
    print(summaries)  
    # Print extracted URLs from Bing search results
    print(urls)       
    print("Done.")    # Print completion message