# Import WebRTC Voice Activity Detection library
import webrtcvad

# Import wave module to read audio files
import wave


class PauseDetector:

    def __init__(self):

        # Initialize VAD with aggressiveness level
        # Range: 0 (least aggressive) to 3 (most aggressive)
        # 2 is balanced for speech detection
        self.vad = webrtcvad.Vad(2)


    def detect_pauses(self, audio_path):

        # Open audio file
        wf = wave.open(audio_path, 'rb')

        # Get audio sample rate
        sample_rate = wf.getframerate()

        # Frame duration in milliseconds
        frame_duration = 30

        # Calculate number of samples per frame
        frame_size = int(sample_rate * frame_duration / 1000)

        # Variable to count silent frames
        pauses = 0

        while True:

            # Read audio frame
            frame = wf.readframes(frame_size)

            # Stop when audio ends
            if len(frame) == 0:
                break

            # Detect if frame contains speech
            is_speech = self.vad.is_speech(frame, sample_rate)

            # If frame is not speech → count as pause
            if not is_speech:
                pauses += 1

        # Return number of silent segments
        return pauses