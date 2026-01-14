import os
import json
import hashlib
from datetime import datetime, timedelta


class NewsDeduplicator:
    def __init__(self, config):
        self.config = config
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.log')
        self.cache_file = os.path.join(self.cache_dir, 'posted_urls.json')
        self.days_to_keep = 7  # 7日分のURLを保持
        
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
    
    def _save_cache(self, cache):
        """投稿済みURLキャッシュを保存"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.config.logprint.error(f"Failed to save URL cache: {str(e)}")
    
    def _clean_old_entries(self, cache):
        """古いエントリを削除"""
        cutoff_date = (datetime.now() - timedelta(days=self.days_to_keep)).strftime('%Y-%m-%d')
        return {date: urls for date, urls in cache.items() if date >= cutoff_date}
    
    def _extract_url_from_news(self, news_item):
        """ニュースアイテムからURLを抽出"""
        import re
        url_match = re.search(r'(https?://[^\s]+)', news_item)
        return url_match.group(1) if url_match else None
    
    def filter_duplicates(self, summary):
        """
        投稿済みURLを除外してサマリーをフィルタリング
        
        Args:
            summary: DELIMITERで区切られた全ニュースサマリー
            
        Returns:
            フィルタリング後のサマリー文字列
        """
        # キャッシュ読み込み
        cache = self._load_cache()
        cache = self._clean_old_entries(cache)
        
        # 今日の日付
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 既に投稿されたURL一覧（過去7日分）
        posted_urls = set()
        for urls in cache.values():
            posted_urls.update(urls)
        
        # ニュースアイテムを分割
        news_items = summary.split(self.config.TWITTER_DELIMITER)
        news_items = [item.strip() for item in news_items if item.strip()]
        
        # 重複をフィルタリング
        filtered_items = []
        new_urls = []
        
        for item in news_items:
            url = self._extract_url_from_news(item)
            
            if url:
                if url not in posted_urls:
                    filtered_items.append(item)
                    new_urls.append(url)
                    posted_urls.add(url)  # 同じバッチ内での重複も防ぐ
                else:
                    self.config.logprint.info(f"Skipping duplicate URL: {url}")
            else:
                # URLがない場合はそのまま含める（念のため）
                filtered_items.append(item)
        
        # 今日の投稿URLを記録
        if today not in cache:
            cache[today] = []
        cache[today].extend(new_urls)
        
        # キャッシュ保存
        self._save_cache(cache)
        
        self.config.logprint.info(f"Filtered {len(news_items)} items -> {len(filtered_items)} items (removed {len(news_items) - len(filtered_items)} duplicates)")
        
        # フィルタリング後のサマリーを再構築
        return self.config.TWITTER_DELIMITER.join(filtered_items)
