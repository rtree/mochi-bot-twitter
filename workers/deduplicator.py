import os
import json
import hashlib
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher


class NewsDeduplicator:
    def __init__(self, config):
        self.config = config
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.log')
        self.cache_file = os.path.join(self.cache_dir, 'posted_urls.json')
        self.title_cache_file = os.path.join(self.cache_dir, 'posted_titles.json')
        self.days_to_keep = 7  # 7日分のURLを保持
        self.similarity_threshold = 0.6  # タイトル類似度の閾値（60%以上で重複とみなす）
        
    def _load_cache(self):
        """投稿済みURLキャッシュを読み込み"""
        if not os.path.exists(self.cache_file):
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.config.logprint.warning(f"Failed to load URL cache: {str(e)}")
            return {}

    def _load_title_cache(self):
        """投稿済みタイトルキャッシュを読み込み"""
        if not os.path.exists(self.title_cache_file):
            return {}
        
        try:
            with open(self.title_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.config.logprint.warning(f"Failed to load title cache: {str(e)}")
            return {}
    
    def _save_cache(self, cache):
        """投稿済みURLキャッシュを保存"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.config.logprint.error(f"Failed to save URL cache: {str(e)}")

    def _save_title_cache(self, cache):
        """投稿済みタイトルキャッシュを保存"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.title_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.config.logprint.error(f"Failed to save title cache: {str(e)}")
    
    def _clean_old_entries(self, cache):
        """古いエントリを削除"""
        cutoff_date = (datetime.now() - timedelta(days=self.days_to_keep)).strftime('%Y-%m-%d')
        return {date: data for date, data in cache.items() if date >= cutoff_date}
    
    def _extract_url_from_news(self, news_item):
        """ニュースアイテムからURLを抽出"""
        url_match = re.search(r'(https?://[^\s]+)', news_item)
        return url_match.group(1) if url_match else None

    def _extract_title_from_news(self, news_item):
        """ニュースアイテムからタイトル（最初の文）を抽出"""
        # URLを除去
        text = re.sub(r'https?://[^\s]+', '', news_item).strip()
        # 最初の文を取得（。や、で区切る）
        first_sentence = re.split(r'[。、．\.\n]', text)[0].strip()
        return first_sentence[:100] if first_sentence else text[:100]

    def _normalize_text(self, text):
        """テキストを正規化（比較用）"""
        # 小文字化、記号除去、空白正規化
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _is_similar_title(self, title, posted_titles):
        """タイトルが過去の投稿と類似しているかチェック"""
        normalized_title = self._normalize_text(title)
        
        for posted_title in posted_titles:
            normalized_posted = self._normalize_text(posted_title)
            similarity = SequenceMatcher(None, normalized_title, normalized_posted).ratio()
            
            if similarity >= self.similarity_threshold:
                self.config.logprint.info(f"Similar title found ({similarity:.0%}): '{title[:30]}...' ~ '{posted_title[:30]}...'")
                return True
        
        return False
    
    def filter_duplicates(self, summary):
        """
        投稿済みURLと類似タイトルを除外してサマリーをフィルタリング
        
        Args:
            summary: DELIMITERで区切られた全ニュースサマリー
            
        Returns:
            フィルタリング後のサマリー文字列
        """
        # キャッシュ読み込み
        url_cache = self._load_cache()
        url_cache = self._clean_old_entries(url_cache)
        title_cache = self._load_title_cache()
        title_cache = self._clean_old_entries(title_cache)
        
        # 今日の日付
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 既に投稿されたURL一覧（過去7日分）
        posted_urls = set()
        for urls in url_cache.values():
            posted_urls.update(urls)
        
        # 既に投稿されたタイトル一覧（過去7日分）
        posted_titles = []
        for titles in title_cache.values():
            posted_titles.extend(titles)
        
        # ニュースアイテムを分割
        news_items = summary.split(self.config.TWITTER_DELIMITER)
        news_items = [item.strip() for item in news_items if item.strip()]
        
        # 重複をフィルタリング
        filtered_items = []
        new_urls = []
        new_titles = []
        url_duplicates = 0
        title_duplicates = 0
        
        for item in news_items:
            url = self._extract_url_from_news(item)
            title = self._extract_title_from_news(item)
            
            # URL重複チェック
            if url and url in posted_urls:
                self.config.logprint.info(f"Skipping duplicate URL: {url}")
                url_duplicates += 1
                continue
            
            # タイトル類似度チェック（同じ話題の別記事を除外）
            all_titles = posted_titles + new_titles
            if title and self._is_similar_title(title, all_titles):
                title_duplicates += 1
                continue
            
            # 重複なし → 追加
            filtered_items.append(item)
            if url:
                new_urls.append(url)
                posted_urls.add(url)
            if title:
                new_titles.append(title)
        
        # 今日の投稿を記録
        if today not in url_cache:
            url_cache[today] = []
        url_cache[today].extend(new_urls)
        
        if today not in title_cache:
            title_cache[today] = []
        title_cache[today].extend(new_titles)
        
        # キャッシュ保存
        self._save_cache(url_cache)
        self._save_title_cache(title_cache)
        
        total_removed = url_duplicates + title_duplicates
        self.config.logprint.info(
            f"Filtered {len(news_items)} items -> {len(filtered_items)} items "
            f"(removed {total_removed}: {url_duplicates} URL dups, {title_duplicates} similar titles)"
        )
        
        # フィルタリング後のサマリーを再構築
        return self.config.TWITTER_DELIMITER.join(filtered_items)
