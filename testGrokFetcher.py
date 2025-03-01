from collections import deque
from config import Config
from workers.grokFetcher import GrokFetcher
import asyncio

if __name__ == "__main__":
    config = Config()  # Instantiate Config
    context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
    fetcher = GrokFetcher(context, config)

    # summaries, urls = asyncio.run(fetcher.fetch())
    # print(summaries)  # Print summarized content from Grok
    # print(urls)       # Print extracted URLs
    # print("Done.")    # Print completion message

    news = asyncio.run(fetcher.fetch_news())
    print(news)  # Print summarized news content from Grok
    print("Done.")  # Print completion message