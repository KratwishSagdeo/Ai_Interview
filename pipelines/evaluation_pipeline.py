# Import pickle module
# Pickle is used to load serialized machine learning models stored on disk
from email.mime import audio
import pickle
import librosa
import soundfile as sf
import time
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
    # STEP A: Preprocess + Transcribe ONLY
    # ----------------------------------------------------
    # Returns transcript and timestamps as fast as possible
    # so Gemini can start generating while analysis continues.

    def transcribe(self, audio_path):

        t0 = time.time()

        # Run Whisper STT directly (faster-whisper handles decoding in C)
        text, timestamps = self.asr.transcribe(audio_path)

        elapsed = time.time() - t0
        print(f"⏱  STT Time: {elapsed:.2f}s")

        return text, timestamps


    # ----------------------------------------------------
    # STEP B: Analyze fluency metrics (no STT)
    # ----------------------------------------------------
    # Runs in parallel with Gemini follow-up generation.

    def analyze(self, audio_path, text, timestamps):

        t0 = time.time()

        # Pause detection (WebRTC VAD)
        pause_count = self.pause_detector.detect_pauses(audio_path)

        # Handle empty transcript
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


        # Detect filler words
        disfluency = self.disfluency.detect(text)

        # Grammar analysis
        grammar_errors = self.grammar.analyze(text)

        # Lexical analysis
        lexical_results = self.lexical_analyzer.analyze(text)

        # Pause count
        print("Pause count:", pause_count)

        # Calculate speech duration
        duration_seconds = timestamps[-1][1] if timestamps and len(timestamps) > 0 else 1
        duration_minutes = duration_seconds / 60

        # Speech rate
        word_count = lexical_results["word_count"]
        speech_rate = word_count / duration_minutes if duration_minutes > 0 else 0
        print("Speech rate:", speech_rate)

        # Build feature vector for ML model
        features = [[
            speech_rate,
            pause_count,
            disfluency["fillers"],
            grammar_errors,
            lexical_results["type_token_ratio"],
            lexical_results["sentence_complexity"]
        ]]

        # ML Fluency Scoring
        if self.fluency_model is not None:

            try:
                score = self.fluency_model.predict(features)[0]

            except Exception:
                score = 50

        else:

            # Rule-based scoring fallback
            score = 70

            score -= disfluency["fillers"] * 3
            score -= grammar_errors * 2
            score -= pause_count * 2

            if speech_rate < 100:
                score -= 5

            if speech_rate > 180:
                score -= 5

            score += lexical_results["type_token_ratio"] * 10
            score = max(0, min(100, score))

        elapsed = time.time() - t0
        print(f"⏱  Analysis Time: {elapsed:.2f}s")

        return {
            "transcript": text,
            "fluency_score": float(score),
            "speech_rate": speech_rate,
            "pause_count": pause_count,
            "filler_count": disfluency["fillers"],
            "grammar_errors": grammar_errors,
            "lexical_diversity": lexical_results["type_token_ratio"]
        }


    # ----------------------------------------------------
    # Original evaluate() — kept for backward compatibility
    # ----------------------------------------------------

    def evaluate(self, audio_path):

        text, timestamps = self.transcribe(audio_path)
        return self.analyze(audio_path, text, timestamps)


    # ----------------------------------------------------
    # Preprocess audio to 16kHz mono (Trims silence & limits to 15s)
    # ----------------------------------------------------

    def preprocess_audio(self, audio_path):

        t0 = time.time()
        
        # Load audio and automatically resample to 16000 Hz
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        
        # Trim leading and trailing silence (top_db=30 is a good default)
        audio_trimmed, _ = librosa.effects.trim(audio, top_db=30)
        
        # Limit to 15 seconds max to guarantee fast processing
        max_samples = 15 * sr
        if len(audio_trimmed) > max_samples:
            audio_trimmed = audio_trimmed[:max_samples]
            
        # Save the optimized audio back to the same file
        sf.write(audio_path, audio_trimmed, 16000)
        
        elapsed = time.time() - t0
        print(f"⏱  Audio Preprocessing Time: {elapsed:.2f}s (Len: {len(audio_trimmed)/sr:.1f}s)")