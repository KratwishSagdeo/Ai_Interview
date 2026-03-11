import pickle
import os

from Ai_Interview.asr.whisper_stream import WhisperStreamer
from Ai_Interview.audio.vad import PauseDetector
from Ai_Interview.nlp.disfluency_detector import DisfluencyDetector
from Ai_Interview.nlp.grammar import GrammarAnalyzer
from Ai_Interview.nlp.lexical import LexicalAnalyzer
from Ai_Interview.configs.config import FLUENCY_MODEL_PATH


class SpeechEvaluationPipeline:

    def __init__(self):

        self.asr = WhisperStreamer()
        self.pause_detector = PauseDetector()
        self.disfluency = DisfluencyDetector()
        self.grammar = GrammarAnalyzer()
        self.lexical_analyzer = LexicalAnalyzer()

        # Load fluency model safely
        self.fluency_model = None

        if os.path.exists(FLUENCY_MODEL_PATH):
            with open(FLUENCY_MODEL_PATH, "rb") as f:
                self.fluency_model = pickle.load(f)

    def evaluate(self, audio):

        # Speech to text
        text, timestamps = self.asr.transcribe(audio)

        # NLP analysis
        disfluency = self.disfluency.detect(text)
        grammar_errors = self.grammar.analyze(text)
        lexical_results = self.lexical_analyzer.analyze(text)

        pauses = len(timestamps)

        # Avoid division by zero
        duration_minutes = timestamps[-1][1] / 60 if timestamps else 1

        speech_rate = lexical_results["word_count"] / duration_minutes

        features = [[
            speech_rate,
            pauses,
            disfluency["fillers"],
            grammar_errors,
            lexical_results["type_token_ratio"],
            lexical_results["sentence_complexity"]
        ]]

        # If ML model exists → use it
        if self.fluency_model:
            score = self.fluency_model.predict(features)[0]

        # Otherwise fallback rule-based scoring
        else:
            score = max(
                0,
                min(
                    100,
                    70
                    - disfluency["fillers"] * 2
                    - grammar_errors * 2
                    + lexical_results["type_token_ratio"] * 10
                )
            )

        return {

            "transcript": text,

            "fluency_score": float(score),

            "speech_rate": speech_rate,

            "pause_count": pauses,

            "filler_count": disfluency["fillers"],

            "grammar_errors": grammar_errors,

            "lexical_diversity": lexical_results["type_token_ratio"]
        }