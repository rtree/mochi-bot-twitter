import os
import google.generativeai as genai

# Get the API key from the environment variable
google_api_key = os.environ.get("GOOGLE_API_KEY")

if not google_api_key:
    print("Error: GOOGLE_API_KEY environment variable not set.")
else:
    try:
        # Configure the generative AI client
        genai.configure(api_key=google_api_key)

        # Create the model
        model = genai.GenerativeModel('gemini-pro')

        # Ask the question
        response = model.generate_content("What is the hottest news as of today? Use Google Search to ground your answer.")

        # Print the response
        print(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")
