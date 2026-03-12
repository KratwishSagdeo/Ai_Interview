# Import grammar correction library
import language_tool_python


class GrammarAnalyzer:

    def __init__(self):

        # Initialize English grammar checker
        self.tool = language_tool_python.LanguageTool('en-US')


    def analyze(self, text):

        # If text is empty return 0 errors
        if text.strip() == "":
            return 0

        # Detect grammar mistakes
        matches = self.tool.check(text)

        # Return number of grammar mistakes
        return len(matches)