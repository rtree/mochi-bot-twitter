import os
import google.generativeai as genai
from config import Config

def get_latest_news_with_api_key():
    """
    Uses the Google Generative AI SDK (with an API key from config.py) and the Google Search tool
    to find the hottest news and print the results with source URLs.
    """
    config = Config()
    google_api_key_gemini = config.GOOGLE_API_KEY_GEMINI

    if not google_api_key_gemini:
        print("Error: GOOGLE_API_KEY_GEMINI not set in your .env file or config.py.")
        return

    try:
        # Configure the generative AI client with the API key
        genai.configure(api_key=google_api_key_gemini)

        # Create a model with the Google Search tool enabled
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=['google_search'],
        )

        # The prompt for the model
        prompt = "What is the hottest news as of today? Provide a summary and the source links."

        print(f"Asking Google AI Gemini: '{prompt}'\n")

        # Generate content
        response = model.generate_content(prompt)

        # Print the model's summarized text response
        print("--- Gemini's Summary ---")
        print(response.text)
        print("------------------------\n")

        # Extract and print the search results from the grounding metadata
        if response.grounding_metadata and response.grounding_metadata.web_search_results:
            print("--- Search Results ---")
            for result in response.grounding_metadata.web_search_results:
                print(f"Title: {result.title}")
                print(f"URL: {result.uri}")
                print("-" * 20)
        else:
            print("No search results were returned in the grounding metadata.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    get_latest_news_with_api_key()
