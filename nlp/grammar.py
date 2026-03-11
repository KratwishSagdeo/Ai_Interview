import requests
from Ai_Interview.configs.config import LANGUAGETOOL_URL
class GrammarAnalyzer:

    def analyze(self, text):

        response = requests.post(
            LANGUAGETOOL_URL,
            data={
                "text": text,
                "language": "en-US"
            }
        )

        matches = response.json()["matches"]

        return len(matches)