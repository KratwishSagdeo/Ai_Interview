import webrtcvad
import numpy as np

class PauseDetector:

    def __init__(self):

        self.vad = webrtcvad.Vad(2)

    def detect_pauses(self, audio_frames):

        pauses = 0

        for frame in audio_frames:

            if not self.vad.is_speech(frame, 16000):
                pauses += 1

        return pauses