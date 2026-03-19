import os
import openai
from dotenv import load_dotenv

def validate_openai_connection():
    """
    Validates the connection to the OpenAI API by loading environment variables
    and making a simple API call.
    """
    try:
        # Load environment variables from .env file
        load_dotenv()
        print("Attempting to load environment variables from .env file...")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment variables.")
            return

        print("OPENAI_API_KEY loaded successfully.")
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=api_key)
        print("OpenAI client initialized.")

        # Make a simple API call to test the connection
        print("Attempting to connect to OpenAI API to list models...")
        models = client.models.list()
        
        print("\nConnection to OpenAI API successful!")
        print("Successfully retrieved a list of models.")
        
        # Optionally print some model IDs
        model_ids = [model.id for model in models.data[:5]]
        print(f"First 5 available models: {model_ids}")

    except openai.APIConnectionError as e:
        print("\n--- FAILED TO CONNECT TO OPENAI API ---")
        print("Error Type: APIConnectionError")
        print(f"Details: {e.__cause__}")
    except openai.RateLimitError as e:
        print("\n--- OPENAI API RATE LIMIT EXCEEDED ---")
        print("Error Type: RateLimitError")
        print(f"Details: {e}")
    except openai.AuthenticationError as e:
        print("\n--- OPENAI API AUTHENTICATION FAILED ---")
        print("Error Type: AuthenticationError")
        print("Please check your OPENAI_API_KEY. It seems to be invalid or expired.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    validate_openai_connection()