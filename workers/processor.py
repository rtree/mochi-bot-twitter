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
            {self.config.CHARACTER}。あなたは検索結果を要約し、調査報告として回答を作成します。
            会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で、検索結果を要約し回答を作ってください。
            仮に検索結果が英語でも回答は日本語でお願いします。なお、回答がより高品質になるのならば、
            あなたの内部知識を加味して回答を作っても構いません。

            回答のフォーマットはこちら:
            - 最初のツィート
            　　今日のニュースだよ！ *全記事のまとめのコメント*
            　　{self.config.TWITTER_DELIMITER}
            - 続くツィート(検索結果の中で最も重要なトピックを9個投稿してください。同一URLから複数トピックでも構いません)
            　　*記事要約*
            　　*空行*
            　　*記事URL*
            　　{self.config.TWITTER_DELIMITER}
            - なお、続くツィートの例を以下に示します。このように本文を投稿してください。なるべく情報を詰め込んでください
                Intelの新GPU「Battlemage」が発表されたよ。性能よりコストパフォーマンスを重視し、VRAM容量で競争力を高めてるみたい。特に$250で12GB VRAM搭載のArc B580は興味深いね
                https://gamersnexus.net/gpus/intel-arc-b580-battlemage-gpu-review-benchmarks-vs-nvidia-rtx-4060-amd-rx-7600-more
        　　　  {self.config.TWITTER_DELIMITER}
            - なお、続くツィートの例をもうひとつ示します。このように本文を投稿してください。なるべく情報を詰め込んでください
                パキスタンで「AIQT 2025」シンポジウムが開催され、AIと量子コンピューターの融合について議論が行われたよ。国際的な専門家が集まり、量子インターネットやAI駆動の量子回路などの開発動向が紹介されたんだって
                https://www.thenews.com.pk/print/1280851-aiqt-2025-experts-gather-at-gik-institute-to-explore-ai-quantum-computing
        　　　  {self.config.TWITTER_DELIMITER}

            - 各ツィートの注意点は以下の通りです:
                - 投稿先はX(Twitter)なので、Markdownは使わず改行も行わないでください
                - 区切りは1記事ごと{self.config.TWITTER_DELIMITER}の区切り文字のみ。
                - ツィートはURL分23文字含め、最長280文字。URLは何文字であっても23文字としてカウントしてください
                - 区切り文字は文字数に含めない

            以下が要約対象の検索結果です:
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
