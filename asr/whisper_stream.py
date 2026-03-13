# Import faster whisper model
from faster_whisper import WhisperModel


class WhisperStreamer:

    def __init__(self):

        # Load whisper model optimized for CPU
        self.model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8",
            cpu_threads=4
        )

        print("Whisper model loaded (CPU optimized)")


    def transcribe(self, audio_path):

        # Run speech recognition
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=3,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=2500
            )
        )

        transcript_parts = []
        timestamps = []

        for segment in segments:

            # Skip low confidence segments
            if segment.avg_logprob < -1.5:
                continue

            if len(segment.text.strip()) < 2:
                continue

            transcript_parts.append(segment.text.strip())
            timestamps.append((segment.start, segment.end))

        transcript = " ".join(transcript_parts)

        print("Transcript:", transcript)

        return transcript, timestamps