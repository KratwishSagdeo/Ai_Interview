# Import faster whisper model
from faster_whisper import WhisperModel


class WhisperStreamer:

    def __init__(self):

        # Load whisper model
        # "base" model is fast and good for MVP
        self.model = WhisperModel("base", device="cpu")


    def transcribe(self, audio_path):

        # Run speech recognition on audio file
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=5
        )

        transcript = ""

        timestamps = []

        # Loop through each detected speech segment
        for segment in segments:

            # FILTER 1 — Ignore low confidence speech
            # avg_logprob measures confidence of transcription
            if segment.avg_logprob < -1.0:
                continue

            # FILTER 2 — Ignore extremely short segments
            if len(segment.text.strip()) < 2:
                continue

            # Append clean text
            transcript += segment.text + " "

            # Save timestamp for pause detection
            timestamps.append((segment.start, segment.end))


        # Remove extra spaces
        transcript = transcript.strip()

        return transcript, timestamps