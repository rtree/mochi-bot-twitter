import os
import subprocess
from datetime import datetime
from pathlib import Path


class NewsPageGenerator:
    def __init__(self, config):
        self.config = config
        # 現在のリポジトリ内でGitHub Pagesを使用
        self.pages_repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # プロジェクトルート
        self.posts_dir = os.path.join(self.pages_repo_path, '_posts')

    def generate_and_publish(self, all_news_content, urls):
        """
        全ニュースをMarkdownファイルとして生成し、GitHubにpush
        
        Args:
            all_news_content: 全ニュースの要約テキスト（区切り文字で分割済み）
            urls: ニュースのURL一覧
        """
        try:
            # _postsディレクトリ作成
            os.makedirs(self.posts_dir, exist_ok=True)
            
            # Markdownファイル生成
            filepath = self._generate_markdown(all_news_content, urls)
            
            # GitHubにpush
            self._push_to_github(filepath)
            
            self.config.logprint.info(f"News page published successfully: {filepath}")
            return True
            
        except Exception as e:
            self.config.elogprint.error(f"Failed to publish news page: {str(e)}")
            return False

    def _generate_markdown(self, all_news_content, urls):
        """Markdownファイルを生成"""
        today = datetime.now()
        date_str = today.strftime('%Y-%m-%d')
        date_display = today.strftime('%Y年%m月%d日')
        
        # ファイル名: YYYY-MM-DD-daily-news.md
        filename = f"{date_str}-daily-news.md"
        filepath = os.path.join(self.posts_dir, filename)
        
        # ニュースを分割
        news_items = all_news_content.split(self.config.TWITTER_DELIMITER)
        news_items = [item.strip() for item in news_items if item.strip()]
        
        # Markdownコンテンツ生成
        content = self._build_markdown_content(date_display, news_items, urls)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.config.logprint.info(f"Generated markdown file: {filepath}")
        return filepath

    def _build_markdown_content(self, date_display, news_items, urls):
        """Markdownコンテンツを構築"""
        # Jekyll Front Matter
        content = f"""---
layout: post
title: "{date_display}のテック・経済ニュース"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} +0900
categories: news
---

# {date_display}のテック・経済ニュース

もちおがお届けする今日のニュースまとめだよ！

---

"""
        # 各ニュースアイテムを追加
        for i, item in enumerate(news_items, 1):
            # URLを本文から抽出（末尾にあるはず）
            lines = item.strip().split('\n')
            url = None
            text_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('http://') or line.startswith('https://'):
                    url = line
                elif line:
                    text_lines.append(line)
            
            text = ' '.join(text_lines)
            
            content += f"## {i}. ニュース\n\n"
            content += f"{text}\n\n"
            if url:
                content += f"🔗 [記事を読む]({url})\n\n"
            content += "---\n\n"

        # フッター
        content += f"""
## 参考リンク一覧

"""
        for i, url in enumerate(urls, 1):
            if url:
                content += f"{i}. {url}\n"

        content += f"""

---

*このページは自動生成されています。by もちお 🐱*
"""
        return content

    def _push_to_github(self, filepath):
        """GitHubにpush"""
        try:
            # git add
            subprocess.run(
                ['git', 'add', filepath],
                cwd=self.pages_repo_path,
                check=True
            )
            
            # git commit
            today = datetime.now().strftime('%Y-%m-%d')
            subprocess.run(
                ['git', 'commit', '-m', f'Add daily news for {today}'],
                cwd=self.pages_repo_path,
                check=True
            )
            
            # git push
            subprocess.run(
                ['git', 'push'],
                cwd=self.pages_repo_path,
                check=True
            )
            
            self.config.logprint.info("Successfully pushed to GitHub")
            
        except subprocess.CalledProcessError as e:
            self.config.elogprint.error(f"Git operation failed: {str(e)}")
            raise
