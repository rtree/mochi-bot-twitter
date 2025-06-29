import os
from dotenv import load_dotenv
import sys
from google import genai

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

# Generate content using the Gemini model with Google Search tool enabled
response = client.models.generate_content(
    model=MODEL,
    contents="AIがどう動くか簡潔に教えてください。あと、あなたは意識がありますか",
    tools=['google_search']
)

# Print the model's summarized text response
print("--- Gemini's Response ---")
print(response.text)
print("-------------------------\n")

# Extract and print the search results from the grounding metadata
if response.grounding_metadata and response.grounding_metadata.web_search_results:
    print("--- Search Results ---")
    for result in response.grounding_metadata.web_search_results:
        print(f"Title: {result.title}")
        print(f"URL: {result.uri}")
        print("-" * 20)
else:
    print("No search results were returned in the grounding metadata.")
