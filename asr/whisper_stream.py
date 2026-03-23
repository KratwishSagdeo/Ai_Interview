import os
import time
import requests


class WhisperStreamer:

    def __init__(self):

        self.api_key = os.getenv("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")

        # Groq Whisper endpoint
        self.url = "https://api.groq.com/openai/v1/audio/transcriptions"

        print("Whisper model loaded (Groq Cloud — fast mode)")


    def transcribe(self, audio_path):

        start = time.time()

        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": (os.path.basename(audio_path), f, "audio/wav")},
                    data={
                        "model": "whisper-large-v3-turbo",   # fastest Groq whisper model
                        "language": "en",                    # skip language detection
                        "response_format": "verbose_json",   # gives us timestamps
                        "temperature": "0"
                    }
                )

            data = response.json()

            if "error" in data:
                print("❌ Groq Whisper error:", data["error"])
                return "", []

            transcript = data.get("text", "").strip()

            # Extract word-level timestamps if available
            timestamps = []
            segments = data.get("segments", [])
            for seg in segments:
                timestamps.append((seg.get("start", 0), seg.get("end", 0)))

            elapsed = time.time() - start
            print(f"Transcript: {transcript}")
            print(f"⏱ STT Time (Groq Cloud): {elapsed:.2f}s")

            return transcript, timestamps

        except Exception as e:
            print(f"❌ Groq Whisper FAILED: {e}")
            return "", []