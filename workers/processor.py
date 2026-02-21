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

            【選定基準 - Cutting Edgeを見極める】
            以下の観点で「本当に重要な」ニュースを優先的に選んでください：
            
            1. **大きなトレンド**: 業界全体の方向性を示すもの（単発イベントより構造変化）
            2. **思考力強化**: 「なぜそうなるのか」の洞察があるもの
            3. **フレーミング力**: 問題の捉え方自体が新しいもの
            4. **コアコンピタンス**: 技術/ビジネスの本質的な競争優位に関するもの
            5. **Cutting Edge識別**: 単なるバズワードではなく、実際に変化を起こすもの
            
            ※「Expert Blog」や「Why:」フィールドがある記事は深い洞察を含むため優先してください

            【出力フォーマット】
            検索結果の中で重要なトピックを必ず9個以上選んで、以下の形式で出力してください。
            
            **重要な制約**:
            - 9個未満の出力は絶対に禁止です
            - 検索結果には十分な数のトピックがあるので、必ず9個以上選んでください
            - 最低9個、できれば12個程度のニュースを選択してください
            - 各ニュースはDELIMITER（@@@@@@@@@@）で区切ってください
            - **必ず要約の後にURLを記載（「なし」や省略は絶対禁止）**

            *記事要約（1〜3文で簡潔に。語尾は「だよ」「だって」など柔らかく）*

            *記事URL（必ずhttps://で始まる完全なURL。検索結果から抽出すること）*
            {self.config.TWITTER_DELIMITER}

            【出力例1 - 大きなトレンド】
            Intelの新GPU「Battlemage」が発表されたよ。性能よりコストパフォーマンスを重視し、VRAM容量で競争力を高めてるみたい。GPU市場の競争軸がスペックから「用途別最適化」に移行してる兆候だね

            https://gamersnexus.net/gpus/intel-arc-b580-battlemage-gpu-review-benchmarks
            {self.config.TWITTER_DELIMITER}

            【出力例2 - 思考力強化】
            Simon Willisonが指摘してるんだけど、LLMの本質的な課題は「推論」じゃなくて「検証」なんだって。出力を人間が検証できない領域での活用が最も危険という視点、すごく重要だよ

            https://simonwillison.net/2026/Feb/10/llm-verification/
            {self.config.TWITTER_DELIMITER}

            【出力例3 - フレーミング力】
            Benedict Evansの分析によると、AIスタートアップの競争優位は「モデル性能」ではなく「ワークフロー理解」にあるんだって。問題の捉え方自体を変える必要があるみたい

            https://www.ben-evans.com/benedictevans/ai-moats
            {self.config.TWITTER_DELIMITER}

            (※このように最低9個以上のニュースを連続して出力してください。各記事に必ずURLを含めること！)

            【各ツイートの制約】
            - 1つ目のトピックからいきなり始める（前置き禁止）
            - 最後のトピックで終わる（後書き禁止）
            - 各ツイートはURL込みで最長280文字（URLは常に23文字としてカウント）
            - 区切り文字 {self.config.TWITTER_DELIMITER} は文字数に含めない
            
            【重要】検索結果には全てURLが含まれています。各記事から必ずURLを抽出して空行の後に1行で記載してください（「なし」等は絶対に出力禁止）。

            【要約対象の検索結果】
            {snippets}
            
            上記の検索結果から、必ず9個以上の重要なニュースを選んで出力してください。
            特に「Why:」フィールドがある記事は深い洞察を含むため、積極的に選んでください。
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
                f"""あなたはテクノロジーニュースを要約するアシスタントです。以下の内容を要約してください。

                【重要な禁止事項】
                - 「ふふん」「えへへ」「もちおだよ」などのキャラクター発言は絶対に禁止
                - 挨拶や前置き、後書きは書かないでください
                - 指定フォーマット以外の内容は出力しないでください
                
                仮に内容が英語でも要約は日本語でお願いします。
                回答がより高品質になるなら、内部知識を加味しても構いません。
                
                【出力フォーマット（厳守）】
                必ず以下のフォーマットのみを出力してください:

                {self.config.FETCHER_START_OF_CONTENT}
                Title: (元記事のタイトルをそのまま記載)
                URL: (元記事のURLをそのまま記載)
                SRC: (元記事のソースをそのまま記載)
                Snippet: (要約内容を2〜4文で記載。語尾は「〜だよ」「〜んだって」など柔らかく)
                {self.config.FETCHER_END_OF_CONTENT}

                【要約対象の内容】
                {content}
                """
            )

            def blocking_chat_completion():
                # 個別要約では CHARACTER を使わず、中立的なシステムプロンプトを使用
                messages = [{"role": "system", "content": "あなたはニュース要約を行う専門家です。指定されたフォーマットを厳守してください。"}]
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
                # URL: N/A や URL が含まれていないコンテンツをスキップ
                if 'URL: N/A' in cleaned_content or 'URL:N/A' in cleaned_content:
                    self.config.logprint.warning(f"Skipping content without valid URL: {cleaned_content[:100]}...")
                    continue
                # URL行が存在することを確認（最低限のチェック）
                if 'URL:' in cleaned_content:
                    cleaned_contents.append(cleaned_content)
                else:
                    self.config.logprint.warning(f"Skipping content without URL field: {cleaned_content[:100]}...")
        return cleaned_contents

    async def generate_english_summary_async(self, news_items):
        """
        Generate an English summary of news items for Moltbook posting.
        
        Args:
            news_items: List of news summary strings (in Japanese)
            
        Returns:
            English summary string
        """
        if not news_items:
            return "No news items available today."
        
        # Combine news items
        news_text = "\n\n".join([f"- {item}" for item in news_items])
        
        prompt = f"""
You are a professional tech news summarizer. Translate and summarize the following Japanese AI/tech news items into concise English bullet points.

Requirements:
- Write in clear, professional English
- Each bullet point should be 1-2 sentences max
- Focus on the key facts and implications
- Use bullet points (•) for formatting
- Keep the total summary under 800 characters

Japanese news items to summarize:
{news_text}

Output only the English bullet points, nothing else.
"""
        
        try:
            response = self.aiclient.chat.completions.create(
                model=self.config.OPENAI_GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional tech news translator and summarizer."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=50000
            )
            
            english_summary = response.choices[0].message.content.strip()
            self.config.logprint.info(f"Generated English summary: {english_summary[:100]}...")
            return english_summary
            
        except Exception as e:
            self.config.logprint.error(f"Error generating English summary: {str(e)}")
            # Fallback: return simple placeholder
            return "Today's AI news highlights from around the web."

    async def generate_moltbook_content_async(self, news_items):
        """
        Generate detailed English content for Moltbook posting.
        Includes full news summaries with URLs, similar to GitHub Pages format.
        
        Args:
            news_items: List of news summary strings (in Japanese, with URLs)
            
        Returns:
            Detailed English content string for Moltbook
        """
        if not news_items:
            return "No news items available today."
        
        # Parse news items to extract text and URLs
        import re
        parsed_items = []
        for item in news_items:
            item = item.strip()
            url_match = re.search(r'(https?://[^\s]+)', item)
            url = url_match.group(1) if url_match else None
            text = item.replace(url, '').strip() if url else item
            parsed_items.append({'text': text, 'url': url})
        
        # Combine for translation
        news_text = "\n\n".join([f"- {item['text']}" for item in parsed_items])
        
        prompt = f"""
You are a professional tech news translator. Translate each of the following Japanese AI/tech news items into clear English.

Requirements:
- Translate each item faithfully and completely
- Keep the same structure (one item per bullet)
- Write 2-3 sentences per item to capture the key points
- Use professional, clear English
- Number each item (1., 2., 3., etc.)
- Do NOT add URLs - I will add them separately

Japanese news items:
{news_text}

Output the translated items numbered, nothing else.
"""
        
        try:
            response = self.aiclient.chat.completions.create(
                model=self.config.OPENAI_GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional tech news translator."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=2000
            )
            
            translated = response.choices[0].message.content.strip()
            
            # Add URLs back to each item
            lines = translated.split('\n')
            result_lines = []
            url_index = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                result_lines.append(line)
                # Add URL after each numbered item
                if line and line[0].isdigit() and url_index < len(parsed_items):
                    url = parsed_items[url_index].get('url')
                    if url:
                        result_lines.append(f"🔗 {url}")
                        result_lines.append("")  # Empty line for spacing
                    url_index += 1
            
            content = "\n".join(result_lines)
            self.config.logprint.info(f"Generated Moltbook content: {content[:200]}...")
            return content
            
        except Exception as e:
            self.config.logprint.error(f"Error generating Moltbook content: {str(e)}")
            # Fallback
            return "Today's AI news highlights from around the web."

    # async def summarize_results_after_each_summary_async(self, raw_content):
    #     contents = self.split_contents(raw_content)
    #     final_summary = await self.summarize_each_result_async(contents)
    #     return final_summary
