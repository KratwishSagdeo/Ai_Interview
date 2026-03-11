from faster_whisper import WhisperModel
import numpy as np
from Ai_Interview.configs.config import WHISPER_MODEL

class WhisperStreamer:

    def __init__(self):

       self.model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8"
        )

    def transcribe(self, audio):

        segments, info = self.model.transcribe(
            audio,
            beam_size=5,
            vad_filter=True
        )

        text = ""
        timestamps = []

        for seg in segments:
            text += seg.text
            timestamps.append((seg.start, seg.end))

        return text, timestamps