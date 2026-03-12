# Import spaCy NLP library
import spacy

# Load transformer based English NLP model
nlp = spacy.load("en_core_web_trf")


class LexicalAnalyzer:

    def analyze(self, text):

        # Convert text into spaCy document
        doc = nlp(text)

        # Extract only alphabetic tokens (ignore punctuation)
        words = [token.text for token in doc if token.is_alpha]

        # Count unique words
        unique_words = len(set(words))

        # Count total words
        total_words = len(words)

        # Type Token Ratio (vocabulary diversity)
        if total_words > 0:
            ttr = unique_words / total_words
        else:
            ttr = 0

        # Extract sentences
        sentences = list(doc.sents)

        # Prevent division by zero if no sentences detected
        if len(sentences) > 0:
            complexity = sum(len(s) for s in sentences) / len(sentences)
        else:
            complexity = 0

        return {
            "type_token_ratio": ttr,
            "sentence_complexity": complexity,
            "word_count": total_words
        }