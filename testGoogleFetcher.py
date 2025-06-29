from collections import deque
from config import Config
from workers.googleFetcher import GoogleFetcher
import asyncio

if __name__ == "__main__":
    config = Config()
    context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)
    fetcher = GoogleFetcher(context, config)
    # Fetch summary and URLs using GoogleFetcher
    summary, urls = asyncio.run(fetcher.fetch())
    # Print the summary and extracted URLs
    print(summary)
    print(urls)
    print("Done.")
