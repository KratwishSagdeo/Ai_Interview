# Used to load ML model from disk
import pickle

# Used to check if model file exists
import os


# Speech recognition module (Whisper wrapper)
from Ai_Interview.asr.whisper_stream import WhisperStreamer


# Pause detection module
from Ai_Interview.audio.vad import PauseDetector


# Detect filler words like "um", "uh", "like"
from Ai_Interview.nlp.disfluency_detector import DisfluencyDetector


# Grammar checking module
from Ai_Interview.nlp.grammar import GrammarAnalyzer


# Vocabulary richness analyzer
from Ai_Interview.nlp.lexical import LexicalAnalyzer


# Path where trained ML model is stored
from Ai_Interview.configs.config import FLUENCY_MODEL_PATH



class SpeechEvaluationPipeline:

    def __init__(self):

        # Initialize Whisper speech recognition model
        # Converts audio → text transcript
        self.asr = WhisperStreamer()

        # Initialize pause detection logic
        # Used to identify silent gaps between speech segments
        self.pause_detector = PauseDetector()

        # Initialize filler word detector
        # Detects hesitation words in transcript
        self.disfluency = DisfluencyDetector()

        # Initialize grammar checking engine
        self.grammar = GrammarAnalyzer()

        # Initialize lexical richness analyzer
        # Measures vocabulary diversity
        self.lexical_analyzer = LexicalAnalyzer()

        # Variable to hold ML fluency model
        self.fluency_model = None

        # If trained model exists → load it
        if os.path.exists(FLUENCY_MODEL_PATH):

            with open(FLUENCY_MODEL_PATH, "rb") as f:
                self.fluency_model = pickle.load(f)



    def evaluate(self, audio):

        # STEP 1 — Convert speech audio to text
        text, timestamps = self.asr.transcribe(audio)


        # STEP 2 — Prevent evaluation of empty transcript
        if text is None or text.strip() == "":

            return {
                "transcript": "",
                "fluency_score": 0,
                "speech_rate": 0,
                "pause_count": 0,
                "filler_count": 0,
                "grammar_errors": 0,
                "lexical_diversity": 0
            }


        # STEP 3 — Detect filler words
        disfluency = self.disfluency.detect(text)


        # STEP 4 — Detect grammar mistakes
        grammar_errors = self.grammar.analyze(text)


        # STEP 5 — Analyze vocabulary richness
        lexical_results = self.lexical_analyzer.analyze(text)



        # STEP 6 — Calculate real pauses between speech segments
        pause_count = 0

        for i in range(1, len(timestamps)):

            previous_end = timestamps[i - 1][1]

            current_start = timestamps[i][0]

            pause_duration = current_start - previous_end

            # Consider pause only if silence > 0.5 seconds
            if pause_duration > 0.5:
                pause_count += 1



        # STEP 7 — Calculate speech duration
        if timestamps:
            duration_seconds = timestamps[-1][1]
        else:
            duration_seconds = 1


        # Convert seconds → minutes
        duration_minutes = duration_seconds / 60



        # STEP 8 — Calculate words per minute
        word_count = lexical_results["word_count"]

        speech_rate = word_count / duration_minutes



        # STEP 9 — Create feature vector for ML model
        features = [[
            speech_rate,
            pause_count,
            disfluency["fillers"],
            grammar_errors,
            lexical_results["type_token_ratio"],
            lexical_results["sentence_complexity"]
        ]]



        # STEP 10 — Predict score using ML model if available
        if self.fluency_model:

            score = self.fluency_model.predict(features)[0]



        # Otherwise fallback to rule-based scoring
        else:

            score = 70

            # Penalize fillers
            score -= disfluency["fillers"] * 3

            # Penalize grammar errors
            score -= grammar_errors * 2

            # Penalize too many pauses
            score -= pause_count * 2

            # Penalize slow speech
            if speech_rate < 100:
                score -= 5

            # Penalize very fast speech
            if speech_rate > 180:
                score -= 5

            # Reward vocabulary diversity
            score += lexical_results["type_token_ratio"] * 10


            # Ensure score stays between 0-100
            score = max(0, min(100, score))



        # STEP 11 — Return evaluation results
        return {

            "transcript": text,

            "fluency_score": float(score),

            "speech_rate": speech_rate,

            "pause_count": pause_count,

            "filler_count": disfluency["fillers"],

            "grammar_errors": grammar_errors,

            "lexical_diversity": lexical_results["type_token_ratio"]
        }