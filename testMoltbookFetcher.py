from collections import deque
from config import Config
from workers.moltbookFetcher import MoltbookFetcher
import asyncio

if __name__ == "__main__":
    config = Config()  # Instantiate Config
    context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
    fetcher = MoltbookFetcher(context, config)
    
    print("=== Fetching Top Posts from Moltbook ===")
    summaries, urls = asyncio.run(fetcher.fetch())
    print(summaries)  # Print summarized Moltbook posts
    print("\n=== URLs ===")
    print(urls)       # Print extracted post URLs
    print("\nDone.")  # Print completion message
