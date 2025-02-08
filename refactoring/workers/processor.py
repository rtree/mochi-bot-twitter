import asyncio
from openai import OpenAI

class Processor:
    def __init__(self, context, config):
        self.context  = context
        self.config   = config
        self.aiclient = OpenAI(api_key=config.OPENAI_API_KEY)

    async def summarize_results_async(self, snippets):
        p_src = (
            f"{self.config.CHARACTER}。あなたは検索結果を要約し、調査報告として回答を作成します。"
            f" 会話履歴を踏まえつつ私が知りたいことの主旨を把握の上で、検索結果を要約し回答を作ってください。"
            f" 仮に検索結果が英語でも回答は日本語でお願いします。"
            f" なお、回答がより高品質になるのならば、あなたの内部知識を加味して回答を作っても構いません。"
            f" 回答のフォーマットはこちら:"
            f" - 書き出しは 今日のニュースだよ！ "
            f" - 書き出しに続き全記事のまとめのコメントをし一度{self.config.TWITTER_DELIMITER}で切る"
            f" - 投稿先はX(Twitter)なので、Markdownは使わないでください"
            f" - 区切りは1記事ごと{self.config.TWITTER_DELIMITER}の区切り文字のみ。180文字ごとに区切ること。区切り文字は文字数に含めない。また、要約の冒頭に箇条書きなどの ・ は含めないでください"
            f" - 参考記事のURLは要約に含めない"
            f" - 要約が終わった後に{self.config.TWITTER_DELIMITER}で切ったのち、締めのコメントをする。締めのコメントは内容からいきなり書き始めてください。つまり、 締めのコメント などの見出しはつけないでください"
            f" - 要約の文体も{self.config.AINAME}になるように気をつけてください"
            f" - 最後に参考記事のURLを投稿する"
            f" - 参考記事の各URKの前に必ず{self.config.TWITTER_DELIMITER}と書き、次の行にリンクを記載"
            f" 以下が要約対象の検索結果です:"
            f"  {snippets}"
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
