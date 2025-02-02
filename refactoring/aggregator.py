import asyncio

class Aggregator:
    """Aggregates and ranks fetched data."""

    async def merge_and_summarize(self, fetcher, processor, query):
        """Fetches, processes, and summarizes results."""
        search_results = await fetcher.fetch_bing(query)
        content_list = []

        tasks = [fetcher.fetch_page_content(url) for url in search_results['urls']]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

        for (url, page_result) in zip(search_results['urls'], pages):
            if isinstance(page_result, Exception):
                continue
            page_content, content_type = page_result
            if content_type in ("HTML", "PDF") and page_content:
                content_list.append(page_content)

        combined_text = "\n".join(content_list)
        return await processor.summarize_content(combined_text)
