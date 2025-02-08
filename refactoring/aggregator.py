import asyncio
from fetcher import Fetcher
from config import Config

class Aggregator:
    """Aggregates and ranks fetched data."""

    @staticmethod
    async def summarize_results_with_pages_async(search_results):
        content_list = []
        web_results = search_results.get('webPages', {}).get('value', [])[:Config.SEARCH_RESULTS]
        tasks = [Fetcher.fetch_page_content_async(r['url']) for r in web_results]
        pages = await asyncio.gather(*tasks, return_exceptions=True)
        for (r, page_result) in zip(web_results, pages):
            title = r['name']
            snippet = r['snippet']
            url = r['url']
            if isinstance(page_result, Exception):
                content_list.append(f"タイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\n")
                continue
            page_content, content_type = page_result
            if content_type in ("HTML", "PDF") and page_content:
                content_list.append(f"タイトル: {title}\nURL: {url}\n内容:\n{page_content}\n")
            else:
                content_list.append(f"タイトル: {title}\nURL: {url}\nスニペット:\n{snippet}\n")
        return "\n".join(content_list)

    @staticmethod
    async def summarize_results_async(query):
        aggregated_results = await Fetcher.fetch(query)
        p_src = (
            f"{Config.CHARACTER}。あなたは検索結果を要約し、調査報告として回答を作成します。"
            f" 会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で、検索結果を要約し回答を作ってください。"
            f" 仮に検索結果が英語でも回答は日本語でお願いします。"
            f" なお、回答がより高品質になるのならば、あなたの内部知識を加味して回答を作っても構いません。"
            f" 回答のフォーマットはこちら:"
            f" - 書き出しは 今日のニュースだよ！ "
            f" - 書き出しに続き全記事のまとめのコメントをし一度{Config.TWITTER_DELIMITER}で切る"
            f" - 投稿先はX(Twitter)なので、Markdownは使わないでください"
            f" - 区切りは1記事ごと{Config.TWITTER_DELIMITER}の区切り文字のみ。180文字ごとに区切ること。区切り文字は文字数に含めない。また、要約の冒頭に箇条書きなどの ・ は含めないでください"
            f" - 参考記事のURLは要約に含めない"
            f" - 要約が終わった後に{Config.TWITTER_DELIMITER}で切ったのち、締めのコメントをする。締めのコメントは内容からいきなり書き始めてください。つまり、 締めのコメント などの見出しはつけないでください"
            f" - 要約の文体も{Config.AINAME}になるように気をつけてください"
            f" - 最後に参考記事のURLを投稿する"
            f" - 参考記事の各URKの前に必ず{Config.TWITTER_DELIMITER}と書き、次の行にリンクを記載"
            f" 以下が要約対象の検索結果です:"
            f"  {aggregated_results}"
        )

        def blocking_chat_completion():
            messages = [{"role": "system", "content": Config.CHARACTER}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": p_src})

            return client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=messages
            )

        response = await asyncio.to_thread(blocking_chat_completion)
        summary = response.choices[0].message.content

        return summary

    async def merge_and_summarize(self, fetcher, processor):
        combined_text = await fetcher.fetch()
        return await processor.summarize_content(combined_text)
