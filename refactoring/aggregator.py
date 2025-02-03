import asyncio

class Aggregator:
    """Aggregates and ranks fetched data."""

    async def merge_and_summarize(self, fetcher, processor):
        combined_text = await fetcher.fetch()
        return await processor.summarize_content(combined_text)
