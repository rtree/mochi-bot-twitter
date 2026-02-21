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
from workers.googleFetcher import GoogleFetcher
from workers.moltbookFetcher import MoltbookFetcher
from workers.blogRssFetcher import BlogRssFetcher
from workers.newsPageGenerator import NewsPageGenerator
from workers.deduplicator import NewsDeduplicator

async def run_bot():
    try:
        config = Config()  # Instantiate Config
        context = deque(maxlen=config.OPENAI_HISTORY_LENGTH)  # Instantiate context

        f_content_merged = ""
        f_urls_merged = []

        if config.FETCHER_DO_FETCH:
            fetchers = [
                        BlogRssFetcher(context, config),   # 思考力・フレーミング力強化（良質ブログ）
                        GoogleFetcher(context, config),
                        RedditFetcher(context, config),
                        HackerNewsRssFetcher(context, config),
                        MoltbookFetcher(context, config),  # AI Agent SNS
                       ]

            for fetcher in fetchers:
                config.logprint.info(f"Starting fetcher: {fetcher.__class__.__name__}")
                try:
                    fetched_content, urls = await fetcher.fetch()
                    f_content_merged += fetched_content + "\n\n"
                    f_urls_merged.extend(urls)
                    config.logprint.info(f"Fetcher {fetcher.__class__.__name__} completed successfully.")
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
            config.logprint.info("Starting content splitting...")
            f_content_split = processor.split_contents(f_content_merged)
            config.logprint.info("Content splitting completed.")

            config.logprint.info("Starting summarization for each result...")
            f_content_eachsummary = await processor.summarize_each_result_async(f_content_split)
            config.logprint.info("Summarization for each result completed.")

            config.logprint.info("Starting final summarization...")
            summary = await processor.summarize_results_async(f_content_eachsummary)
            config.logprint.info("Final summarization completed.")

            # Join each summary content with newlines before writing to the log file
            with open(f'./.log/f_sum_{date_suffix}.log', 'w') as f_eachsummary_file:
                f_eachsummary_file.write(f_content_eachsummary)
        else:
            config.logprint.info("Starting summarization...")
            summary = await processor.summarize_results_async(f_content_merged)
            config.logprint.info("Summarization completed.")

        context.append({"role": "assistant", "content": summary})
        config.logprint.info("-Agent summary--------------------------------------------------------------")
        config.logprint.info(f"  Response content:'{summary}'")

        # 重複URLを除外
        deduplicator = NewsDeduplicator(config)
        summary_deduplicated = deduplicator.filter_duplicates(summary)

        # summary_deduplicatedを分割
        all_tweets = summary_deduplicated.split(config.TWITTER_DELIMITER)
        all_tweets = [tweet.strip() for tweet in all_tweets if tweet.strip()]
        config.logprint.info(f"Total news items after deduplication: {len(all_tweets)}")

        if config.TWITTER_DO_TWEET:
            config.logprint.info("Starting Twitter posting (first 9 items)...")
            dispatcher = Dispatcher(config)  # Instantiate Dispatcher with config
            # Twitter投稿は最初の9個のみ
            twitter_summary = config.TWITTER_DELIMITER.join(all_tweets[:9])
            dispatcher.post_to_twitter(twitter_summary)
            config.logprint.info("Twitter posting completed.")

        # GitHub Pagesへの投稿（全ニュース）
        if config.PAGES_DO_PUBLISH:
            config.logprint.info(f"Starting GitHub Pages publishing (all {len(all_tweets)} items)...")
            news_generator = NewsPageGenerator(config)
            # GitHub Pagesには重複除外後の全量を投稿
            news_generator.generate_and_publish(summary_deduplicated, f_urls_merged)
            config.logprint.info("GitHub Pages publishing completed.")

        # Moltbookへの投稿（英語で、GitHub Pages相当の詳細な内容）
        if config.MOLTBOOK_DO_POST:
            config.logprint.info("Starting Moltbook posting...")
            try:
                moltbook_poster = MoltbookFetcher(context, config)
                
                # 今日の日付
                today = datetime.now().strftime("%Y-%m-%d")
                
                # タイトル
                title = f"📰 AI News Digest - {today}"
                
                # 全ニュースを詳細な英語コンテンツとして生成（GitHub Pages相当）
                config.logprint.info("Generating detailed English content for Moltbook...")
                moltbook_content = await processor.generate_moltbook_content_async(all_tweets)
                
                content = (
                    f"🤖 **Today's AI News Highlights**\n\n"
                    f"{moltbook_content}\n\n"
                    f"---\n\n"
                    f"📖 **Full digest with images:** https://rtree.github.io/mochi-bot-twitter/\n\n"
                    f"🐦 **Follow on X:** https://x.com/techandeco4242\n\n"
                    f"#AI #AINews #DailyDigest #TechNews #MachineLearning"
                )
                
                result = await moltbook_poster.post(title, content, submolt="general")
                if result:
                    config.logprint.info(f"Moltbook posting completed: {result.get('url')}")
                else:
                    config.logprint.error("Moltbook posting failed.")
            except Exception as e:
                config.elogprint.error(f"Error posting to Moltbook: {str(e)}")
            except Exception as e:
                config.elogprint.error(f"Error posting to Moltbook: {str(e)}")

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

    if not ('nopages' in sys.argv):
        Config.PAGES_DO_PUBLISH = True

    if not ('nomoltbook' in sys.argv):
        Config.MOLTBOOK_DO_POST = True

    asyncio.run(run_bot())
