"""
BlogRssFetcher - 良質なテックブログからRSSで記事を取得

目的:
- 即応性よりも「大きなトレンド」「思考力強化」「フレーミング力」を重視
- 本当の意味でCutting Edgeなものを識別する常識力を養う
- 深い洞察・戦略分析を提供するソースからの情報収集
"""

import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from openai import OpenAI


class BlogRssFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.aiclient = OpenAI(api_key=config.OPENAI_API_KEY)
        self.srcname = "Expert Blog"
        
        # 良質なブログRSSフィード一覧
        # 選定基準: 思考力強化、フレーミング力、コアコンピタンス認識、Cutting Edge識別
        self.blog_feeds = [
            {
                "name": "Simon Willison",
                "url": "https://simonwillison.net/atom/everything/",
                "category": "AI/LLM Deep Dive",
                "why": "LLM技術の本質的理解、実践的な洞察"
            },
            {
                "name": "Benedict Evans",
                "url": "https://www.ben-evans.com/benedictevans?format=rss",
                "category": "Tech Strategy",
                "why": "テック業界の大局観、フレーミング力"
            },
            {
                "name": "Paul Graham Essays",
                "url": "http://www.aaronsw.com/2002/feeds/pgessays.rss",
                "category": "Startup Thinking",
                "why": "思考力強化、本質を見抜く力"
            },
            {
                "name": "a16z Blog",
                "url": "https://a16z.com/feed/",
                "category": "VC/Trends",
                "why": "大きなトレンド把握、投資家視点"
            },
            {
                "name": "MIT Technology Review",
                "url": "https://www.technologyreview.com/feed/",
                "category": "Tech Research",
                "why": "研究視点、長期トレンド"
            },
            {
                "name": "Stratechery",
                "url": "https://stratechery.com/feed/",
                "category": "Business Strategy", 
                "why": "ビジネス戦略分析、コアコンピタンス"
            },
            {
                "name": "The Gradient",
                "url": "https://thegradient.pub/rss/",
                "category": "AI Research",
                "why": "AI研究の深い解説、学術視点"
            },
            {
                "name": "Lil'Log (Lilian Weng)",
                "url": "https://lilianweng.github.io/index.xml",
                "category": "AI/ML Technical",
                "why": "ML技術の詳細解説、OpenAI研究者視点"
            },
        ]
        
        # 取得する記事の日数（最近N日以内の記事のみ）
        self.days_lookback = getattr(config, 'BLOG_RSS_DAYS_LOOKBACK', 7)
        # 各ブログから取得する最大記事数
        self.max_articles_per_blog = getattr(config, 'BLOG_RSS_MAX_PER_BLOG', 2)

    async def fetch(self):
        """全ブログからRSSを取得し、要約を生成"""
        today = datetime.today().strftime('%Y-%m-%d')
        self.config.logprint.info(f"BlogRssFetcher: Fetching expert blogs ({today})")
        
        all_articles = []
        all_urls = []
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_blog(session, blog) for blog in self.blog_feeds]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    self.config.logprint.error(f"Blog fetch error: {str(result)}")
                    continue
                if result:
                    articles, urls = result
                    all_articles.extend(articles)
                    all_urls.extend(urls)
        
        self.config.logprint.info(f"BlogRssFetcher: Fetched {len(all_articles)} articles from {len(self.blog_feeds)} blogs")
        
        # 記事を要約形式に変換
        summaries = "\n".join(all_articles)
        return summaries, all_urls

    async def _fetch_blog(self, session, blog):
        """個別ブログからRSSを取得"""
        try:
            headers = {"User-Agent": "MochiBot/1.0 (AI News Aggregator)"}
            
            async with session.get(blog["url"], headers=headers, timeout=15) as response:
                if response.status != 200:
                    self.config.logprint.warning(f"Failed to fetch {blog['name']}: Status {response.status}")
                    return None
                
                content = await response.text()
                feed = feedparser.parse(content)
                
                if not feed.entries:
                    self.config.logprint.warning(f"No entries in {blog['name']}")
                    return None
                
                articles = []
                urls = []
                cutoff_date = datetime.now() - timedelta(days=self.days_lookback)
                
                for entry in feed.entries[:self.max_articles_per_blog]:
                    # 日付チェック（可能な場合）
                    published = self._parse_date(entry)
                    if published and published < cutoff_date:
                        continue
                    
                    title = entry.get('title', 'No Title')
                    url = entry.get('link', '')
                    summary = entry.get('summary', entry.get('description', ''))
                    
                    # HTML タグを除去
                    summary = self._strip_html(summary)
                    # 長すぎる場合は切り詰め
                    if len(summary) > 2000:
                        summary = summary[:2000] + "..."
                    
                    article = self._format_article(
                        title=title,
                        url=url,
                        summary=summary,
                        blog_name=blog["name"],
                        category=blog["category"],
                        why_important=blog["why"]
                    )
                    
                    articles.append(article)
                    urls.append(url)
                    
                    self.config.logprint.info(f"  [{blog['name']}] {title[:50]}...")
                
                return articles, urls
                
        except asyncio.TimeoutError:
            self.config.logprint.warning(f"Timeout fetching {blog['name']}")
            return None
        except Exception as e:
            self.config.logprint.error(f"Error fetching {blog['name']}: {str(e)}")
            return None

    def _format_article(self, title, url, summary, blog_name, category, why_important):
        """記事を統一フォーマットに変換"""
        return (
            f"{self.config.FETCHER_START_OF_CONTENT}\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"SRC: {blog_name} ({category})\n"
            f"Why: {why_important}\n"
            f"Snippet: {summary}\n"
            f"{self.config.FETCHER_END_OF_CONTENT}\n"
        )

    def _parse_date(self, entry):
        """RSSエントリから日付をパース"""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
        except Exception:
            pass
        return None

    def _strip_html(self, text):
        """HTMLタグを除去"""
        import re
        # HTMLタグを除去
        clean = re.sub(r'<[^>]+>', '', text)
        # 連続する空白を1つに
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()
