import asyncio
import aiohttp
from datetime import datetime


class MoltbookFetcher:
    """
    Fetcher for Moltbook - A Social Network for AI Agents
    https://www.moltbook.com/
    
    Fetches top/trending posts from Moltbook API.
    """
    
    def __init__(self, context, config):
        self.context = context
        self.config = config
        self.base_url = "https://www.moltbook.com/api/v1"
        self.srcname = "Moltbook"
        
    async def fetch(self):
        """Fetch trending Moltbook posts and return summaries with URLs."""
        today = datetime.today().strftime('%Y-%m-%d')
        msg = f"今日のMoltbookのトレンド ({today}) をまとめます。"
        self.config.logprint.info(f"-User input: '{msg}'")
        
        # Fetch top posts
        moltbook_data = await self._fetch_posts()
        
        if not moltbook_data or not moltbook_data.get("posts"):
            self.config.logprint.error("No data fetched from Moltbook.")
            return "Moltbookからデータを取得できませんでした。", []
        
        fetched_summaries = self._format_posts(moltbook_data["posts"])
        return fetched_summaries, moltbook_data["urls"]
    
    async def _fetch_posts(self, sort="top", limit=None):
        """
        Fetch posts from Moltbook API.
        
        Args:
            sort: Sorting method - "top", "hot", "new", "rising"
            limit: Number of posts to fetch
        """
        limit = limit or getattr(self.config, 'MOLTBOOK_SEARCH_RESULTS', 10)
        
        url = f"{self.base_url}/posts"
        params = {
            "sort": sort,
            "limit": limit
        }
        
        headers = {
            "User-Agent": "MochiBot/1.0",
            "Accept": "application/json"
        }
        
        # Add API key if available (optional for public endpoints)
        api_key = getattr(self.config, 'MOLTBOOK_API_KEY', None)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        self.config.logprint.error(f"Failed to fetch Moltbook posts. Status: {response.status}")
                        # Try without auth if we got 401
                        if response.status == 401:
                            del headers["Authorization"]
                            async with session.get(url, headers=headers, params=params) as retry_response:
                                if retry_response.status != 200:
                                    return None
                                data = await retry_response.json()
                        else:
                            return None
                    else:
                        data = await response.json()
                    
                    # Check if data is None or empty
                    if data is None:
                        self.config.logprint.error("Moltbook API returned None")
                        return None
                    
                    # Parse the response
                    posts = []
                    urls = []
                    
                    # Handle different response formats
                    if isinstance(data, list):
                        post_list = data
                    elif isinstance(data, dict):
                        post_list = data.get("data", data.get("posts", []))
                        if isinstance(post_list, dict):
                            post_list = post_list.get("posts", [])
                    else:
                        post_list = []
                    
                    for post in post_list:
                        post_data = {
                            "id": post.get("id", ""),
                            "title": post.get("title", ""),
                            "content": post.get("content", ""),
                            "author": post.get("author", {}).get("name", post.get("author_name", "Unknown")),
                            "upvotes": post.get("upvotes", post.get("karma", 0)),
                            "downvotes": post.get("downvotes", 0),
                            "comments": post.get("comment_count", post.get("comments", 0)),
                            "submolt": post.get("submolt", {}).get("name", post.get("submolt_name", "general")),
                            "created_at": post.get("created_at", ""),
                            "url": f"https://www.moltbook.com/post/{post.get('id', '')}"
                        }
                        posts.append(post_data)
                        urls.append(post_data["url"])
                    
                    self.config.logprint.info(f"Moltbook Search Results ({sort}):")
                    for post in posts[:5]:  # Log first 5
                        self.config.logprint.info(f"Title: {post['title']}")
                        self.config.logprint.info(f"Author: u/{post['author']}")
                        self.config.logprint.info(f"Upvotes: {post['upvotes']}")
                        self.config.logprint.info(f"URL: {post['url']}")
                        self.config.logprint.info("---")
                    
                    return {"posts": posts, "urls": urls}
                    
        except Exception as e:
            self.config.logprint.error(f"Error fetching Moltbook posts: {str(e)}")
            return None
    
    def _format_posts(self, posts):
        """Format posts into summary strings."""
        content_list = []
        
        for post in posts:
            # Truncate content if too long
            content = post.get("content", "")
            if len(content) > 500:
                content = content[:500] + "..."
            
            # Build formatted output
            formatted = (
                f"{self.config.FETCHER_START_OF_CONTENT}\n"
                f"Title: {post['title']}\n"
                f"URL: {post['url']}\n"
                f"SRC: {self.srcname}\n"
                f"Author: u/{post['author']} | Submolt: m/{post['submolt']}\n"
                f"Upvotes: {post['upvotes']} | Comments: {post['comments']}\n"
                f"Snippet: {content}\n"
                f"{self.config.FETCHER_END_OF_CONTENT}\n"
            )
            content_list.append(formatted)
        
        return "\n".join(content_list)
    
    async def search(self, query, limit=None):
        """
        Semantic search for posts and comments on Moltbook.
        
        Args:
            query: Search query (natural language works best)
            limit: Max results to return
        """
        limit = limit or getattr(self.config, 'MOLTBOOK_SEARCH_RESULTS', 10)
        
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "type": "all",
            "limit": limit
        }
        
        headers = {
            "User-Agent": "MochiBot/1.0",
            "Accept": "application/json"
        }
        
        api_key = getattr(self.config, 'MOLTBOOK_API_KEY', None)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        self.config.logprint.error(f"Failed to search Moltbook. Status: {response.status}")
                        return None
                    
                    data = await response.json()
                    results = data.get("results", [])
                    
                    posts = []
                    urls = []
                    
                    for result in results:
                        post_data = {
                            "id": result.get("id", ""),
                            "type": result.get("type", "post"),
                            "title": result.get("title", ""),
                            "content": result.get("content", ""),
                            "author": result.get("author", {}).get("name", "Unknown"),
                            "upvotes": result.get("upvotes", 0),
                            "similarity": result.get("similarity", 0),
                            "submolt": result.get("submolt", {}).get("name", "general"),
                            "url": f"https://www.moltbook.com/post/{result.get('post_id', result.get('id', ''))}"
                        }
                        posts.append(post_data)
                        urls.append(post_data["url"])
                    
                    return {"posts": posts, "urls": urls, "query": query}
                    
        except Exception as e:
            self.config.logprint.error(f"Error searching Moltbook: {str(e)}")
            return None
    async def post(self, title, content, submolt="general"):
        """
        Post to Moltbook.
        
        Args:
            title: Post title
            content: Post content
            submolt: Target submolt (default: "general")
            
        Returns:
            dict with post info on success, None on failure
        """
        api_key = getattr(self.config, 'MOLTBOOK_API_KEY', None)
        if not api_key:
            self.config.logprint.error("MOLTBOOK_API_KEY not configured. Cannot post to Moltbook.")
            return None
        
        url = f"{self.base_url}/posts"
        headers = {
            "User-Agent": "MochiBot/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "submolt": submolt,
            "title": title,
            "content": content
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if response.status != 200 and response.status != 201:
                        self.config.logprint.error(f"Failed to post to Moltbook. Status: {response.status}, Error: {data}")
                        return None
                    
                    if data.get("success"):
                        post_info = data.get("post", {})
                        post_url = f"https://www.moltbook.com{post_info.get('url', '')}"
                        self.config.logprint.info(f"Posted to Moltbook: {post_url}")
                        return {
                            "id": post_info.get("id"),
                            "title": post_info.get("title"),
                            "url": post_url
                        }
                    else:
                        self.config.logprint.error(f"Moltbook post failed: {data.get('error', 'Unknown error')}")
                        return None
                    
        except Exception as e:
            self.config.logprint.error(f"Error posting to Moltbook: {str(e)}")
            return None