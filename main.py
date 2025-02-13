import os
from collections import deque
import asyncio
import sys
from datetime import datetime

from config import Config
from workers.dispatcher import Dispatcher
from workers.processor  import Processor
from workers.redditFetcher import RedditFetcher
from workers.bingFetcher import BingFetcher
from workers.hackerNewsRssFetcher import HackerNewsRssFetcher

async def run_bot():
    try:
        config = Config()  # Instantiate Config
        context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context

        f_content_merged = ""
        f_urls_merged = []

        if config.FETCHER_DO_FETCH:
            fetchers = [BingFetcher(context, config),
                        RedditFetcher(context, config),
                        HackerNewsRssFetcher(context, config),
                       ]

            for fetcher in fetchers:
                try:
                    fetched_content, urls = await fetcher.fetch()
                    f_content_merged += fetched_content + "\n\n"
                    f_urls_merged.extend(urls)
                except Exception as e:
                    config.elogprint.error(f"Error in fetcher {fetcher.__class__.__name__}: {str(e)}")

            # Save fetched content and URLs to log files
            os.makedirs('./.log', exist_ok=True)
            date_suffix = datetime.now().strftime("%Y-%m%d")
            with open(f'./.log/f_nosum_{date_suffix}.log', 'w') as f_content_file:
                f_content_file.write(f_content_merged)
            with open(f'./.log/f_urls_{date_suffix}.log', 'w') as f_urls_file:
                f_urls_file.write('\n'.join(f_urls_merged))
        else:
            # Read content and URLs from log files
            date_suffix = datetime.now().strftime("%Y-%m%d")
            with open(f'./.log/f_nosum_{date_suffix}.log', 'r') as f_content_file:
                f_content_merged = f_content_file.read()
            with open(f'./.log/f_urls_{date_suffix}.log', 'r') as f_urls_file:
                f_urls_merged = f_urls_file.read().splitlines()

        processor = Processor(context, config)  # Instantiate Processor with context and config
        if config.PROCESSOR_DO_EACH_SUMMARY:
            f_content_split = processor.split_contents(f_content_merged)
            f_content_eachsummary = await processor.summarize_each_result_async(f_content_split)
            summary = await processor.summarize_results_async(f_content_eachsummary)

            # Join each summary content with newlines before writing to the log file
            with open(f'./.log/f_sum_{date_suffix}.log', 'w') as f_eachsummary_file:
                f_eachsummary_file.write(f_content_eachsummary)
        else:
            summary = await processor.summarize_results_async(f_content_merged)

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
    if not ('notweet' in sys.argv):
        Config.TWITTER_DO_TWEET = True

    if not ('nofetch' in sys.argv):
        Config.FETCHER_DO_FETCH = True

    if not ('nosummary' in sys.argv):
        Config.PROCESSOR_DO_EACH_SUMMARY = True

    asyncio.run(run_bot())
