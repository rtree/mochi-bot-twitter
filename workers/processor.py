import asyncio
from openai import OpenAI

class Processor:
    def __init__(self, context, config):
        self.context  = context
        self.config   = config
        self.aiclient = OpenAI(api_key=config.OPENAI_API_KEY)

    async def summarize_results_async(self, snippets):
        # p_src = (
        #     f"{self.config.CHARACTER}。あなたは検索結果を要約し、調査報告として回答を作成します。"
        #     f" 会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で、検索結果を要約し回答を作ってください。"
        #     f" 仮に検索結果が英語でも回答は日本語でお願いします。"
        #     f" なお、回答がより高品質になるのならば、あなたの内部知識を加味して回答を作っても構いません。"
        #     f" 回答のフォーマットはこちら:"
        #     f" - 書き出しは 今日のニュースだよ！ "
        #     f" - 書き出しに続き全記事のまとめのコメントをし一度{self.config.TWITTER_DELIMITER}で切る"
        #     f" - 投稿先はX(Twitter)なので、Markdownは使わないでください"
        #     f" - 区切りは1記事ごと{self.config.TWITTER_DELIMITER}の区切り文字のみ。
        #     180文字ごとに区切ること。区切り文字は文字数に含めない。また、要約の冒頭に箇条書きなどの ・ は含めないでください"
        #     f" - 参考記事のURLは要約に含めない"
        #     f" - 要約が終わった後に{self.config.TWITTER_DELIMITER}で切ったのち、締めのコメントをする。締めのコメントは内容からいきなり書き始めてください。つまり、 締めのコメント などの見出しはつけないでください"
        #     f" - 要約の文体も{self.config.AINAME}になるように気をつけてください"
        #     f" - 最後に参考記事のURLを投稿する"
        #     f" - 参考記事の各URLの前に必ず{self.config.TWITTER_DELIMITER}と書き、次の行にリンクを記載"
        #     f" 以下が要約対象の検索結果です:"
        #     f"  {snippets}"
        # )
        p_src = (
            f"""
            あなたはX(Twitter)投稿用のニュース要約を作成するアシスタントです。
            検索結果を要約し、Twitter投稿形式で出力してください。
            検索結果が英語でも回答は日本語でお願いします。

            【重要な禁止事項】
            - 「ふふん」「もちおだよ」などの挨拶や前置きは絶対に書かないでください
            - 「ほかにも読みたい記事があったら」などの後書きは絶対に書かないでください
            - 「--- Start of content ---」「--- End of content ---」形式は使わないでください
            - Markdown（**太字**、- 箇条書き など）は使わないでください
            - いきなり1つ目のニュース要約から始めてください

            【出力フォーマット】
            検索結果の中で最も重要なトピックを最大9個、以下の形式で出力:

            *記事要約（1〜3文で簡潔に。語尾は「だよ」「だって」など柔らかく）*

            *記事URL*
            {self.config.TWITTER_DELIMITER}

            【出力例1】
            Intelの新GPU「Battlemage」が発表されたよ。性能よりコストパフォーマンスを重視し、VRAM容量で競争力を高めてるみたい。特に$250で12GB VRAM搭載のArc B580は興味深いね

            https://gamersnexus.net/gpus/intel-arc-b580-battlemage-gpu-review-benchmarks
            {self.config.TWITTER_DELIMITER}

            【出力例2】
            パキスタンで「AIQT 2025」シンポジウムが開催され、AIと量子コンピューターの融合について議論が行われたよ。国際的な専門家が集まり、量子インターネットやAI駆動の量子回路などの開発動向が紹介されたんだって

            https://www.thenews.com.pk/print/1280851-aiqt-2025
            {self.config.TWITTER_DELIMITER}

            【各ツイートの制約】
            - 1つ目のトピックからいきなり始める（前置き禁止）
            - 最後のトピックで終わる（後書き禁止）
            - 各ツイートはURL込みで最長280文字（URLは常に23文字としてカウント）
            - 区切り文字 {self.config.TWITTER_DELIMITER} は文字数に含めない
            - 検索結果が少ない場合は、その数だけ出力（無理に9個にしない）
            - URLがない記事は絶対に出力しないでください。必ずURLを含む記事のみを選んでください

            【要約対象の検索結果】
            {snippets}
            """
         )


        def blocking_chat_completion():
            messages = [{"role": "system", "content": self.config.CHARACTER}]
            messages.extend(self.context)
            messages.append({"role": "user", "content": p_src})

            return self.aiclient.chat.completions.create(
                model=self.config.OPENAI_GPT_MODEL,
                messages=messages
            )

        response = await asyncio.to_thread(blocking_chat_completion)
        summary = response.choices[0].message.content

        return f"{summary}"

    async def summarize_each_result_async(self, contents):
        summaries = []
        for idx, content in enumerate(contents):
            self.config.logprint.info(f"Starting summarization for content {idx + 1}/{len(contents)}...")
            p_src = (
                f"""あなたは著名テクノロジー企業の創業者です。あなたは以下の内容を要約してください。
                要約は、会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で作ってください。
                仮に内容が英語でも回答は日本語でお願いします。
                なお、回答がより高品質になるのならば、あなたの内部知識を加味して回答を作っても構いません。
                回答のフォーマットは以下でお願いします:

                {self.config.FETCHER_START_OF_CONTENT}
                Title: *要約前のTitle*
                URL: *要約前のURL*
                SRC: *要約前のSRC*
                Snippet: *要約結果*
                {self.config.FETCHER_END_OF_CONTENT}

                以下が要約対象の内容です:
                 {content}
                """
            )

            def blocking_chat_completion():
                messages = [{"role": "system", "content": self.config.CHARACTER}]
                messages.extend(self.context)
                messages.append({"role": "user", "content": p_src})

                return self.aiclient.chat.completions.create(
                    model=self.config.OPENAI_GPT_MODEL,
                    messages=messages
                )

            try:
                response = await asyncio.to_thread(blocking_chat_completion)
                summary = response.choices[0].message.content
                summaries.append(summary)
                self.config.logprint.info(f"Summarization for content {idx + 1}/{len(contents)} completed.")
            except Exception as e:
                self.config.elogprint.error(f"Error summarizing content {idx + 1}/{len(contents)}: {str(e)}")
                summaries.append(f"{self.config.FETCHER_START_OF_CONTENT}\nTitle: Error\nSnippet: Unable to summarize due to error.\n{self.config.FETCHER_END_OF_CONTENT}\n")

        return "\n".join(summaries)

    def split_contents(self, raw_content):
        contents = raw_content.split(self.config.FETCHER_START_OF_CONTENT)
        cleaned_contents = []
        for content in contents:
            if content.strip():
                cleaned_content = content.split(self.config.FETCHER_END_OF_CONTENT)[0].strip()
                cleaned_contents.append(cleaned_content)
        return cleaned_contents

    # async def summarize_results_after_each_summary_async(self, raw_content):
    #     contents = self.split_contents(raw_content)
    #     final_summary = await self.summarize_each_result_async(contents)
    #     return final_summary
