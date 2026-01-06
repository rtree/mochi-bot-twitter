import os
import re
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class NewsPageGenerator:
    def __init__(self, config):
        self.config = config
        # 現在のリポジトリ内でGitHub Pagesを使用
        self.pages_repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # プロジェクトルート
        self.posts_dir = os.path.join(self.pages_repo_path, '_posts')
        self.twitter_url = config.TWITTER_PROFILE_URL  # Xアカウント

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

    def _fetch_ogp_image(self, url):
        """URLからOGP画像を取得"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; MochiBot/1.0)'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # OGP画像を探す
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return og_image['content']
            
            # Twitter Card画像を探す
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                return twitter_image['content']
            
            return None
        except Exception as e:
            self.config.logprint.warning(f"Failed to fetch OGP image from {url}: {str(e)}")
            return None

    def _extract_title_from_text(self, text):
        """ニュース本文から短いタイトルを抽出"""
        # 最初の文を取得して短くする
        text = text.strip()
        # 最初の句点または。で区切る
        match = re.split(r'[。．\.、]', text)
        if match:
            title = match[0].strip()
            # 長すぎる場合は切り詰め
            if len(title) > 50:
                title = title[:47] + "..."
            return title
        return text[:50] + "..." if len(text) > 50 else text

    def _generate_markdown(self, all_news_content, urls):
        """Markdownファイルを生成"""
        today = datetime.now()
        date_str = today.strftime('%Y-%m-%d')
        date_display = today.strftime('%Y年%m月%d日')
        
        # ファイル名: YYYY-MM-DD-daily-news.md
        filename = f"{date_str}-daily-news.md"
        filepath = os.path.join(self.posts_dir, filename)
        
        # ニュースを分割してパース
        news_items = all_news_content.split(self.config.TWITTER_DELIMITER)
        news_items = [item.strip() for item in news_items if item.strip()]
        
        # 各ニュースアイテムを構造化
        parsed_items = []
        for item in news_items:
            item = item.strip()
            url = None
            text = item
            
            # URLを抽出（本文中のどこにあっても対応）
            url_match = re.search(r'(https?://[^\s]+)', item)
            if url_match:
                url = url_match.group(1)
                # URLを本文から除去
                text = item.replace(url, '').strip()
            else:
                # URLがない記事はスキップ
                self.config.logprint.warning(f"Skipping news item without URL: {text[:50]}...")
                continue
            
            title = self._extract_title_from_text(text)
            ogp_image = self._fetch_ogp_image(url) if url else None
            
            parsed_items.append({
                'title': title,
                'text': text,
                'url': url,
                'ogp_image': ogp_image
            })
        
        # メインタイトルは最初のニュースから
        main_title = parsed_items[0]['title'] if parsed_items else f"{date_display}のニュース"
        
        # Markdownコンテンツ生成
        content = self._build_markdown_content(date_display, main_title, parsed_items, urls)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.config.logprint.info(f"Generated markdown file: {filepath}")
        return filepath

    def _build_markdown_content(self, date_display, main_title, parsed_items, urls):
        """Markdownコンテンツを構築"""
        now = datetime.now()
        
        # Jekyll Front Matter
        content = f"""---
layout: post
title: "{main_title}"
date: {now.strftime('%Y-%m-%d %H:%M:%S')} +0900
categories: news
---

📅 {date_display} | [アーカイブ]({{{{ site.baseurl }}}}/news/) | [@techandeco4242]({self.twitter_url})

Xに収まりきらなかったニュースをお届け 🐱

---

"""
        # 各ニュースアイテムを追加
        for i, item in enumerate(parsed_items, 1):
            content += f'### {i}. {item["title"]}\n\n'
            content += f'{item["text"]}\n\n'
            
            # OGP画像があれば表示（クリッカブル）
            if item['ogp_image'] and item['url']:
                content += f'[![{item["title"]}]({item["ogp_image"]})]({item["url"]})\n\n'
            
            if item['url']:
                domain = urlparse(item['url']).netloc
                content += f'🔗 [{domain}]({item["url"]})\n\n'
            
            content += '\n---\n\n'

        # フッター
        content += f"""[📅 過去のニュース]({{{{ site.baseurl }}}}/news/) | [🐱 テクの猫をフォロー]({self.twitter_url})
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
