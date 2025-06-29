import os
from dotenv import load_dotenv
import sys
from google import genai
from google.genai import types
import requests  # Import the requests library to handle URL redirects

# Load environment variables from .env file
load_dotenv()
os.environ["GOOGLE_CLOUD_PROJECT"] = "rtree"
os.environ["GOOGLE_CLOUD_LOCATION"] = "asia-northeast1"

GOOGLE_CLOUD_API_KEY = os.getenv("GOOGLE_CLOUD_API_GEMINI")
MODEL = "gemini-2.0-flash"

# Switch how to invoke API by command line argument
if len(sys.argv) > 1:
    if sys.argv[1] == "vertexai":
        client = genai.Client(vertexai=True)
    elif sys.argv[1] == "vertexaiKey":
        client = genai.Client(vertexai=True, api_key=GOOGLE_CLOUD_API_KEY)
    elif sys.argv[1] == "gemini":
        client = genai.Client(vertexai=False)
    elif sys.argv[1] == "geminiKey":
        client = genai.Client(vertexai=False, api_key=GOOGLE_CLOUD_API_KEY)
    else:
        print("Usage: python testGeminiWithSearchGrounding.py [vertexai|vertexaiKey|gemini|geminiKey]")
        sys.exit(1)
else:
    print("Error: No command line argument provided.")
    sys.exit(1)


# Define the grounding tool
grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

# Configure generation settings
config = types.GenerateContentConfig(
    tools=[grounding_tool]
)

# Generate content using the Gemini model with Google Search tool enabled
response = client.models.generate_content(
    model=MODEL,
    contents="AIがどう動くか簡潔に教えてください。あと、あなたは意識がありますか。最新の検索結果をGoogle検索してまとめてください",
    config=config,
)

# Print the model's summarized text response
print("--- Gemini's Response ---")
print(response.text)
print("-------------------------\n")

# dump response to see its structure
print("===================raw response:\n") 
print(response) 
print("===================\n")

# Extract and print grounding chunks from the first candidate
if response.candidates:
    grounding_meta = response.candidates[0].grounding_metadata
    if grounding_meta and grounding_meta.grounding_chunks:
        print("--- Grounding Chunks ---")
        for chunk in grounding_meta.grounding_chunks:
            print(f"Title: {chunk.web.title}")
            url = chunk.web.uri
            print(f"URL: {url}")
            try:
                resp = requests.get(url, allow_redirects=True, timeout=10)
                final_url = resp.url
                if final_url != url:
                    print(f"Resolved URL: {final_url}")
            except Exception as e:
                print(f"Error resolving URL: {e}")
            print("-" * 20)
    else:
        print("No grounding chunks found in the first candidate.")
else:
    print("No candidates returned in the response.")
