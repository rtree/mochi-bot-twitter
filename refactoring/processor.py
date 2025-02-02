import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
GPT_MODEL = os.getenv('GPT_MODEL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

class Processor:
    """Processes and summarizes fetched data."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    async def summarize_content(self, content):
        """Summarizes text using GPT."""
        def blocking_summary():
            return self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a summarization assistant."},
                    {"role": "user", "content": f"Please summarize the following content:\n{content}"}
                ]
            ).choices[0].message.content

        return await asyncio.to_thread(blocking_summary)
