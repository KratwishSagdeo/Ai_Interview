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

        # Debug: print sample rate
        print("Audio sample rate:", sample_rate)

        # Frame duration in milliseconds
        frame_duration = 30

        # Calculate number of samples per frame
        frame_size = int(sample_rate * frame_duration / 1000)

        # Counters
        pauses = 0
        silent_frames = 0

        while True:

            # Read audio frame
            frame = wf.readframes(frame_size)

            # Stop when audio ends
            if len(frame) < frame_size * 2:
                break

            try:
                # Detect if frame contains speech
                is_speech = self.vad.is_speech(frame, sample_rate)
            except Exception:
                # Skip invalid frames instead of crashing
                continue

            if not is_speech:

                # Increase silent frame count
                silent_frames += 1

            else:

                # Convert silent frames to milliseconds
                silence_duration_ms = silent_frames * frame_duration

                # Count pause only if silence >= 2.5 seconds
                if silence_duration_ms >= 2500:
                    pauses += 1

                # Reset silent frame counter
                silent_frames = 0


        # Handle silence at end of audio
        silence_duration_ms = silent_frames * frame_duration
        if silence_duration_ms >= 2500:
            pauses += 1

        # Debug output
        print("Detected pauses:", pauses)

        # Return number of pauses
        wf.close()
        return pauses