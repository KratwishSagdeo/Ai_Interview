import spacy

nlp = spacy.load("en_core_web_trf")

class LexicalAnalyzer:

    def analyze(self, text):

        doc = nlp(text)

        words = [token.text for token in doc if token.is_alpha]

        unique_words = len(set(words))
        total_words = len(words)

        ttr = unique_words / total_words if total_words > 0 else 0

        sentences = list(doc.sents)

        complexity = sum(len(s) for s in sentences) / len(sentences)

        return {
            "type_token_ratio": ttr,
            "sentence_complexity": complexity,
            "word_count": total_words
        }