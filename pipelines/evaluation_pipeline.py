import pickle

from asr.whisper_stream import WhisperStreamer
from audio.vad import PauseDetector
from nlp.disfluency_detector import DisfluencyDetector
from nlp.grammar import GrammarAnalyzer
from nlp.lexical import LexicalAnalyzer

from configs.config import FLUENCY_MODEL_PATH


class SpeechEvaluationPipeline:

    def __init__(self):

        self.asr = WhisperStreamer()
        self.pause_detector = PauseDetector()
        self.disfluency = DisfluencyDetector()
        self.grammar = GrammarAnalyzer()
        self.lexical = LexicalAnalyzer()

        with open(FLUENCY_MODEL_PATH, "rb") as f:
            self.fluency_model = pickle.load(f)

    def evaluate(self, audio):

        text, timestamps = self.asr.transcribe(audio)

        disfluency = self.disfluency.detect(text)

        grammar_errors = self.grammar.analyze(text)

        lexical = self.lexical.analyze(text)

        pauses = len(timestamps)

        speech_rate = lexical["word_count"] / (timestamps[-1][1] / 60)

        features = [[
            speech_rate,
            pauses,
            disfluency["fillers"],
            grammar_errors,
            lexical["type_token_ratio"],
            lexical["sentence_complexity"]
        ]]

        score = self.fluency_model.predict(features)[0]

        return {

            "transcript": text,

            "fluency_score": float(score),

            "speech_rate": speech_rate,

            "pause_count": pauses,

            "filler_count": disfluency["fillers"],

            "grammar_errors": grammar_errors,

            "lexical_diversity": lexical["type_token_ratio"]
        }