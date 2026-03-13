# Import pickle module
# Pickle is used to load serialized machine learning models stored on disk
from email.mime import audio
import pickle
import librosa
import soundfile as sf
from audio.audio_loader import load_audio


# Import os module
# os provides functions to interact with the operating system (files, paths etc.)
import os


# Import the Whisper speech recognition streaming module
# This module converts audio speech into text transcript
from asr.whisper_stream import WhisperStreamer


# Import pause detection module
# This module detects pauses in speech using timestamps
from audio.vad import PauseDetector


# Import filler word detection module
# This detects disfluencies like "um", "uh", "like", "you know"
from nlp.disfluency_detector import DisfluencyDetector


# Import grammar analysis module
# This module checks grammar errors in the transcript
from nlp.grammar import GrammarAnalyzer


# Import lexical richness analyzer
# This module measures vocabulary diversity
from nlp.lexical import LexicalAnalyzer


# Import path to the trained fluency ML model
# The path is defined in the config file
from configs.config import FLUENCY_MODEL_PATH



# ----------------------------------------------------
# Main Speech Evaluation Pipeline Class
# ----------------------------------------------------

class SpeechEvaluationPipeline:

    # Constructor method
    # This runs automatically when the class is initialized
    def __init__(self):

        # Initialize Whisper ASR engine
        # This object will convert audio → transcript
        self.asr = WhisperStreamer()

        # Initialize pause detector
        # This will help detect pauses between spoken words
        self.pause_detector = PauseDetector()

        # Initialize filler word detector
        # This detects words like "um", "uh", etc.
        self.disfluency = DisfluencyDetector()

        # Initialize grammar analysis module
        # This will check grammar correctness
        self.grammar = GrammarAnalyzer()

        # Initialize lexical analyzer
        # This computes vocabulary richness metrics
        self.lexical_analyzer = LexicalAnalyzer()

        # Default ML model state
        # If loading fails we will fallback to rule-based scoring
        self.fluency_model = None


        # ------------------------------------------------
        # Safe model loading
        # ------------------------------------------------

        # Check if the model file exists
        if os.path.exists(FLUENCY_MODEL_PATH):

            # Check if model file is not empty
            if os.path.getsize(FLUENCY_MODEL_PATH) > 0:

                try:

                    # Open model file in binary read mode
                    with open(FLUENCY_MODEL_PATH, "rb") as f:

                        # Load the trained ML model using pickle
                        self.fluency_model = pickle.load(f)

                    # Print confirmation message
                    print("✅ Fluency model loaded")

                # Catch errors if model loading fails
                except Exception as e:

                    # Print warning message
                    print("⚠ Failed to load fluency model:", e)

                    # Fallback to rule-based scoring
                    self.fluency_model = None

            else:

                # Model file exists but is empty
                print("⚠ fluency_model.pkl exists but is empty. Using rule-based scoring.")

        else:

            # Model file does not exist
            print("⚠ fluency_model.pkl not found. Using rule-based scoring.")



    # ----------------------------------------------------
    # Main Evaluation Function
    # ----------------------------------------------------

    def evaluate(self, audio):

        # STEP 1 — Speech Recognition
        # Convert audio speech into transcript text
        # Also returns timestamps for each spoken word
        self.preprocess_audio(audio)
        #text, timestamps = self.asr.transcribe(audio)
        audio_data, sample_rate = load_audio(audio)
        text, timestamps = self.asr.transcribe(audio)
        pause_count = self.pause_detector.detect_pauses(audio)

        # STEP 2 — Handle empty transcript
        # If ASR failed or detected no speech
        if text is None or text.strip() == "":

            # Return default zero metrics
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
        # Example fillers: um, uh, like, you know
        disfluency = self.disfluency.detect(text)


        # STEP 4 — Grammar analysis
        # Count grammar mistakes in transcript
        grammar_errors = self.grammar.analyze(text)


        # STEP 5 — Lexical analysis
        # Compute vocabulary richness metrics
        lexical_results = self.lexical_analyzer.analyze(text)


        # STEP 6 — Pause detection
        # Count pauses longer than 0.5 seconds
        # STEP 6 — Pause detection using WebRTC VAD
        #pause_count = self.pause_detector.detect_pauses(audio)
        print("Pause count:", pause_count)


        # STEP 7 — Calculate speech duration
        # Last timestamp indicates end of speech
        duration_seconds = timestamps[-1][1] if timestamps and len(timestamps) > 0 else 1

        # Convert duration to minutes
        duration_minutes = duration_seconds / 60


        # STEP 8 — Calculate speech rate
        # Words spoken per minute
        word_count = lexical_results["word_count"]

        speech_rate = word_count / duration_minutes if duration_minutes > 0 else 0
        print("Speech rate:", speech_rate)


        # STEP 9 — Build feature vector
        # This will be fed into the ML fluency model
        features = [[
            speech_rate,
            pause_count,
            disfluency["fillers"],
            grammar_errors,
            lexical_results["type_token_ratio"],
            lexical_results["sentence_complexity"]
        ]]


        # STEP 10 — ML Fluency Scoring
        if self.fluency_model is not None:

            try:

                # Predict fluency score using trained ML model
                score = self.fluency_model.predict(features)[0]

            except Exception:

                # If prediction fails use default score
                score = 50

        else:

            # ------------------------------------------------
            # Rule-based scoring fallback
            # ------------------------------------------------

            score = 70

            # Penalize filler words
            score -= disfluency["fillers"] * 3

            # Penalize grammar mistakes
            score -= grammar_errors * 2

            # Penalize pauses
            score -= pause_count * 2

            # Penalize slow speech
            if speech_rate < 100:
                score -= 5

            # Penalize overly fast speech
            if speech_rate > 180:
                score -= 5

            # Reward lexical diversity
            score += lexical_results["type_token_ratio"] * 10

            # Clamp score between 0 and 100
            score = max(0, min(100, score))


        # STEP 11 — Return final evaluation result
        return {
            "transcript": text,
            "fluency_score": float(score),
            "speech_rate": speech_rate,
            "pause_count": pause_count,
            "filler_count": disfluency["fillers"],
            "grammar_errors": grammar_errors,
            "lexical_diversity": lexical_results["type_token_ratio"]
        }
    def preprocess_audio(self, audio_path):


    # Load audio and automatically resample to 16000 Hz
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)

    # Debug output
        print("Audio resampled to:", sr)

    # Save the corrected audio back to the same file
        sf.write(audio_path, audio, 16000)