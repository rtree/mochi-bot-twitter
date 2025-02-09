from collections import deque
import asyncio
import sys

from config import Config
from workers.dispatcher import Dispatcher
from workers.processor  import Processor
from workers.redditFetcher import RedditFetcher
from workers.bingFetcher import BingFetcher

async def run_bot():
    try:
        config = Config()  # Instantiate Config
        context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context
        fetchers = [BingFetcher(context, config),
                    #RedditFetcher(context, config),
                  ]

        combined_search_results = ""
        all_urls = []
        for fetcher in fetchers:
            try:
                fetched_content, urls = await fetcher.fetch()
                combined_search_results += fetched_content + "\n\n"
                all_urls.extend(urls)
            except Exception as e:
                config.elogprint.error(f"Error in fetcher {fetcher.__class__.__name__}: {str(e)}")

        processor = Processor(context, config)  # Instantiate Processor with context and config
        summary   = await processor.summarize_results_async(combined_search_results)

        context.append({"role": "assistant", "content": summary})
        config.logprint.info("-Agent summary--------------------------------------------------------------")
        config.logprint.info(f"  Response content:'{summary}'")

        if config.TWITTER_DO_TWEET:
            dispatcher = Dispatcher(config)  # Instantiate Dispatcher with config
            dispatcher.post_to_twitter(summary)

    except Exception as e:
        config.elogprint.error(f"API Call Error: {str(e)}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
    if not ('test' in sys.argv):
        Config.TWITTER_DO_TWEET = True

    asyncio.run(run_bot())
