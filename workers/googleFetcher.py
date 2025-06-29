import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
import requests  # For resolving URL redirects

class GoogleFetcher:
    def __init__(self, context, config):
        self.context = context
        self.config = config

        # Load environment and set Google Cloud settings
        load_dotenv()
        os.environ["GOOGLE_CLOUD_PROJECT"]  = os.getenv("GOOGLE_CLOUD_PROJECT",self.config.GOOGLE_CLOUD_PROJECT)
        os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION",self.config.GOOGLE_CLOUD_LOCATION)

        # Initialize Gemini client
        # Use Google API key from config or environment
        api_key = os.getenv("GOOGLE_CLOUD_API_GEMINI", self.config.GOOGLE_CLOUD_API_GEMINI)
        self.client = genai.Client(vertexai=False, api_key=api_key)
        self.model = "gemini-2.0-flash"

    async def fetch(self):
        """
        Fetch the latest news via Gemini with Google Search grounding and return summary and URLs.
        """
        # Define the grounding tool for Google Search
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        # Configure generation settings
        gen_config = types.GenerateContentConfig(
            tools=[grounding_tool]
        )
        # Compose query with today's date
        query = (
            f"今日のニュースをまとめて。今日は ({datetime.today().strftime('%Y-%m-%d')}) です。"
            "ジャンルは経済・テクノロジーでお願いします。最新の検索結果をGoogle検索してまとめてください"
        )
        # Generate content
        response = self.client.models.generate_content(
            model=self.model,
            contents=query,
            config=gen_config,
        )
        # Extract summary text
        summary = response.text
        # Extract grounding URLs
        urls = []
        if response.candidates:
            grounding_meta = response.candidates[0].grounding_metadata
            if grounding_meta and grounding_meta.grounding_chunks:
                self.config.logprint.info("Google Search Results:")
                for chunk in grounding_meta.grounding_chunks:
                    title = chunk.web.title
                    url = chunk.web.uri
                    try:
                        resp = requests.get(url, allow_redirects=True, timeout=10)
                        final_url = resp.url
                    except Exception as e:
                        final_url = url
                        self.config.logprint.error(f"Error resolving {url}: {e}")
                    self.config.logprint.info(f"Title: {title}")
                    self.config.logprint.info(f"URL: {final_url}")
                    self.config.logprint.info("---")
                    urls.append(final_url)
        return summary, urls
