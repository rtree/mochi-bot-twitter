import asyncio
from fetcher import Fetcher
from processor import Processor
from aggregator import Aggregator
from dispatcher import Dispatcher

TWITTER_DO_TWEET = False  # Set to True to enable tweeting

async def main():
    fetcher    = Fetcher()
    processor  = Processor()
    aggregator = Aggregator()
    dispatcher = Dispatcher()

    query = "Today's news in technology and economics"
    summary = await aggregator.merge_and_summarize(fetcher, processor, query)

    if TWITTER_DO_TWEET:
        dispatcher.post_to_twitter(summary)
    else:
        print(summary)

if __name__ == "__main__":
    asyncio.run(main())
