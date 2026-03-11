from transformers import pipeline

class DisfluencyDetector:
    def __init__(self):
        self.model = pipeline(
            "token-classification",
            model="elastic/distilbert-base-cased-finetuned-conll03-english"
        )

    def detect(self, text):
        results = self.model(text)
        return results

        for r in results:

            if r["entity_group"] == "FILLER":
                fillers += 1

            if r["entity_group"] == "REPETITION":
                repetitions += 1

        return {
            "fillers": fillers,
            "repetitions": repetitions
        }