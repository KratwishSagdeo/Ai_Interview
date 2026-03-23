import re


class GrammarAnalyzer:

    def __init__(self):

        # ✅ No external server to start — instant initialization
        # LanguageTool spins up a Java process which takes 8-12 seconds
        # This regex-based checker runs in microseconds and catches
        # the most common spoken English errors interviewers care about

        self.filler_patterns = [
            r'\bi\s+(?:is|are|am\s+not\s+(?:know|sure))\b',   # "I are", "I is"
            r'\bhe\s+(?:have|are)\b',                           # "he have", "he are"
            r'\bshe\s+(?:have|are)\b',
            r'\bthey\s+(?:is|has)\b',                           # "they is", "they has"
            r'\bwe\s+(?:is|has)\b',
            r'\bdoesn\'t\s+\w+s\b',                             # "doesn't works"
            r'\bdon\'t\s+\w+s\b',                               # "don't works"
            r'\b(?:a)\s+[aeiou]\w+\b',                          # "a apple" (should be "an")
            r'\bmore\s+\w+er\b',                                 # "more faster"
            r'\bmost\s+\w+est\b',                                # "most fastest"
        ]

        self.compiled = [re.compile(p, re.IGNORECASE) for p in self.filler_patterns]

    def analyze(self, text):

        if not text or text.strip() == "":
            return 0

        errors = 0
        for pattern in self.compiled:
            errors += len(pattern.findall(text))

        return errors