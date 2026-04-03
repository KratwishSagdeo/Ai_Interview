import os
import logging
from groq import Groq

logger = logging.getLogger("groq_client")

class GroqClientProvider:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing.")

        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"      # ✅ fixed — old model decommissioned
        logger.info(f"Using Groq model: {self.model}")

    def get_client(self):
        return self.client