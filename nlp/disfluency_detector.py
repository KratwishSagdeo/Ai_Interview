from transformers import pipeline

class DisfluencyDetector:

    def __init__(self):

        self.model = pipeline(
            "token-classification",
            model="philschmid/bert-base-cased-finetuned-disfluency",
            aggregation_strategy="simple"
        )

    def detect(self, text):

        results = self.model(text)

        fillers = 0
        repetitions = 0

        for r in results:

            if r["entity_group"] == "FILLER":
                fillers += 1

            if r["entity_group"] == "REPETITION":
                repetitions += 1

        return {
            "fillers": fillers,
            "repetitions": repetitions
        }