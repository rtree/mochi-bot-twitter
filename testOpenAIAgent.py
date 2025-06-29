
import os
from azure.identity import DefaultAzureCredential
from azure.ai.assistant import AgentsClient
from azure.ai.assistant.models import (
    AssistantThread,
    ThreadMessage,
)
from config import Config

class OpenAIAgent:
    def __init__(self):
        # Load configuration from config.py
        self.config = Config()
        self.azure_project_endpoint = self.config.AZURE_PROJECT_ENDPOINT
        self.azure_agent_id = self.config.AZURE_AGENT_ID

    def setup_credentials(self):
        """Sets up Azure credentials from environment variables loaded by Config."""
        if self.config.AZURE_CLIENT_ID:
            os.environ["AZURE_CLIENT_ID"] = self.config.AZURE_CLIENT_ID
        if self.config.AZURE_CLIENT_SECRET:
            os.environ["AZURE_CLIENT_SECRET"] = self.config.AZURE_CLIENT_SECRET
        if self.config.AZURE_TENANT_ID:
            os.environ["AZURE_TENANT_ID"] = self.config.AZURE_TENANT_ID
        return DefaultAzureCredential()

    def run_agent_with_bing_grounding(self, user_query):
        """
        Uses a predefined agent to run a query.
        """
        if not self.azure_project_endpoint or not self.azure_agent_id:
            print("Error: AZURE_PROJECT_ENDPOINT and AZURE_AGENT_ID must be set in your .env file.")
            return

        try:
            credential = self.setup_credentials()
            client = AgentsClient(endpoint=self.azure_project_endpoint, credential=credential)

            try:
                assistant = client.get_assistant(self.azure_agent_id)
                print(f"Using predefined agent: {assistant.name} ({assistant.id})")
            except Exception as e:
                 print(f"Could not retrieve agent '{self.azure_agent_id}'. Please ensure it exists. Error: {e}")
                 return

            # Create a thread to interact with the assistant
            thread_response = client.create_thread(
                AssistantThread(
                    messages=[
                        ThreadMessage(
                            role="user",
                            content=user_query
                        )
                    ]
                )
            )
            print(f"Thread created with ID: {thread_response.id}")

            # Run the thread and get the response
            run_response = client.run_thread(assistant_id=self.azure_agent_id, thread_id=thread_response.id)
            print(f"Run created with ID: {run_response.id}")

            # Wait for the run to complete
            while run_response.status in ["in_progress", "queued"]:
                print(f"Run status: {run_response.status}")
                run_response = client.get_run(run_id=run_response.id, thread_id=thread_response.id)
                import time
                time.sleep(5)
            
            print(f"Final run status: {run_response.status}")

            # Get the messages from the thread
            messages_response = client.get_messages(thread_id=thread_response.id)
            for message in messages_response.data:
                if message.role == "assistant":
                    for content_item in message.content:
                        print(f"Assistant response: {content_item.text.value}")
                        # Citations will be in the annotations
                        if hasattr(content_item.text, 'annotations') and content_item.text.annotations:
                            print("Citations:")
                            for annotation in content_item.text.annotations:
                                if hasattr(annotation, 'file_citation'):
                                    print(f"- {annotation.file_citation.quote}")

        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Example usage:
    # Make sure to set the following environment variables in your .env file:
    # AZURE_PROJECT_ENDPOINT, AZURE_AGENT_ID,
    # AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
    
    agent = OpenAIAgent()
    agent.run_agent_with_bing_grounding("What are the latest features of the new Surface Pro?")

